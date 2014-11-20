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

import gtk
import webbrowser

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import get_resource


class RenameDialog(object):
    """builds and runs the rename dialog
    """
    def __init__(self, dialog_settings):
        """sets up the dialog using the settings supplied by the server"""
        self.torrent_id = dialog_settings["torrent_id"]
        self.files = dialog_settings["files"]
        self.ui_settings = dialog_settings["rename_dialog_last_settings"]

        self.glade = gtk.glade.XML(get_resource("rename.glade"))
        self.window = self.glade.get_widget("rename_dialog")
        signal_dic = {}

        self.glade.siginal_autoconnect(signal_dic)

        self.build_combo_boxes()
        self.populate_with_previous_settings()
        self.build_treestore()
        self.load_treestore()

        treeview = self.glade.get_widget("files_treeview")
        treeview.expand_all()
        self.window.show()

    def build_combo_boxes(self):
        """builds models and links them up to the combo boxes"""
        pass

    def populate_with_previous_settings(self):
        """presets the window with the last settings used in the plugin"""
        pass

    def build_treestore(self):
        """builds the treestore that will be used to hold the files info"""
        pass

    def load_treestore(self):
        """populates the treestore using the torrent data given to dialog"""
        pass


class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("FileBotTool", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        # add context menu item for FileBotTool
        torrentmenu = component.get("MenuBar").torrentmenu
        self.menu_item = gtk.ImageMenuItem("FileBotTool")

        img = gtk.image_new_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_MENU)
        self.menu_item.set_image(img)
        self.menu_item.connect("activate", self.get_torrent_info)
        torrentmenu.append(self.menu_item)
        torrentmenu.show_all()

    def get_torrent_info(self, *args):
        torrent_id = component.get("TorrentView").get_selected_torrent()
        client.filebottool.get_rename_dialog_info(torrent_id).addCallback(
            self.build_rename_dialog)

    def build_rename_dialog(self, dialog_info):
        rename_dialog = RenameDialog()

    def disable(self):
        component.get("Preferences").remove_page("FileBotTool")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('Format expression info button was clicked')

    def on_apply_prefs(self):
        log.debug("applying prefs for FileBotTool")
        self.config['database'] = self.glade.get_widget("db_combo").get  # TODO
        client.filebottool.set_config(self.config)

    def on_show_prefs(self):
        client.filebottool.get_config().addCallback(self.on_get_config)
        client.filebottool.get_filebot_version().addCallback(
            self.on_get_version)

    def on_get_config(self, config):
        self.config = config

    def on_get_version(self, version):
        "callback for on show_prefs"
        self.glade.get_widget("filebot_version").set_text(version)