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

from deluge.log import LOG as delugelog
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
import pyfilebot


class Log(object):
    """small wrapper class for formatting log outputs"""

    def error(self, msg):
        delugelog.error("[FilebotTool] {}".format(msg))

    def info(self, msg):
        delugelog.info("[FilebotTool] {}".format(msg))

    def debug(self, msg):
        delugelog.debug("[FilebotTool] {}".format(msg))

    def critical(self, msg):
        delugelog.critical("[FilebotTool] {}".format(msg))

    def warning(self, msg):
        delugelog.warning("[FilebotTool] {}".format(msg))

log = Log()


DEFAULT_PREFS = {
    "rename_dialog_last_settings": {
        "database": None,
        "format_string": None,
        "show_advanced": False,
        "query": None,
        "episode_order": None,
        "download_subs": False,
        "language": None,
        "encoding": None
    },


}


class Core(CorePluginBase):
    """The Plugin Core"""

    def enable(self):
        self.config = deluge.configmanager.ConfigManager("filebottool.conf", DEFAULT_PREFS)

        self.handler = pyfilebot.FilebotHandler()
        try:
            self.fb_version = pyfilebot.get_filebot_version()
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
        torrent_files = self.torrent_manager[torrent_id].get_files()
        log.debug("files recieved: {}".format(torrent_files))
        # get dict info

    def _file_movement_safty_check(self, torrent_id, target):
        """executes a dry run to see if a filebot run will be torrent-safe
        returns: True if torrent-safe, False if not
        """
        pass

    def _translate_file_movements(self, torrent_id, filebot_moves):
        """translates a filebot run into deluge torrent info

        returns: tuple(new_save_path, [(index, new file/folder name),...])
        """
        pass

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

    #  Section: Public API

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
    def do_dry_run(self, handler_settings, torrent_id):
        """does a dry run to get predicted renames"""
        pass

    @export
    def do_rename(self, handler_settings, torrent_id):
        """executes a filebot run"""
        pass

    @export
    def get_rename_dialog_info(self, torrent_id):
        """returns the needed variables and torrent info needed to build a
        rename dialog"""
        log.debug("dialog info requested, packing dialog.")
        dialog_info = {}

        dialog_info["torrent_id"] = torrent_id
        torrent = self.torrent_manager[torrent_id]
        dialog_info["torrent_save_path"] = torrent.get_status(['save_path'])
        dialog_info["files"] = torrent.get_files()

        rename_dialog_last_settings = self.config["rename_dialog_last_settings"]
        dialog_info["rename_dialog_last_settings"] = rename_dialog_last_settings

        dialog_info["valid_databases"] = pyfilebot.FILEBOT_DATABASES
        dialog_info["valid_rename_actions"] = pyfilebot.FILEBOT_MODES
        dialog_info["valid_on_conflicts"] = pyfilebot.FILEBOT_ON_CONFLICT
        dialog_info["valid_episode_orders"] = pyfilebot.FILEBOT_ORDERS

        log.debug("sending dialog info to client: {}".format(dialog_info))
        return dialog_info

    @export
    def get_filebot_databases(self):
        return pyfilebot.FILEBOT_DATABASES

    @export
    def test_function(self):
        """used for testing purposes"""
        pass

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
