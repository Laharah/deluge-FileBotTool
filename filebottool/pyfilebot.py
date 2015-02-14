"""Contains functions for interaction with the filebotCLI and the
FilebotHandler convenience class.
"""
__author__ = 'Lunchbox'
__version__ = 0.2

import subprocess
import re
import os
import tempfile
import inspect
import sys
from types import MethodType
import functools


FILEBOT_MODES = [
    'rename',
    'move',
    'check',
    'get-missing-subtitles',
    'get-subtitles',
    'list',
    'mediainfo'
]


FILEBOT_ORDERS = [
    None,
    "dvd",
    "airdate",
    "absolute"
]


FILEBOT_DATABASES = [
    None,
    'TheTVDB',
    'TvRage',
    'AniDB',
    'OpenSubtitles',
    'TheMovieDB',
    'OMDb',
    'AccoustID',
    'ID3 Tags'
]


FILEBOT_RENAME_ACTIONS = [
    None,
    'move',
    'copy',
    'duplicate',
    'keeplink',
    'symlink',
    'hardlink',
    'test'
]


FILEBOT_ON_CONFLICT = [
    None,
    'override',
    'skip',
    'fail'
]


class Error(Exception):
    """Error baseclass for module"""
    def __init__(self, msg=None):
        self.msg = msg

class FilebotFatalError(Error):
    """raise on a non-recoverable error, such as filebot not found"""
    pass

class FilebotRuntimeError(Error):
    """raised when filebot has a non-zero exit code"""
    pass

def get_version():
    """returns the filebot version string. Usefull for testing if filebot is
    installed."""
    return_code, output, error_data = _execute(['-version'], workaround=False)
    if return_code != 0:
        return 'FileBot Not Found!', error_data

    else:
        return output.strip()


def rename(targets, format_string=None, database=None, output=None,
           rename_action='move', episode_order=None, on_conflict=None,
           query_override=None, non_strict=True, recursive=True):
    """Renames file or files from *targets* using the current settings

    Args:
        target: the file/folder or list of files/folders you want filebot to
            execute against.
        format_string: The filename formatting string you want filebot to use.
             Defaults to None which will use the filebot defaut format.
        database: the database filebot should match against. leave None to
            allow filebot to decide for you.
        rename_action: (move | copy | keeplink | symlink | hardlink | test)
            use "test" here to test output without changing files. defaults to
            move.
        episode_order: (dvd | airdate | absolute). None uses filebot's
            default season:episode order
        output: The directory filebot should output files to.
        on_conflict: (override, skip, fail). what to do when filebot
            encounters a naming conflict. Defaults to skip.
        query_override: sets the query filebot should match against rather
            than the file name. Useful if matches are returning incorrect.
        non_strict: generally kept on to allow filebot more leeway when
            identifying files. set to False if you want to force an exact
            match. Defaults to True
        recursive: process folders recursively. Defaults to True
    Returns:
        a tuple consisting of:
            -number of processed files
            -list of tuples containing (old, new) file locations OR error
                message
            -number of skipped files
    """

    if output:
        output = os.path.abspath(os.path.expandvars(os.path.expanduser(output)))

    exit_code, data, filebot_error = (
        _build_filebot_arguments(targets, format_string=format_string,
                                 database=database, output=output,
                                 rename_action=rename_action,
                                 episode_order=episode_order,
                                 on_confilct=on_conflict,
                                 query_override=query_override,
                                 non_strict=non_strict, recursive=recursive))

    #  TODO:better error handling

    if exit_code != 0:
        raise FilebotRuntimeError("FILEBOT OUTPUT DUMP:\n{}".format(
            data.encode("UTF-8")))

    return parse_filebot(data)


