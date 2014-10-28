"""Contains functions for interaction with the filebotCLI and the
FilebotHandler convenience class.
"""
__author__ = 'Lunchbox'

import subprocess
import re
import os
import tempfile
import inspect
import sys
from types import MethodType


class Error(Exception):
    """Error baseclass for module"""
    pass


class FilebotArgumentError(Error):
    """raised when filebot is attempted to run with invalid argument"""
    pass


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
            attrubutes as defaults

        #>>> fb_handler = pyfilebot.FilebotHandler()
        #>>> fb_handler.format_string = '{n} made in {y}'
        #>>> fb_handler.test_format_string()
        u'Citizen Kane made in 1941.avi'

        to ignore handler attributes, simply pass the arguments you want
            to use
        #>>> fb_handler.test_format_string('{n} ({d})')
        u'Citizen Kane (1941-05-01).avi'
        #>>> fb_handler.test_format_string(format_string='{n} ({y})')
        u'Citizen Kane (1941).avi'
    """

    def __init__(self):
        self.mode = None
        self.format_string = None
        self.database = None
        self.episode_order = None
        self.rename_action = None
        self.recursive = True
        self.language_code = None
        self.encoding = None
        self.on_conflict = None
        self.non_strict = True
        self._populate_methods()

    def _populate_methods(self):
        """populates the class methods with public functions from the module"""
        to_add = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        to_add = [f[0] for f in to_add if not f[0].startswith('_')]
        for func_name in to_add:
            func = getattr(sys.modules[__name__], func_name)
            self._add_function_as_method(func_name, func)

    def _add_function_as_method(self, func_name, func):
        """used to add a module function as a method for this class"""
        def function_template(self, *args, **kwargs):
            """template for added methods"""
            return self._pass_to_function(func, *args, **kwargs)
        setattr(FilebotHandler, func_name, MethodType(function_template, None,
                                                      FilebotHandler))

    def _pass_to_function(self, function, *overrided_args, **overrided_kwargs):
        """used set the function arguments to attributes found in this class.
         Also allows for argument replacement by the user"""
        functon_kwargs = inspect.getargspec(function)[0][len(overrided_args):]
        handler_vars = vars(self)
        kwargs_to_pass = {}

        for arg in functon_kwargs:
            if arg in handler_vars:
                kwargs_to_pass[arg] = handler_vars[arg]
        for arg in overrided_kwargs:
            kwargs_to_pass[arg] = overrided_kwargs[arg]

        return function(*overrided_args, **kwargs_to_pass)

#TODO: cleanup get and set functions with implemented checks
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
            self.database = database
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
            self.database = database
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
            self.mode = mode_string
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
            self.order = order_string
            return True
        else:
            return False


def parse_filebot(data):
    """Parses the output of a filebot run and returns relevant information

    parses and gives info about number of files processed, their moves, and
    files that were skipped.
    NOTE: data should be pre-decoded as utf-8

    Args:
        data: a string containing the output of a filebot run

    Returns:
        a tuple in format (num processed files, list of movement tuples,
                           skipped files)
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
        match = re.search(r'\[(.*?)\] (?:(?:to)|(?:=>)) \[(.*?)\]', line)
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


def rename(targets, format_string=None, database=None,
           rename_action='move', episode_order=None, on_conflict=None,
           query_override=None, non_strict=True, recursive=True):
    """Renames file or files from *targets* using the current settings

    Args:
        target: the file or folder you want filebot to execute against
        format_string: The filename formatting string you want filebot to use.
             Defaults to None which will use the filebot defaut format.
        database: the database filebot should match against. leave None to
            allow filebot to decide for you.
        rename_action: (move | copy | keeplink | symlink | hardlink | test)
            use "test" here to test output without changing files. defaults to
            move.
        episode_order: (dvd | airdate | absolute). None uses filebot's
            default season:episode order
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

    exit_code, data, filebot_error = (
        _build_filebot_arguments(targets, format_string=format_string,
                                 database=database,
                                 rename_action=rename_action,
                                 episode_order=episode_order,
                                 on_confilct=on_conflict,
                                 query_override=query_override,
                                 non_strict=non_strict, recursive=recursive))

    if exit_code != 0:
        return 0, "FILEBOT ERROR", 0

    return parse_filebot(data)


def get_subtitles(target, language_code=None, encoding=None,
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

    _, data, _ = _build_filebot_arguments(target, mode=mode,
                                          language_code=language_code,
                                          encoding=encoding)
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
    _, data, _ = _build_script_arguments("fn:revert", targets)
    _, file_moves, _ = parse_filebot(data)

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
    if order_string in [None, "dvd", "airdate", "absolute"]:
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

    if mode_string.lower() not in valid_modes:
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

    Returns: True if valid Database, False if not
    """
    valid_databases = [
        None,
        'thetvdbb',
        'tvrage',
        'anidb',
        'opensubtitles'
        'themoviedb'
    ]
    if database is not None:
        database = database.lower()
    if database in valid_databases:
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
    valid_rename_actions = [
        None,
        'move',
        'copy',
        'keeplink',
        'symlink',
        'hardlink',
        'test'
    ]
    if action_string is not None:
        action_string = action_string.lower()
    if action_string in valid_rename_actions:
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
    if on_conflict_string in [None, 'override', 'skip', 'fail']:
        return True
    else:
        return False


def _build_filebot_arguments(targets, format_string=None,
                             database=None, rename_action='move',
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
        raise FilebotArgumentError("'{}' is not a valid rename action".format(
            rename_action))
    if not _order_is_valid(episode_order):
        raise FilebotArgumentError("'{}' is not a valid episode order".format(
            episode_order))
    if not _database_is_valid(database):
        raise FilebotArgumentError("'{}' is not a valid filebot database"
                                   .format(database))
    if not _mode_is_valid(mode):
        raise FilebotArgumentError("'{}' is not a valid filebot mode".format(
            mode))

    if not mode.startswith('-'):
        mode = '-' + mode
    process_arguments = [mode]

    if format_string:
        process_arguments.append("--format")
        process_arguments.append(format_string)
    if database:
        process_arguments.append("--db")
        process_arguments.append(database)
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

    if isinstance(targets, str):
        process_arguments.append(targets)
    else:
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
        if isinstance(script_arguments, str):
            script_arguments = [script_arguments]
        process_arguments += [arg.decode("utf8") for arg in script_arguments]

    return _execute(process_arguments)


def _execute(process_arguments):
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
