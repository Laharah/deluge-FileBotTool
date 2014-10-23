__author__ = 'Lunchbox'

import subprocess
import re
import os
import platform
import locale
import tempfile

#from deluge.log import LOG as log


class FileBotInterface(object):
    """Calls and interacts with filebot as a subprocess

    Attributes:
        database: the databse to use with a filebot run
        format_string: a filebot format string to use with a filebot run
            see 'http://www.filebot.net/naming.html' for details
        order: the order filebot should use for episode naming
            airdate | absolute | dvd
        action: filebot --action flag argument defaluts to 'move'
        """
    def __init__(self):
        self.database = None
        self.format_string = None
        self.filebot_order = None
        self.filebot_mode = "-rename"
        self.filebot_action = "move"
        self.destination_mappings = {}

    def dry_run(self, target):
        """executes a filebot dry run using current settings.

        Useful for gathering non-destructive infromation about filemovements
        before they are executed.

        Args:
            target: file or folder you would like the handler to run on

        Returns:
            a tupple consisting of:
            -number of processed files
            -list of tuples containing (old, suggested) file locations OR error
                message
            -number of skipped files

        """
        exit_code, data, filebot_error = self._execute(target, action='test')
        if exit_code != 0:
            log.error("FILEBOT ERROR:\n{}\n".format(data, filebot_error))
            return (0, "FILEBOT ERROR", 0)

        total_processed_files, suggested_moves, skipped_files = (
            self.parse_filebot(data))

        if len(suggested_moves) < 1:
            return (total_processed_files, "NO SUGGESTIONS", skipped_files)
        else:
            return (total_processed_files, suggested_moves, skipped_files)

    def parse_filebot(self, data):
        """Parses the output of a filebot run and returns relevent infromation

        parses and gives info about number of files processd, their moves, and
        the number of skipped files, using regular expressions
        NOTE: data should be pre-decoded as utf-8 or windows-1252

        Args:
            data: a string containing the output of a filebot run

        Returns:
            a tuple in format (num processed files, list of movement tuples,
                              number of skipped files)
        """
        data = data.splitlines()

        skipped_files = []
        for line in data:
            skippedMatch = re.search(r'Skipped \[(.*?)\] because', line)
            if skippedMatch:
                skipped_files.append(skippedMatch.group(1))

        #processed files
        total_processed_files = 0
        for line in data:
            match = re.search(r'Processed (\d*) ', line)
            if match:
                total_processed_files = int(match.group(1))

        #suggested moves
        file_moves = []
        for line in data:
            match = re.search(r' \[(.*?)\] to \[(.*?)\]', line)
            if match:
                file_moves.append((match.group(1), match.group(2)))

        return (total_processed_files, file_moves, len(skipped_files))

    def _execute(self, target, action=None, format_string=None):
        """used to execute a filebot run on target.

        executes a run using the current handler settings, optionally takes an
        action argument

        Args:
            target: str; the file or folder filebot will execute on.
            action: str; the argument for the filebotCLI '--action' flag.
                valid input: move | copy | keeplink | symlink | hardlink | test
                defaults to the filebot_action attribute (default='move')
            format_string: str; the format string you would like to use
                defaults to instance format string

        Returns:
            tuple in format '(exit_code, stdoutput, stderr)'
        """

        #open and close a temp file so filebot can use it as a log file.
        #this is a workaround for malfunctioning UTF-8 chars in windows.
        file_temp = tempfile.NamedTemporaryFile(delete=False)
        file_temp.close()

        if not format_string:
            format_string = self.format_string
        if not action:
            action = self.filebot_action
        process_arguments = [
            "filebot",
            self.filebot_mode,
            target.decode('utf8'),
            "-non-strict",
            "--action",
            action,
            "-r",
            "--log-file",
            file_temp.name
        ]
        if format_string:
            process_arguments.append("--format")
            process_arguments.append(format_string)
        if self.database:
            process_arguments.append("--db")
            process_arguments.append(self.database)
        if self.filebot_order:
            process_arguments.append('--order')
            process_arguments.append(self.filebot_order)


        process = subprocess.Popen(process_arguments, stdout=subprocess.PIPE)
        process.wait()
        _, error = process.communicate()
        exit_code = process.returncode

        with open(file_temp.name, 'rU') as log:
            data = log.read().decode('utf8')  #read and cleanup temp/logfile
            log.close()
        os.remove(file_temp.name)

        return (exit_code, data, error)

    def test_format_string(self, format_string=None,
                           file_name="Citizen Kane.avi"):
        """Runs a quick test of a format string and returns renamed sample
         filename

        Useful for testing to see if filebot will correctly parse a format
        string. By default uses a movie title, you must pass a custom filename
        to test a tvshow style format string.

        Args:
            format_string: the string to be tested. defaults instance format
                string
            file_name: a string that contains an (imaginary) file name to test
                the format string against. defaults to a movie

        Returns:
            a string containing the renamed file_name using the format_string.
                Returns an empty string if no matches were found.
        """
        if not format_string:
            format_string = self.format_string
        _, data, _ = self._execute(file_name, action='test',
                                   format_string=format_string)
        _, file_moves, _ = self.parse_filebot(data)
        if not file_moves:
            return ""
        else:
            return file_moves[0][1]