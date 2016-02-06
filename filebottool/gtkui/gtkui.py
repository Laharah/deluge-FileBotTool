#
# gtkui.py
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

# noinspection PyUnresolvedReferences
import gtk

# noinspection PyUnresolvedReferences
from deluge.ui.client import client
# noinspection PyUnresolvedReferences
from deluge.plugins.pluginbase import GtkPluginBase
# noinspection PyUnresolvedReferences
import deluge.component as component

from filebottool.common import Log, get_resource

from rename_dialog import RenameDialog
from config_ui import ConfigUI

log = Log()


class GtkUI(GtkPluginBase):
    # noinspection PyAttributeOutsideInit,PyAttributeOutsideInit
    def enable(self):
        """actions to take on plugin enabled.
        loads preference page, and context menu.
        """
        self.config_ui = ConfigUI()
        component.get("Preferences").add_page("FileBotTool",
                                              self.config_ui.config_page)
        component.get("PluginManager").register_hook("on_apply_prefs",
                                                     self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs",
                                                     self.on_show_prefs)

        # add context menu item for FileBotTool
        torrentmenu = component.get("MenuBar").torrentmenu
        self.menu_item = gtk.ImageMenuItem("FileBotTool")
        img = gtk.image_new_from_file(get_resource("fb_icon16.png"))
        self.menu_item.set_image(img)
        self.menu_item.connect("activate", self.get_torrent_info)
        torrentmenu.append(self.menu_item)
        torrentmenu.show_all()

    def get_torrent_info(self, *args):
        """context menu has been selected on a specific torrent.
        asks server for torrent info and builds rename dialog on reply"""
        torrent_ids = component.get("TorrentView").get_selected_torrents()
        client.filebottool.get_rename_dialog_info(torrent_ids).addCallback(
            self.build_rename_dialog)

    def build_rename_dialog(self, dialog_info):
        rename_dialog = RenameDialog(dialog_info)

    def disable(self):
        """cleanup actions for when plugin is disabled.
        """
        component.get("Preferences").remove_page("FileBotTool")
        component.get("PluginManager").deregister_hook("on_apply_prefs",
                                                       self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs",
                                                       self.on_show_prefs)
        component.get("MenuBar").torrentmenu.remove(self.menu_item)

    def on_apply_prefs(self):
        log.debug("gathering prefs for FileBotTool")
        config = self.config_ui.gather_settings()
        client.filebottool.set_config(config)

    def on_show_prefs(self):
        client.filebottool.get_config().addCallback(self.on_get_config)

    # noinspection PyAttributeOutsideInit
    def on_get_config(self, config):
        log.debug("recireved config from server: {0}".format(config))
        self.config_ui.populate_settings(config)