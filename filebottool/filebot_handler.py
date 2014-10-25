"""contains the FileBotHandler class and utility functions for interaction with
filebot.
"""
__author__ = 'Lunchbox'

import subprocess
import re
import os
import tempfile

#from deluge.log import LOG as log


def parse_filebot(data):
    """Parses the output of a filebot run and returns relevant information

    parses and gives info about number of files processed, their moves, and
    the number of skipped files, using regular expressions
    NOTE: data should be pre-decoded as utf-8

    Args:
        data: a string containing the output of a filebot run

    Returns:
        a tuple in format (num processed files, list of movement tuples,
                          number of skipped files)
    """
    data = data.splitlines()

    skipped_files = []
    for line in data:
        skipped_match = re.search(r'Skipped \[(.*?)\] because', line)
        if skipped_match:
            skipped_files.append(skipped_match.group(1))

    # processed files
    total_processed_files = 0
    for line in data:
        match = re.search(r'Processed (\d*) ', line)
        if match:
            total_processed_files = int(match.group(1))

    # file moves
    file_moves = []
    for line in data:
        match = re.search(r' \[(.*?)\] (?:(?:to)|(?:=>)) \[(.*?)\]', line)
        if match:
            file_moves.append((match.group(1), match.group(2)))

    return total_processed_files, file_moves, len(skipped_files)


