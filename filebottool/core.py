#
# core.py
#
# Copyright (C) 2009 laharah <laharah+fbt@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# The Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#
import os

# noinspection PyUnresolvedReferences
from deluge.plugins.pluginbase import CorePluginBase
# noinspection PyUnresolvedReferences
import deluge.component as component
# noinspection PyUnresolvedReferences
import deluge.configmanager
# noinspection PyUnresolvedReferences
from deluge.core.rpcserver import export
from twisted.internet import threads, defer

import pyfilebot
from common import Log
import filebottool.auto_sort_manager


log = Log()

DEFAULT_PREFS = {
    "rename_dialog_last_settings": {
        "database": None,
        "output": None,
        "format_string": None,
        "rename_action": None,
        "show_advanced": False,
        "query_override": None,
        "on_conflict": None,
        "episode_order": None,
        "download_subs": False,
        "language_code": None,
        "encoding": "UTF-8"
    },
    "saved_handlers": {},
    "plugin_preferences": {},
    "auto_sort_rules": {},
}


class Core(CorePluginBase):
    """The Plugin Core"""

    # noinspection PyAttributeOutsideInit
    def enable(self):
        self.config = deluge.configmanager.ConfigManager(
            "filebottool.conf", DEFAULT_PREFS)

        try:
            self.filebot_version = pyfilebot.get_version()
            log.info("Filebot Found with version {}".format(
                self.filebot_version))
        except pyfilebot.FilebotFatalError:
            log.error("Filebot cannot be found!")
            self.filebot_version = None

        self.torrent_manager = component.get("TorrentManager")
        self.listening_dictionary = {}

        #register event/alert hooks:
        component.get("AlertManager").register_handler("storage_moved_alert",
                                                       self._on_storage_moved)
        event_manager = component.get("EventManager")
        event_manager.register_event_handler("TorrentFolderRenamedEvent",
                                             self._on_folder_renamed)
        event_manager.register_event_handler("TorrentFileRenamedEvent",
                                             self._on_file_renamed)

        self.auto_sort_manager = filebottool.auto_sort_manager.AutoSortManager(
            self,
            sorting_rules=self.config["auto_sort_rules"]
        )

    def disable(self):
        component.get("AlertManager").deregister_handler(self._on_storage_moved)
        event_manager = component.get("EventManager")
        event_manager.deregister_event_handler("TorrentFolderRenamedEvent",
                                               self._on_folder_renamed)
        event_manager.deregister_event_handler("TorrentFileRenamedEvent",
                                               self._on_file_renamed)

    def update(self):
        pass

    #########
    #  Section: Event Handlers
    #########

    def _on_storage_moved(self, alert):
        """handler for storage movements, Checks listening dictionary if it's
         a relevant movement"""
        torrent_id = str(alert.handle.info_hash())
        log.debug("_on_storage_moved({})".format(torrent_id))
        if torrent_id not in self.listening_dictionary:
            return

        if self.listening_dictionary[torrent_id]["move_storage"]:
            del self.listening_dictionary[torrent_id]["move_storage"]

        self._check_listening_dictionary(torrent_id)

    def _on_folder_renamed(self, torrent_id, old, new):
        """handler for folder renames, Checks plugin listening dictionary and
        takes appropriate action.
        """
        log.debug("_on_folder_moved({},{}, {})".format(torrent_id, old, new))
        if torrent_id not in self.listening_dictionary:
            return

        if self.listening_dictionary[torrent_id]["folder_rename"] == (old, new):
            del self.listening_dictionary[torrent_id]["folder_rename"]

        self._check_listening_dictionary(torrent_id)

    def _on_file_renamed(self, torrent_id, index, name):
        """handler for file renames, Checks plugin listening dictionary and
        takes appropriate action."""
        log.debug("on_file_renamed({},{}, {})".format(torrent_id, index, name))
        if torrent_id not in self.listening_dictionary:
            return

        if (index, name) in self.listening_dictionary[torrent_id]:
            del self.listening_dictionary[torrent_id][(index, name)]

        self._check_listening_dictionary(torrent_id)

    def _check_listening_dictionary(self, torrent_id):
        """called after events, checks if the plugin has been waiting for the
        event and decides what to do."""
        if torrent_id in self.listening_dictionary:
            if not self.listening_dictionary[torrent_id]:
                del self.listening_dictionary[torrent_id]
                self.torrent_manager[torrent_id].resume()

        log.debug("listning dictionary updated: {}".format(
            self.listening_dictionary))

    #########
    #  Section: Filebot interaction
    #########

    # noinspection PyPep8Naming
    def _translate_filebot_movements(self, torrent_id, filebot_moves):
        """translates a filebot run into deluge torrent info
        Args:
          torrent_id
          filebot_moves: a list of movements made by filebot
        returns: tuple(new_path, new_toplevel, [(index, new file path), ...])
        """
        if not filebot_moves:
            log.info("No movements for {}".format(torrent_id))
            return
        torrent = self.torrent_manager[torrent_id]
        current_save_path = torrent.get_status(["save_path"])["save_path"]
        current_files = torrent.get_files()
        renames = {}
        for f in current_files:
            renames[self._get_full_os_path(current_save_path, f["path"])] = {
                "index": f["index"]
            }

        #  compact the relative moves filebot returns into absolute paths
        filebot_moves = [(m[0], os.path.abspath(os.path.join(
            os.path.dirname(m[0]), m[1]))) for m in filebot_moves]

        #  cross-reference
        for old, new in filebot_moves:
            try:
                renames[old]["new_path"] = new
            except KeyError:
                log.error("could not find index for {} in the torrent, problem "
                          "with movement matching.".format(old))
                raise

        #  get new top level based on gcd of new paths
        if len(current_files) > 1:
            #  gcd = Greatest Common Directory, or a torrent's top level.
            gcd = os.path.dirname(os.path.commonprefix([m[1] for m
                                                        in filebot_moves]))
            current_GCD = os.path.join(
                torrent.get_status(["save_path"])["save_path"],
                torrent.get_status(["name"])["name"])
        else:
            gcd = None
            current_GCD = None

        if gcd:
            new_save_path = os.path.dirname(gcd)
        else:
            new_save_path = os.path.dirname(
                renames[renames.keys()[0]]["new_path"])

        #  build filemove tuples by striping out new_save_path
        #  spliting on sep, and joining with '/'
        deluge_moves = []
        for old in renames:
            if "new_path" not in renames[old]:
                continue
            if old == renames[old]["new_path"]:
                #rename not needed
                continue
            index = renames[old]["index"]
            new_deluge_path = renames[old]["new_path"].replace(new_save_path,
                                                               "")[1:]
            new_deluge_path = "/".join(new_deluge_path.split(os.path.sep))
            deluge_moves.append((index, new_deluge_path))

        if gcd == current_GCD:
            gcd = None
        else:
            gcd = os.path.basename(gcd)
        if new_save_path == current_save_path:
            new_save_path = None
        return new_save_path, gcd, deluge_moves

    def _redirect_torrent_paths(self, torrent_id, (new_save_path, new_top_lvl,
                                new_file_paths), original_state=None):
        """redirects a torrent's files and save paths to the new locations.
        registers them to the listening dictionary
        Args:
            torrent_id
            a tuple from _translate_filebot_movements
        """
        torrent = self.torrent_manager[torrent_id]
        if any([new_save_path, new_top_lvl, new_file_paths]):
            self.listening_dictionary[torrent_id] = {}
        if new_save_path:
            self.listening_dictionary[torrent_id]["move_storage"] = (
                new_save_path)
            torrent.move_storage(new_save_path)
        if new_top_lvl:
            current_top_lvl = torrent.get_files()[0]["path"].split("/")[0] + "/"
            self.listening_dictionary[torrent_id]["folder_rename"] = (
                current_top_lvl, new_top_lvl + "/")
            torrent.rename_folder(current_top_lvl, new_top_lvl)
        if new_file_paths:
            for index, path in new_file_paths:
                self.listening_dictionary[torrent_id][(index, path)] = True
            torrent.rename_files(new_file_paths)

        #prefent resume if torrent was originally paused
        if original_state == "Paused":
            del self.listening_dictionary[torrent_id]

    def _file_conflicts(self, torrent_id, filebot_translation,
                              skipped_files):
        """
        builds a list of exsisting file conflicts for a given torrent rename.
        :param torrent_id:
        :param filebot_translation:
        :return: list of conflicting files
        """
        torrent = self.torrent_manager[torrent_id]
        if not filebot_translation:
            return []

        original_files = torrent.get_files()
        original_save_path = torrent.get_status(["save_path"])["save_path"]
        mockup = self._get_mockup_files_dictionary(torrent_id,
                                                   filebot_translation)
        new_files = mockup
        new_save_path = filebot_translation[0]
        if not new_save_path:
            new_save_path = original_save_path

        original_files = [(f["index"], f["path"]) for f in original_files]
        new_files = [(f["index"], f["path"]) for f in new_files]
        original_paths = [self._get_full_os_path(original_save_path, f[1])
                          for f in sorted(original_files)]
        new_paths = [self._get_full_os_path(new_save_path, f[1]) for
                     f in sorted(new_files)]

        extra_files = []
        for f in mockup:
            if f["index"] not in [x[0] for x in filebot_translation[2]]:
                extra_files.append(
                    self._get_full_os_path(new_save_path, f["path"]))

        conflicts = []

        for original_path, new_path in zip(original_paths, new_paths):
            if new_path == original_path:
                continue
            if (original_path not in skipped_files and
                    new_path not in extra_files):
                continue
            if os.path.exists(new_path):
                conflicts.append(new_path)

        return conflicts

    @defer.inlineCallbacks
    def _rollback(self, filebot_movements, torrent_id):
        targets = [pair[1] for pair in filebot_movements[1]]
        try:
            results = yield threads.deferToThread(pyfilebot.revert, targets)
        except pyfilebot.FilebotRuntimeError, err:
            log.error("FILEBOT ERROR: {}".format(err))
            defer.returnValue(None)
        # noinspection PyUnboundLocalVariable
        log.info("Successfully rolled back files: {}".format(results[1]))
        log.info("forcing recheck on {}".format(torrent_id))
        self.torrent_manager[torrent_id].force_recheck()

    #########
    #  Section: Utilities
    #########

    def _get_filebot_target(self, torrent_id):
        """returns the path of the file or folder that filebot should target
        Args: torrent_id: torrent_id
        returns: path
        """
        log.debug("targets list for torrent {}".format(torrent_id))
        torrent = self.torrent_manager[torrent_id]
        save_path = torrent.get_status(["save_path"])["save_path"]
        targets = [self._get_full_os_path(save_path, f["path"]) for f in
                   torrent.get_files()]
        log.debug("targets found: {}".format(targets))
        return targets

    @staticmethod
    def _get_full_os_path(save_path, deluge_path):
        """given a save path and a deluge file path, return the actual os
        path of a given file"""
        return os.path.sep.join(save_path.split(os.path.sep) +
                                deluge_path.split('/'))

    @staticmethod
    def _configure_filebot_handler(settings, handler=None):
        """Configures a handler using the given settings dictionary.

        If no handler is given a new handler is created. Invalid settings
        will be skipped

        *settings*: a dictionary in format {"setting": value, ...}
        *handler*: the handler you want to use, defaults to new Handler

        *returns*: a configured handler.
        """
        if not handler:
            handler = pyfilebot.FilebotHandler()

        valid_handler_attributes = [
            "format_string",
            "database",
            "output",
            "episode_order",
            "rename_action",
            "recursive",
            "language_code",
            "encoding",
            "on_conflict",
            "query_override",
            "non_strict",
            "mode"
        ]
        for attribute in valid_handler_attributes:
            if attribute in settings:
                try:
                    handler.__setattr__(attribute, settings[attribute])
                except ValueError:
                    log.warning("{} is not a valid value for {}, "
                                "skipping...".format(settings[attribute],
                                                     attribute))
        return handler

    def _get_mockup_files_dictionary(self, torrent_id, translation):
        """Given a translation from _translate_filebot_movements, return a
        mock-up of what the new files will look like"""
        torrent = self.torrent_manager[torrent_id]
        new_files = list(torrent.get_files())
        if not translation:
            return new_files
        _, new_top_level, new_paths = translation

        if new_top_level:
            for f in new_files:
                old_top_level = f["path"].split("/")[0]
                f["path"] = f["path"].replace(old_top_level, new_top_level, 1)

        for index, new_path in new_paths:
            for f in new_files:
                if f["index"] == index:
                    f["path"] = new_path

        return new_files

    #########
    #  Section: Public API
    #########

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_filebot_version(self):
        return self.filebot_version

    @export
    @defer.inlineCallbacks
    def do_dry_run(self, torrent_id, handler_settings=None, handler=None):
        """does a dry run to get predicted renames.
        *returns*: a tuple containing the new save path and a mock
          Torrent.files dictionary showing predicted state
        """
        if not handler:
            if handler_settings:
                handler = self._configure_filebot_handler(handler_settings,
                                                          handler)
            else:
                handler = pyfilebot.FilebotHandler()

        handler.rename_action = "test"
        target = self._get_filebot_target(torrent_id)
        log.debug("running filbot dry run for torrent: {} with target {"
                  "}".format(torrent_id, target))
        try:
            filebot_results = yield threads.deferToThread(handler.rename,
                                                          target)
        except pyfilebot.FilebotRuntimeError as err:
            log.error("FILEBOT ERROR: {}".format(err.msg))
            defer.returnValue(((False, {torrent_id:(str(err), err.msg)}),
                              ('FILEBOTERROR', err.msg)))
        # noinspection PyUnboundLocalVariable
        log.debug("recieved results from filebot: {}".format(filebot_results))
        deluge_movements = self._translate_filebot_movements(torrent_id,
                                                             filebot_results[1])
        if not deluge_movements:
            new_save_path = self.torrent_manager[torrent_id].get_status(
                ["save_path"])["save_path"]
            defer.returnValue(((True, None), (new_save_path, self.torrent_manager[
                torrent_id].get_files())))

        log.debug("REQUIRED DELUGE MOVEMENTS: {}".format(deluge_movements))
        new_save_path = deluge_movements[0]
        if not new_save_path:
            new_save_path = None

        if not new_save_path:
            new_save_path = self.torrent_manager[torrent_id].get_status(
                ["save_path"])["save_path"]
        conflicts = self._file_conflicts(torrent_id, deluge_movements, filebot_results[2])
        if conflicts:
            errors = {}
            errors[torrent_id] = ('File Conflict',
                                  'The following files already exsist:\n{}'.format(
                                    ''.join('    ' + f + '\n' for f in conflicts))
                                  )
        defer.returnValue((
            (True if not conflicts else False, None if not conflicts else errors),
            (new_save_path,
             self._get_mockup_files_dictionary(torrent_id, deluge_movements))))

    @export
    @defer.inlineCallbacks
    def do_rename(self, torrent_ids, handler_settings=None, handler=None):
        """executes a filebot run.
        Args:
            torrent_id: id of torrent to execute against
            handler_settings: an optional dictionary of settings build a filebot
                handler from
            handler: an optional FilebotHandler to use (overrides
                handler_settings)
        returns:
            True if successful, False with "msg" kwarg if some error occurred.
        """
        if not handler:
            if handler_settings:
                handler = self._configure_filebot_handler(handler_settings,
                                                          handler)
            else:
                handler = pyfilebot.FilebotHandler()

        errors = {}
        for torrent_id in torrent_ids:
            target = self._get_filebot_target(torrent_id)
            log.debug("beginning filebot run on torrent {}, with target {"
                      "}".format(torrent_id, target))

            original_torrent_state = self.torrent_manager[torrent_id].state
            self.torrent_manager[torrent_id].pause()

            try:
                filebot_results = yield threads.deferToThread(handler.rename,
                                                              target)
            except pyfilebot.FilebotRuntimeError as err:
                log.error("FILEBOT ERROR{}".format(err))
                errors[torrent_id] = (str(err), err.msg)
                filebot_results = ["", {}, {}]
                continue

            log.debug("recieved results from filebot: {}".format(
                filebot_results))

            deluge_movements = self._translate_filebot_movements(
                torrent_id, filebot_results[1])

            if not deluge_movements:
                if original_torrent_state == "Seeding":
                    self.torrent_manager[torrent_id].resume()

            conflicts = self._file_conflicts(torrent_id,
                                             deluge_movements,
                                             filebot_results[2])

            if conflicts:
                log.warning("Raname is not safe on torrent {}. "
                            "Rolling Back and recheking".format(torrent_id))
                self._rollback(filebot_results, torrent_id)
                errors[torrent_id] = (
                    "File Conflict", "Problem with moving torrent \"{}\".\n"
                    "The following files already exsist:\n{}"
                    "Rolling back to previous state and rechecking.".format(
                    self.torrent_manager[torrent_id].get_status( ["name"])["name"],
                    ''.join('    '+f+'\n' for f in conflicts)))
                continue
            if deluge_movements:
                log.debug("Attempting to re-reoute torrent: {}".format(
                    deluge_movements))
                self._redirect_torrent_paths(
                    torrent_id, deluge_movements,
                    original_state=original_torrent_state)
        if errors:
            defer.returnValue((False, errors))
        else:
            defer.returnValue((True, None))

    @export
    @defer.inlineCallbacks
    def do_revert(self, torrent_id):
        """calls filebottool.revert() on files in a torrent. Will only allow
        one torrent at a time"""
        targets = self._get_filebot_target(torrent_id)
        log.debug("reverting torrent {} with targets {}".format(torrent_id,
                                                                targets))
        original_torrent_state = self.torrent_manager[torrent_id].state
        self.torrent_manager[torrent_id].pause()
        handler = pyfilebot.FilebotHandler()
        try:
            # noinspection PyUnresolvedReferences
            filebot_results = yield threads.deferToThread(handler.revert,
                                                          targets)
        except Exception, err:
            log.error("FILEBOT ERROR {}".format(err))
            defer.returnValue((False, err))

        # noinspection PyUnboundLocalVariable
        deluge_movements = self._translate_filebot_movements(torrent_id,
                                                             filebot_results[1])

        if not deluge_movements:
            if original_torrent_state == "Seeding":
                self.torrent_manager[torrent_id].resume()
            defer.returnValue((True, None))

        conflicts = self._file_conflicts(torrent_id,
                                         deluge_movements,
                                         filebot_results[2])
        if conflicts:
            log.warning('Rename unsafe for torrent {}, conflicting files:{}'.format(
                torrent_id, conflicts))
            log.warning('Rolling back torrent {}.'.format(torrent_id))
            self._rollback(filebot_results, torrent_id)
            defer.returnValue((False, "Rename is not safe on torrent {}.\n"
                               "The following files already exsist:\n"
                               "{}"
                               "Rolling Back and recheking.".format(torrent_id,
                               ''.join('    ' + f + '\n' for f in conflicts))))

        log.debug("Attempting to re-reoute torrent: {}".format(
            deluge_movements))
        self._redirect_torrent_paths(torrent_id, deluge_movements,
                                     original_state=original_torrent_state)
        defer.returnValue((True, None))

    @export
    def save_rename_dialog_settings(self, new_settings):
        log.debug("recieved settings from client: {}".format(new_settings))
        for setting in self.config["rename_dialog_last_settings"]:
            try:
                if new_settings[setting] is not None:
                    self.config["rename_dialog_last_settings"][setting] = (
                        new_settings[setting])
                    log.debug("setting saved: {} : {}".format(
                        setting, new_settings[setting]))
                else:
                    self.config["rename_dialog_last_settings"][setting] = None
            except KeyError:
                pass

        #query_override should not be saved between runs
        self.config["rename_dialog_last_settings"]["query_override"] = None
        self.config.save()

    @export
    def get_rename_dialog_info(self, torrent_ids):
        """returns the needed variables and torrent info needed to build a
        rename dialog"""
        log.debug("dialog info requested, packing dialog info.")
        dialog_info = {"torrent_ids": torrent_ids}

        if len(torrent_ids) == 1:
            torrent = self.torrent_manager[torrent_ids[0]]
            dialog_info["torrent_save_path"] = torrent.get_status(
                ['save_path'])['save_path']
            dialog_info["files"] = torrent.get_files()

        dialog_info["filebot_version"] = self.filebot_version

        rename_dialog_last_settings = self.config["rename_dialog_last_settings"]
        dialog_info["rename_dialog_last_settings"] = rename_dialog_last_settings
        dialog_info.update(self.get_filebot_valid_values())

        log.debug("sending dialog info to client: {}".format(dialog_info))
        return dialog_info

    # noinspection PyDictCreation
    @export
    def get_filebot_valid_values(self):
        """gathers valid arguments to filebot from pyfilebot.

        returns: dictionary of lists in format {"valid_databases": [
            'imdb'...]...}
        """
        valid_args = {}
        valid_args["valid_databases"] = pyfilebot.FILEBOT_DATABASES
        valid_args["valid_rename_actions"] = pyfilebot.FILEBOT_RENAME_ACTIONS
        valid_args["valid_on_conflicts"] = pyfilebot.FILEBOT_ON_CONFLICT
        valid_args["valid_episode_orders"] = pyfilebot.FILEBOT_ORDERS
        return valid_args

    @export
    def update_handlers(self, handlers):
        log.debug("Updating saved handlers: {}".format(handlers))
        self.config["saved_handlers"] = handlers
        self.config.save()

    @export
    def test_function(self):
        """used for testing purposes"""
        pass

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
