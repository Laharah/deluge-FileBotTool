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
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
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


from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
from twisted.internet import threads, defer


import pyfilebot
from common import Log


log = Log()


DEFAULT_PREFS = {
    "rename_dialog_last_settings": {
        "database": None,
        "format_string": None,
        "rename_action": None,
        "show_advanced": False,
        "query": None,
        "on_conflict": None,
        "episode_order": None,
        "download_subs": False,
        "language_code": None,
        "encoding": "UTF-8"
    }
}


class Core(CorePluginBase):
    """The Plugin Core"""

    def enable(self):
        self.config = deluge.configmanager.ConfigManager("filebottool.conf", DEFAULT_PREFS)

        self.handler = pyfilebot.FilebotHandler()
        try:
            self.fb_version = pyfilebot.get_version()
            log.info("Filebot Found with version {}".format(self.fb_version))
        except pyfilebot.FilebotFatalError:
            log.error("Filebot cannot be found!")
            self.filebot_version = None

        self.torrent_manager = component.get("TorrentManager")
        self.listening_dictionary = {}
        #  a dictionary of specific events to listen for (generally
        # file/folder movement events)

    def _get_filebot_target(self, torrent_id):
        """returns the path of the file or folder that filebot should target

        returns: path
        """
        log.debug("getting top level for torrent {}".format(torrent_id))
        torrent = self.torrent_manager[torrent_id]
        target = os.path.join(torrent.get_status(["save_path"])["save_path"],
                              torrent.get_status(["name"])["name"])
        log.debug("target found: {}".format(target))
        return target

    def _configure_filebot_handler(self, settings, handler=None):
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
        "episode_order",
        "rename_action",
        "recursive",
        "language_code",
        "encoding",
        "on_conflict",
        "non_strict",
        "mode"
        ]
        for attribute in valid_handler_attributes:
            if attribute in settings:
                try:
                    handler.__setattr__(attribute, settings[attribute])
                except pyfilebot.FilebotArgumentError:
                    log.warning("{} is not a valid value for {}, "
                                "skipping...".format(settings[attribute],
                                                     attribute))
        return handler

    def _file_movement_safty_check(self, torrent_id, target):
        """executes a dry run to see if a filebot run will be torrent-safe
        returns: True if torrent-safe, False if not
        """
        pass

    def _translate_filebot_movements(self, torrent_id, filebot_moves):
        """translates a filebot run into deluge torrent info

        returns: tuple(new_path, new_toplevel, [(index, new file/), ...])
        """

        torrent = self.torrent_manager[torrent_id]
        current_save_path = torrent.get_status(["save_path"])["save_path"]
        current_files = torrent.get_files()
        renames = {}
        for f in current_files:
            renames[self._get_full_os_path(current_save_path, f["path"])] = {
                "index": f["index"]}

        #  check for easy case, no save path movement

        #  compact the relative moves filebot returns into absolute paths
        filebot_moves = [(m[0], os.path.abspath(os.path.join(
                                                os.path.dirname(m[0]), m[1])))
                         for m in filebot_moves]
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
            new_save_path = os.path.dirname(renames[renames.keys()[0]][
                "new_path"])

        #  build filemove tuples by striping out new_save_path
        #  spliting on sep, and joining with '/'
        deluge_moves = []
        for old in renames:
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
        if new_save_path == current_save_path:
            new_save_path = None
        return new_save_path, gcd, deluge_moves

    def _get_full_os_path(self, save_path, deluge_path):
        """given a save path and a deluge file path, return the actual os
        path of a given file"""
        return os.path.sep.join(save_path.split(os.path.sep) +
                                deluge_path.split('/'))

    def _get_mockup_files_dictionary(self, torrent_id, translation):
        """Given a translation from _translate_filebot_movements, return a
        mock-up of what the new files will look like"""
        torrent = self.torrent_manager[torrent_id]
        new_files = list(torrent.get_files())
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

    def _redirect_torrent_paths(self, file_movements):
        """redirects a torrent's files and save paths to the new locations.
        registers them to the listening dictionary"""
        pass

    def _check_listening_dictionary(self, event):
        """called on events, checks if the plugin has been waiting for the
        event and decides what to do."""
        pass

    def disable(self):
        pass

    def update(self):
        pass

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
        return self.fb_version

    @export
    @defer.inlineCallbacks
    def do_dry_run(self, torrent_id, handler_settings=None, handler=None):
        """does a dry run to get predicted renames.
        *returns*: a mock Torrent.files dictionary showing predicted state
        """
        handler = self._configure_filebot_handler(handler_settings, handler)
        handler.rename_action = "test"
        target = self._get_filebot_target(torrent_id)
        log.debug("running filbot dry run for torrent: {} with target {"
                  "}".format(torrent_id, target))
        filebot_results = yield threads.deferToThread(handler.rename, target)
        deluge_movements = self._translate_filebot_movements(torrent_id,
                                                             filebot_results[1])
        defer.returnValue(self._get_mockup_files_dictionary(torrent_id,
                                                            deluge_movements))

    @export
    def do_rename(self, handler_settings, torrent_id):
        """executes a filebot run"""
        pass

    @export
    def get_rename_dialog_info(self, torrent_id):
        """returns the needed variables and torrent info needed to build a
        rename dialog"""
        log.debug("dialog info requested, packing dialog info.")
        dialog_info = {}

        dialog_info["torrent_id"] = torrent_id
        torrent = self.torrent_manager[torrent_id]
        dialog_info["torrent_save_path"] = torrent.get_status(['save_path'])
        dialog_info["files"] = torrent.get_files()

        rename_dialog_last_settings = self.config["rename_dialog_last_settings"]
        dialog_info["rename_dialog_last_settings"] = rename_dialog_last_settings

        dialog_info["valid_databases"] = pyfilebot.FILEBOT_DATABASES
        dialog_info["valid_rename_actions"] = pyfilebot.FILEBOT_RENAME_ACTIONS
        dialog_info["valid_on_conflicts"] = pyfilebot.FILEBOT_ON_CONFLICT
        dialog_info["valid_episode_orders"] = pyfilebot.FILEBOT_ORDERS

        log.debug("sending dialog info to client: {}".format(dialog_info))
        return dialog_info

    @export
    def test_function(self):
        """used for testing purposes"""
        pass

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