class FileBotHandler(object):
    """Calls and interacts with filebot as a subprocess

    Attributes:
        database: the database to use with a filebot run
        filebot_format_string: a filebot format string to use with a filebot
            run. it is recommended that you test your format string with
            test_format_string before setting this value
            see 'http://www.filebot.net/naming.html' for details
        filebot_order: a special order filebot should use for episode naming
            airdate | absolute | dvd
        filebot_query_string: optional string to override the title filebot
            should try to match. corresponds to the -'-q' command in filebot
        filebot_mode: the type of function you would like filebot to preform
            [rename, get-subtitles, check, etc...]
        filebot_action: filebot --action flag argument defaults to 'move'
        """

    def __init__(self):
        self.filebot_database = None
        self.filebot_format_string = None
        self.filebot_order = None
        self.filebot_query_string = None
        self.filebot_mode = "-rename"
        self.filebot_action = "move"

    def set_filebot_database(self, database, override=False):
        """sets the filebot_database to *database*

        Args:
            database: the database filebot should use
                Valid databases include:
                    TheTVDB
                    TvRage
                    AniDB
                    OpenSubtitles
                    TheMovieDB
            override: set to true pass database argument to filebot
            regardless of validity checking

        Returns: True or False depending on whether or not database is valid
        and was successfully set
        """
        if override:
            self.filebot_database = database
            return True

        valid_databases = [
            'thetvdbb',
            'tvrage',
            'anidb',
            'opensubtitles'
            'themoviedb'
        ]
        database = database.lower()
        if database in valid_databases:
            self.filebot_database = database
            return True
        else:
            return False

    def set_filebot_mode(self, mode_string):
        """sets the filebot mode to *mode_string*

        Args:
            mode_string: the function you would like filebot to execute
                Valid Modes:
                    rename
                    move
                    check
                    get-missing-subtitle
                    get-subtitles
                    list
                    mediainfo

        Returns:
            True if set successfully, False if not.
        """
        valid_modes = [
            '-rename',
            '-move',
            '-check',
            '-get-missing-subtitles',
            '-get-subtitles',
            '-list',
            '-mediainfo'
        ]

        if not mode_string.startswith('-'):
            mode_string = "-" + mode_string

        if mode_string not in valid_modes:
            return False
        else:
            self.filebot_mode = mode_string
            return True

    def set_filebot_order(self, order_string):
        """sets the episode order flag for the filebot run

        sets and checks for validity of the *order_string passed*. Pass None to
         reset to filebot default

        Args:
            order_string: the order you want your episodes named.
            valid orders:(None | airdate | dvd | absolute)

        Returns:
            True or False based on success
        """
        valid_orders = [
            None,
            "dvd",
            "airdate",
            "absolute"
        ]

        if order_string in valid_orders:
            self.filebot_order = order_string
            return True
        else:
            return False

    def dry_run(self, target):
        """executes a filebot dry run using current settings, making no
        changes to the filesystem

        Useful for gathering non-destructive information about file movements
        before they are executed.

        Args:
            target: file/folder or list of files/folders you would like the
            handler to run on

        Returns:
            a tuple consisting of:
            -number of processed files
            -list of tuples containing (old, suggested) file locations OR error
                message
            -number of skipped files
        """
        exit_code, data, filebot_error = self._send_to_filebot(target,
                                                               action='test')
        if exit_code != 0:
            #log.error("FILEBOT ERROR:\n{}\n{}".format(data, filebot_error))
            return 0, "FILEBOT ERROR", 0

        total_processed_files, suggested_moves, skipped_files = (
            parse_filebot(data))

        if len(suggested_moves) < 1:
            return total_processed_files, "NO SUGGESTIONS", skipped_files
        else:
            return total_processed_files, suggested_moves, skipped_files

    def sort_files(self, target, format_string=None):
        """Executes filebot on *target* using the current settings

        Args:
            target: the file or folder you want filebot to execute against
            format_string: optional argument to override the currently set
                format string. Mostly there for convenience.
        Returns:
            a tuple consisting of:
                -number of processed files
                -list of tuples containing (old, new) file locations OR error
                    message
                -number of skipped files
        """
        if not format_string:
            format_string = self.filebot_format_string
        exit_code, data, filebot_error = self._send_to_filebot(target,
                                                               format_string)
        if exit_code != 0:
            return 0, "FILEBOT ERROR", 0

        return parse_filebot(data)

    def get_subtitles(self, target, language_code=None, encoding=None,
                      force=False):
        """Gets subtitles for a given *target*

        Will use filebot to download subtitles from OpenSubtitles.org using
        the file hash. By default, it will only download subtitles if the
        .srt file for the given language is missing. This behavior can be
        overridden by the *force* flag

        Args:
            target: The file/folder or list of files/folders you want filebot
            to find subtitles for
            language_code: the 2 letter language code of the language you
                want. Uses the filebot default if not designated
            encoding: the output charset filebot should use (UTF-8, etc...)
            force: a flag to force filebot to ignore pre-exsisting subtitle
                files

        Returns:
            A list containing the downloaded subtitle file names
        """
        mode = "-get-missing-subtitles"
        if force:
            mode = "-get-subtitles"

        _, data, _ = self._send_to_filebot(target, mode=mode,
                                           language_code=language_code,
                                           encoding=encoding)
        _, downloads, _ = parse_filebot(data)
        return [name[1] for name in downloads]

    def test_format_string(self, format_string=None,
                           file_name="Citizen Kane.avi"):
        """Runs a quick test of a format string and returns renamed sample
         filename

        Useful for testing to see if filebot will correctly parse a format
        string. By default uses a movie title, you must pass a custom filename
        to test a tv show style format string.

        Args:
            format_string: the string to be tested. defaults the instance
            format string
            file_name: a string that contains an (imaginary) file name to
                test the format string against. defaults to a movie

        Returns:
            a string containing the renamed file_name using the format_string.
                Returns an empty string if no matches were found.
        """
        if not format_string:
            format_string = self.filebot_format_string
        _, data, _ = self._send_to_filebot(file_name, action='test',
                                           format_string=format_string)
        _, file_moves, _ = parse_filebot(data)
        if not file_moves:
            return ""
        else:
            return file_moves[0][1]

    def _send_to_filebot(self, targets, action=None, format_string=None,
                         mode=None,
                         language_code=None, encoding=None):
        """internal function used to set arguments and execute a filebot run
            on targets.

        executes a run using the current handler settings, optionally takes an
        action and format argument

        Args:
            target: str; the file or folder filebot will execute on.
            action: str; the argument for the filebotCLI '--action' flag.
                valid input: move | copy | keeplink | symlink | hardlink | test
                defaults to the filebot_action attribute (default='move')
            format_string: str; the format string you would like to use
                defaults to instance format string
            mode: the filebot mode, see *FileBotHandler.set_filebot_mode* for
                details
            language_code: 2 letter language code to hand filebot --lang
                argument
            encoding: output charset

        Returns:
            tuple in format '(exit_code, stdoutput, stderr)'
        """
        # setting up default args if not passed to function
        if not format_string:
            format_string = self.filebot_format_string
        if not action:
            action = self.filebot_action
        if not mode:
            mode = self.filebot_mode

        process_arguments = [
            mode,
            "-non-strict",
            "--action",
            action,
            "-r",
        ]

        if format_string:
            process_arguments.append("--format")
            process_arguments.append(format_string)
        if self.filebot_database:
            process_arguments.append("--db")
            process_arguments.append(self.filebot_database)
        if self.filebot_order:
            process_arguments.append("--order")
            process_arguments.append(self.filebot_order)
        if self.filebot_query_string:
            process_arguments.append("--q")
            process_arguments.append(self.filebot_query_string)
        if language_code:
            process_arguments.append("--lang")
            process_arguments.append(language_code)
        if encoding:
            process_arguments.append("--encoding")
            process_arguments.append(encoding)

        if isinstance(targets, str):
            process_arguments.append(targets)
        else:
            process_arguments += [target.decode("utf8") for target in targets]

        return self._execute(process_arguments)

    def _send_to_filebot_script(self, script_name, script_arguments):
        """special execution method for setting arguments and executing
            filebot scripts.

        takes only the script name and the arguments for the script

        Args:
            script_name: the file name of the script. built-ins have prefix
                'fn:'
            script_arguments: arguments to be passed to the script

        Returns:
            tuple in format '(exit_code, stdout, stderr)'
        """
        process_arguments = [
            '-script',
            script_name
        ]
        if isinstance(script_arguments, str):
            script_arguments = [script_arguments]
        process_arguments += [arg.decode("utf8") for arg in script_arguments]

        self._execute(process_arguments)

    def _execute(self, process_arguments):
        """underlying execution method to call filebot as subprocess

        Handles the actual execution and output capture

        Args:
            process_arguments: list of the arguments to be passed to filebotCLI

        Returns:
            tuple in format '(exit_code, stdout, stderr)'
        """
        # open and close a temp file so filebot can use it as a log file.
        # this is a workaround for malfunctioning UTF-8 chars in Windows.
        file_temp = tempfile.NamedTemporaryFile(delete=False)
        file_temp.close()
        process_arguments = (["filebot", "--log-file", file_temp.name] +
                             process_arguments)

        process = subprocess.Popen(process_arguments, stdout=subprocess.PIPE)
        process.wait()
        _, error = process.communicate()
        exit_code = process.returncode

        with open(file_temp.name, 'rU') as log:
            data = log.read().decode('utf8')  # read and cleanup temp/logfile
            log.close()
        os.remove(file_temp.name)

        return exit_code, data, error