def parse_filebot(data):
    """Parses the output of a filebot run and returns relevant information

    parses and gives info about number of files processed, their moves, and
    files that were skipped.
    NOTE: data should be pre-decoded as utf-8

    Args:
        data: a string containing the output of a filebot run

    Returns:
        a tuple in format (num processed files, list of movement tuples,
                           skipped/failed files)
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
        match = (
            re.search(r'(?:\[\w+\] )?.*?\[(.*?)\] (?:(?:to)|(?:=>)) \[(.*?)\]',
                      line))
        if match:
            file_moves.append((match.group(1), match.group(2)))

    return total_processed_files, file_moves, skipped_files


def test_format_string(format_string=None,
                       file_name="Citizen Kane.avi"):
    """Runs a quick test of a format string and returns renamed sample
     filename

    Useful for testing to see if filebot will correctly parse a format
    string. By default uses a movie title, you must pass a custom filename
    to test a tv show style format string.

    Args:
        format_string: the string to be tested. defaults to filebot's default
         format.
        file_name: a string that contains an (imaginary) file name to
            test the format string against. defaults to a movie.

    Returns:
        a string containing the renamed file_name using the format_string.
            Returns an empty string if no matches were found.
    """

    _, data, _ = _build_filebot_arguments(file_name, rename_action='test',
                                          format_string=format_string)
    _, file_moves, _ = parse_filebot(data)
    if not file_moves:
        return ""
    else:
        return file_moves[0][1]


def get_subtitles(target, language_code=None, encoding=None,
                  force=False, output=None):
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

    if output:
        output = output.lower().strip
        if output != 'srt':
            raise ValueError("Only None and srt are valid output "
                                       "arguments for subtitle mode.")

    _, data, _ = _build_filebot_arguments(target, mode=mode,
                                          language_code=language_code,
                                          encoding=encoding, output=None)
    _, downloads, _ = parse_filebot(data)
    return [name[1] for name in downloads]


def get_history(targets):
    """returns the filebot history of given targets on a file by
        file basis.

    Uses the filebot fn:history script to get the history of each target.

    Args:
        targets: file/folder or list of files/folders you want the
            filebot history of.

    Returns:
        list of tuples in format (current_filename, previous_filename)
    """
    if isinstance(targets, basestring):
        targets = [targets]
    targets = [os.path.expanduser(os.path.expandvars(target))
               for target in targets]
    _, data, _ = _build_script_arguments("fn:history", targets)
    _, file_moves, _ = parse_filebot(data)
    file_moves = [(x[1], x[0]) for x in file_moves]  # swaps entries for
    # clarity

    return file_moves


def revert(targets):
    """reverts the given targets to the most previous point in their
        filebot history

    uses the filebot fn:revert script to revert the given files or folders

    Args:
        targets: file/folder or list of files/folders to revert

    Returns:
        a list of tuples containing the file movements in format (old, new).
    """
    if isinstance(targets, basestring):
        targets = [targets]
    targets = [os.path.expanduser(os.path.expandvars(target))
               for target in targets]
    _, data, _ = _build_script_arguments("fn:revert", targets)
    file_moves = parse_filebot(data)

    return file_moves


def _order_is_valid(order_string):
    """Checks if an order argument is valid

    None passing non evaluates to true as it uses filebot's default ordering

    Args:
        order_string: valid orders:(None | 'airdate' | 'dvd' | 'absolute')

    Returns:
        True or False based on success
    """
    if order_string is not None:
        order_string = order_string.lower()
    if order_string in FILEBOT_ORDERS:
        return True
    else:
        return False


def _mode_is_valid(mode_string):
    """Checks if mode argument is valid
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
        True if valid, False if not.
    """
    if mode_string.startswith('-'):
        mode_string = mode_string[1:]

    if mode_string.lower() not in FILEBOT_MODES:
        return False
    else:
        return True


def _database_is_valid(database):
    """checks if a given database is valid

    None returns true, as it lets filebot decide the database

        Args:
            database: the database filebot should use
                Valid databases include:
                    TheTVDB
                    TvRage
                    AniDB
                    OpenSubtitles
                    TheMovieDB
                    IMDB

    Returns: True if valid Database, False if not
    """
    valid_databases = [db.lower() for db in FILEBOT_DATABASES if db is not None]
    if database is not None:
        database = database.lower()
    if database in valid_databases or database is None:
        return True
    else:
        return False


def _rename_action_is_valid(action_string):
    """Checks if rename_action argument is valid

    Args:
        action_string:the argument passed to the --action flag
            valid actions: None, | move | copy | keeplink | symlink | hardlink

    Returns: True if valid action, False if not.

    """
    if action_string is not None:
        action_string = action_string.lower()
    if action_string in FILEBOT_RENAME_ACTIONS:
        return True
    else:
        return False


def _on_conflict_is_valid(on_conflict_string):
    """Checks if on_conflict argument is valid

    None returns True as it uses filebot default behavior (skip)

    Args:
        on_conflict_string: the conflict action argument.
            Valid entries:(None | override | skip | fail)

    Returns: True if valid conflict resolution, False if not
    """
    if on_conflict_string is not None:
        on_conflict_string = on_conflict_string.lower()
    if on_conflict_string in FILEBOT_ON_CONFLICT:
        return True
    else:
        return False


def _build_filebot_arguments(targets, format_string=None,
                             database=None, output=None, rename_action='move',
                             episode_order=None, mode='-rename',
                             recursive=True, language_code=None,
                             encoding=None, query_override=None,
                             on_confilct=None, non_strict=True):
    """internal function used to set arguments and execute a filebot run
        on targets.

    executes a run using the current handler settings, optionally takes an
    action and format argument

    Args:
        targets: file/folder or list of files/folders to execute on.
        format_string; the format string you would like to use
            defaults to instance format string.
        database: the database filebot should match against.
        output: The output directory for rename, srt|none for subtitles,
        sfv|md5|sha1 for checking
        rename_action; the argument for the filebotCLI '--action' flag. See
            *rename_action_is_valid* for details.
        episode_order: the episode ordering scheme filebot should use. see
            *order_is_valid* for details.
        mode: the filebot mode, see *mode_is_valid* for details.
        recursive: handle folders recursively.
        language_code: 2 letter language code to hand filebot --lang
            argument.
        encoding: output charset.
        query_override: filename query to use against database instead of
            filename.
        on_conflict: how filebot should handle conflicts, defaults to skip.
        non_strict: tells filebot to use non-strict file matching.

    Returns:
        tuple in format '(exit_code, stdoutput, stderr)'
    """
    if not _rename_action_is_valid(rename_action):
        raise ValueError("'{}' is not a valid rename action".format(
            rename_action))
    if not _order_is_valid(episode_order):
        raise ValueError("'{}' is not a valid episode order".format(
            episode_order))
    if not _database_is_valid(database):
        raise ValueError("'{}' is not a valid filebot database"
                                   .format(database))
    if not _mode_is_valid(mode):
        raise ValueError("'{}' is not a valid filebot mode".format(
            mode))
    if not _on_conflict_is_valid(on_confilct):
        raise ValueError("'{}' is not a valid conflict resolution."
                                   .format(on_confilct))

    if not mode.startswith('-'):
        mode = '-' + mode
    process_arguments = [mode]

    if format_string:
        process_arguments.append("--format")
        process_arguments.append(format_string)
    if database:
        process_arguments.append("--db")
        process_arguments.append(database)
    if output:
        process_arguments.append("--output")
        process_arguments.append(output)
    if rename_action:
        process_arguments.append("--action")
        process_arguments.append(rename_action)
    if recursive:
        process_arguments.append("-r")
    if episode_order:
        process_arguments.append("--order")
        process_arguments.append(episode_order)
    if query_override:
        process_arguments.append("--q")
        process_arguments.append(query_override)
    if language_code:
        process_arguments.append("--lang")
        process_arguments.append(language_code)
    if encoding:
        process_arguments.append("--encoding")
        process_arguments.append(encoding)
    if on_confilct:
        process_arguments.append("--conflict")
        process_arguments.append(on_confilct)
    if non_strict:
        process_arguments.append('-non-strict')

    if isinstance(targets, basestring):
        targets = os.path.expanduser((os.path.expandvars(targets)))
        process_arguments.append(targets)
    else:
        targets = [os.path.expanduser(os.path.expandvars(target))
                   for target in targets]
        process_arguments += [target.decode("utf8") for target in targets]

    return _execute(process_arguments)


def _build_script_arguments(script_name, script_arguments):
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
    if script_arguments:
        if isinstance(script_arguments, basestring):
            script_arguments = [script_arguments]
        process_arguments += [arg.decode("utf8") for arg in script_arguments]

    return _execute(process_arguments)


def _execute(process_arguments, workaround=True):
    """underlying execution method to call filebot as subprocess

    Handles the actual execution and output capture

    Args:
        process_arguments: list of the arguments to be passed to filebotCLI
        workaround: implements a work around for capturing unicode
            characters on windows systems. should always be true except in
            special circumstances.

    Returns:
        tuple in format '(exit_code, stdout, stderr)'
    """
    # open and close a temp file so filebot can use it as a log file.
    # this is a workaround for malfunctioning UTF-8 chars in Windows.
    file_temp = tempfile.NamedTemporaryFile(delete=False)
    file_temp.close()
    process_arguments = (["filebot", "--log-file", file_temp.name] +
                         process_arguments)

    if os.name == "nt":  # used to hide cmd window popup
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    else:
        startupinfo = None

    try:
        process = subprocess.Popen(process_arguments, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   startupinfo=startupinfo)
    except OSError:
        raise FilebotFatalError("Filebot could not be found!")

    process.wait()
    stdout, error = process.communicate()
    exit_code = process.returncode

    if workaround:
        with open(file_temp.name, 'rU') as log:
            data = log.read().decode('utf8')  # read and cleanup temp/logfile
            log.close()
    else:
        data = stdout

    os.remove(file_temp.name)

    return exit_code, data, error


class FilebotHandler(object):
    """A convenience class for interacting with filebot.

    contains attributes for storing often used filebot settings as well as
    error checking on arguments. Implements module functions as methods
    replacing the arguments with attributes stored in the class. Methods are
    used exactly like the module functions except that they will use the
    handler attributes as default arguments.
    NOTE: Methods are generated at __init__ dynamically using the module level
    functions. If you are subclassing the handler be sure to call super(
    __init__)

    Examples:
        test_format_string, when called from the handler uses handler
            attributes as defaults

        #>>> fb_handler = pyfilebot.FilebotHandler()
        #>>> fb_handler.format_string = '{n} made in {y}'
        #>>> fb_handler.test_format_string()
        u'Citizen Kane made in 1941.avi'

        to ignore handler attributes, simply pass the arguments you want
            to use
        #>>> fb_handler.test_format_string('{n} ({d})')
        u'Citizen Kane (1941-05-01).avi'

        or
        #>>> fb_handler.test_format_string(format_string='{n} ({y})')
        u'Citizen Kane (1941).avi'

    Attributes:
        format_string: the format string you would like filebot to use. None
            uses filebot default.
            for details see: http://www.filebot.net/naming.html
        database: the database filebot should match against.
            (TVRage | TheTVDB | IMDB | TheMovieDB | AniDB | OpenSubtitles).
            Leave None to allow filebot to decide for you.
        output: for rename, the output location for files.
            for checking, sfv|md5|sha1. (filebot defaults to sfv)
            for subtitles: None|srt (re-encode subtitles)
        episode_order: (dvd | airdate | absolute). None uses filebot's
            default season:episode order
        rename_action: (move | copy | keeplink | symlink | hardlink | test)
            use "test" here to test output without changing files. defaults to
            move.
        recursive: Process folders recursively. Defaults to True
        language_code: The 2 letter language code filebot should use for
            subtitles. None uses the filebot default
        encoding: The charset filebot should use for file output
        on_conflict: The action filebot should take on a file conflict.
            (skip | override | fail). Defaults to skip
        non_strict: allow filebot more leeway when identifying files. Defaults
             to true
        mode: the function you would like filebot to execute. Defaults to
            'rename'. Very rarely used

    Methods:
        Implements all the functions in pyfilebot as methods using handler
        settings where appropriate.
        has these
        additional methods:

        get_settings(): returns a dictionary containing all the current
            handler settings and their values
    """

    def __init__(self, format_string=None, database=None, output=None,
                 episode_order=None, rename_action=None, recursive=True,
                 language_code=None, encoding='UTF-8', on_conflict='skip',
                 query_override=None, non_strict=True, mode='rename'):

        self.format_string = format_string
        self._database = None
        self.database = database
        self.output = output
        self._episode_order = None
        self.episode_order = episode_order
        self._rename_action = None
        self.rename_action = rename_action
        self.recursive = recursive
        self.language_code = language_code
        self.encoding = encoding
        self._on_conflict = 'skip'
        self.on_conflict = on_conflict
        self.non_strict = non_strict
        self.query_override = query_override
        self._mode = 'rename'
        self.mode = mode

        self._populate_methods()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        if _mode_is_valid(value):
            self._mode = value
        else:
            raise ValueError('"{}" is not a valid filebot mode.'.format(value))

    @property
    def database(self):
        return self._database

    @database.setter
    def database(self, value):
        if _database_is_valid(value):
            self._database = value
        else:
            raise ValueError('"{}" is not a valid filebot database'.format(
                value))

    @property
    def episode_order(self):
        return self._episode_order

    @episode_order.setter
    def episode_order(self, order):
        if _order_is_valid(order):
            self._episode_order = order
        else:
            raise ValueError('"{}" is not a valid episode order'.format(order))

    @property
    def rename_action(self):
        return self._rename_action

    @rename_action.setter
    def rename_action(self, action):
        if _rename_action_is_valid(action):
            self._rename_action = action
        else:
            raise ValueError('"{}" is not a valid rename action.'.format(
                action))

    @property
    def on_conflict(self):
        return self._on_conflict

    @on_conflict.setter
    def on_conflict(self, value):
        if _on_conflict_is_valid(value):
            self._on_conflict = value
        else:
            raise ValueError('"{}" is not a valid conflict resolution'.format(
                value))

    def _populate_methods(self):
        """populates the class methods with public functions from the module"""
        to_add = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        to_add = [f[0] for f in to_add if not f[0].startswith('_')]
        for func_name in to_add:
            func = getattr(sys.modules[__name__], func_name)
            self._add_function_as_method(func_name, func)

    def _add_function_as_method(self, func_name, func):
        """used to add a module function as a method for this class"""
        @functools.wraps(func)
        def function_template(self, *args, **kwargs):
            """template for added methods"""
            return self._pass_to_function(func, *args, **kwargs)
        setattr(FilebotHandler, func_name, MethodType(function_template, None,
                                                      FilebotHandler))

    def get_settings(self):
        """returns a dict containing all the current handler settings"""
        handler_vars = vars(self).copy()
        for var in handler_vars.keys():
            if var.startswith('_'):
                handler_vars[var[1:]] = handler_vars[var]
                del handler_vars[var]
        return handler_vars

    def _pass_to_function(self, function, *overrided_args, **overrided_kwargs):
        """used set the function arguments to attributes found in this class.
         Also allows for argument replacement by the user"""
        functon_kwargs = inspect.getargspec(function)[0][len(overrided_args):]
        handler_vars = self.get_settings()
        kwargs_to_pass = {}

        for arg in functon_kwargs:
            if arg in handler_vars:
                kwargs_to_pass[arg] = handler_vars[arg]
        for arg in overrided_kwargs:
            kwargs_to_pass[arg] = overrided_kwargs[arg]

        return function(*overrided_args, **kwargs_to_pass)
