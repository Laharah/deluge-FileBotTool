# killableprocess - subprocesses which can be reliably killed
#
# Parts of this module are copied from the subprocess.py file contained
# in the Python distribution.
#
# Copyright (c) 2003-2004 by Peter Astrand <astrand@lysator.liu.se>
#
# Additions and modifications written by Benjamin Smedberg
# <benjamin@smedbergs.us> are Copyright (c) 2006 by the Mozilla Foundation
# <http://www.mozilla.org/>
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of the
# author not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""killableprocess - Subprocesses which can be reliably killed

This module is a subclass of the builtin "subprocess" module. It allows
processes that launch subprocesses to be reliably killed on Windows (via the Popen.kill() method.

It also adds a timeout argument to Wait() for a limited period of time before
forcefully killing the process.

Note: On Windows, this module requires Windows 2000 or higher (no support for
Windows 95, 98, or NT 4.0). It also requires ctypes, which is bundled with
Python 2.5+ or available from http://python.net/crew/theller/ctypes/
"""

import subprocess
import sys
import os
import time
import types

try:
    from subprocess import CalledProcessError
except ImportError:
    # Python 2.4 doesn't implement CalledProcessError
    class CalledProcessError(Exception):
        """This exception is raised when a process run by check_call() returns
        a non-zero exit status. The exit status will be stored in the
        returncode attribute."""
        def __init__(self, returncode, cmd):
            self.returncode = returncode
            self.cmd = cmd
        def __str__(self):
            return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)

mswindows = (sys.platform == "win32")

if mswindows:
    from . import winprocess
else:
    import signal

def call(*args, **kwargs):
    waitargs = {}
    if "timeout" in kwargs:
        waitargs["timeout"] = kwargs.pop("timeout")

    return Popen(*args, **kwargs).wait(**waitargs)

def check_call(*args, **kwargs):
    """Call a program with an optional timeout. If the program has a non-zero
    exit status, raises a CalledProcessError."""

    retcode = call(*args, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = args[0]
        raise CalledProcessError(retcode, cmd)

if not mswindows:
    def DoNothing(*args):
        pass

class Popen(subprocess.Popen):
    if not mswindows:
        # Override __init__ to set a preexec_fn
        def __init__(self, *args, **kwargs):
            if len(args) >= 7:
                raise Exception("Arguments preexec_fn and after must be passed by keyword.")

            real_preexec_fn = kwargs.pop("preexec_fn", None)
            def setpgid_preexec_fn():
                os.setpgid(0, 0)
                if real_preexec_fn:
                    apply(real_preexec_fn)

            kwargs['preexec_fn'] = setpgid_preexec_fn

            subprocess.Popen.__init__(self, *args, **kwargs)

    if mswindows:
        def _execute_child_27(self, args, executable, preexec_fn, close_fds,
                              cwd, env, universal_newlines, startupinfo,
                              creationflags, shell, to_close,
                              p2cread, p2cwrite,
                              c2pread, c2pwrite,
                              errread, errwrite):
            if not isinstance(args, types.StringTypes):
                args = subprocess.list2cmdline(args)

            if startupinfo is None:
                startupinfo = winprocess.STARTUPINFO()

            if None not in (p2cread, c2pwrite, errwrite):
                startupinfo.dwFlags |= winprocess.STARTF_USESTDHANDLES

                startupinfo.hStdInput = int(p2cread)
                startupinfo.hStdOutput = int(c2pwrite)
                startupinfo.hStdError = int(errwrite)
            if shell:
                startupinfo.dwFlags |= winprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = winprocess.SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = comspec + " /c " + args

            # We create a new job for this process, so that we can kill
            # the process and any sub-processes
            self._job = winprocess.CreateJobObject()

            creationflags |= winprocess.CREATE_SUSPENDED
            creationflags |= winprocess.CREATE_UNICODE_ENVIRONMENT

            def _close_in_parent(fd):
                fd.Close()
                try:
                    to_close.remove(fd)
                except ValueError:
                    pass
            try:
                hp, ht, pid, tid = winprocess.CreateProcess(
                    executable, args,
                    None, None, # No special security
                    1, # Must inherit handles!
                    creationflags,
                    winprocess.EnvironmentBlock(env),
                    cwd, startupinfo)
            finally:
                if p2cread is not None:
                    _close_in_parent(p2cread)
                if c2pwrite is not None:
                    _close_in_parent(c2pwrite)
                if errwrite is not None:
                    _close_in_parent(errwrite)

            self._child_created = True
            self._handle = hp
            self._thread = ht
            self.pid = pid

            winprocess.AssignProcessToJobObject(self._job, hp)
            winprocess.ResumeThread(ht)


        def _execute_child(self, *args):
            if sys.version_info[:2] == (2, 6):
                args = args[:10] + ([],) + args[10:]
            return self._execute_child_27(*args)

    def kill(self, group=True):
        """Kill the process. If group=True, all sub-processes will also be killed."""
        if mswindows:
            if group:
                winprocess.TerminateJobObject(self._job, 127)
            else:
                winprocess.TerminateProcess(self._handle, 127)
            self.returncode = 127
        else:
            if group:
                os.killpg(self.pid, signal.SIGKILL)
            else:
                os.kill(self.pid, signal.SIGKILL)
            self.returncode = -9

    def wait(self, timeout=-1, group=True):
        """Wait for the process to terminate. Returns returncode attribute.
        If timeout seconds are reached and the process has not terminated,
        it will be forcefully killed. If timeout is -1, wait will not
        time out."""

        if self.returncode is not None:
            return self.returncode

        if mswindows:
            if timeout != -1:
                timeout = timeout * 1000
            rc = winprocess.WaitForSingleObject(self._handle, timeout)
            if rc == winprocess.WAIT_TIMEOUT:
                self.kill(group)
            else:
                self.returncode = winprocess.GetExitCodeProcess(self._handle)
        else:
            if timeout == -1:
                subprocess.Popen.wait(self)
                return self.returncode

            starttime = time.time()

            # Make sure there is a signal handler for SIGCHLD installed
            oldsignal = signal.signal(signal.SIGCHLD, DoNothing)

            while time.time() < starttime + timeout - 0.01:
                pid, sts = os.waitpid(self.pid, os.WNOHANG)
                if pid != 0:
                    self._handle_exitstatus(sts)
                    signal.signal(signal.SIGCHLD, oldsignal)
                    return self.returncode

                # time.sleep is interrupted by signals (good!)
                newtimeout = timeout - time.time() + starttime
                time.sleep(newtimeout)

            self.kill(group)
            signal.signal(signal.SIGCHLD, oldsignal)
            subprocess.Popen.wait(self)

        return self.returncode
