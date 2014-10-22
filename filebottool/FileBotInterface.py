__author__ = 'Lunchbox'

import subprocess
import re
import os
import platform
import locale

from deluge.log import LOG as log


class FileBotInterface(object):
    """Calls and interacts with filebot as a subprocess

    Attributes:
        database: the databse to use with a filebot run
        format_string: a filebot
        format string to use with a filebot run
        """
    def __init__(self):
        self.database = None
        self.format_string = None
        self.order = None
        self.filebot_mode = "-rename"
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
        process_arguments = [
            "filebot",
            self.filebot_mode,
            target.decode('utf8'),
            "-non-strict",
            "--action",
            "test",
            "-r"
        ]
        if self.format_string:
            process_arguments.append("--format")
            process_arguments.append(self.format_string)
        if self.database:
            process_arguments.append("--db")
            process_arguments.append(self.database)

        process = subprocess.Popen(process_arguments, stdout=subprocess.PIPE)
        data, error = process.communicate()
        data = data.decode(locale.getpreferredencoding())
        exit_code = process.returncode

        if exit_code != 0:
            log.error("FILEBOT ERROR:\n{}".format(data))
            return (0, "FILEBOT ERROR", 0)

        total_processed_files, suggested_moves, skipped_files = (
            self.parse_filebot(data))
        if len(suggested_moves) < 1:
            return (total_processed_files, "NO SUGGESTIONS", skipped_files)

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

