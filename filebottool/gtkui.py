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
    """builds and runs the rename dialog.
    """
    def __init__(self, dialog_settings):
        """sets up the dialog using the settings supplied by the server
        Also loads relevant glade widgets as members
        """
        self.torrent_id = dialog_settings["torrent_id"]
        self.files = dialog_settings["files"]
        self.ui_settings = dialog_settings["rename_dialog_last_settings"]

        self.glade = gtk.glade.XML(get_resource("rename.glade"))
        self.window = self.glade.get_widget("rename_dialog")
        self.files_treeview = self.glade.get_widget("files_treeview")
        self.database_combo = self.glade.get_widget("database_combo")
        self.rename_action_combo = self.glade.get_widget("rename_action_combo")
        self.on_conflict_combo = self.glade.get_widget("on_conflict_combo")
        self.episode_order_combo = self.glade.get_widget("episode_order_combo")

        self.format_string_entry = self.glade.get_widget("format_string_entry")
        self.query_entry = self.glade.get_widget("query entry")
        self.download_subs_checkbox = self.glade.get_widget(
            "download_subs_checkbox")
        self.language_code_entry = self.glade.get_widget("language_code_entry")
        self.encoding_entry = self.glade.get_widget("encoding_entry")

        signal_dic = {"on_toggle_advanced": self.on_toggle_advanced}

        self.glade.signal_autoconnect(signal_dic)

        combo_data = {}
        for key in dialog_settings:
            try:
                if key.startswith('valid_'):
                    combo_data[key] = dialog_settings[key]
            except KeyError:
                pass

        self.build_combo_boxes(combo_data)
        self.populate_with_settings(self.ui_settings)
        self.build_treestore()
        self.load_treestore()

        treeview = self.glade.get_widget("files_treeview")
        treeview.expand_all()
        self.window.show()

    def build_combo_boxes(self, combo_data):
        """builds the combo boxes for the dialog"""
        log.debug("building database combo box")
        databases = combo_data["valid_databases"]
        self.inflate_list_store_combo(databases, self.database_combo)

        log.debug("building rename action combo box")
        rename_actions = combo_data["valid_rename_actions"]
        self.inflate_list_store_combo(rename_actions, self.rename_action_combo)

        log.debug("building on conflict combo box")
        on_conflicts = combo_data["valid_on_conflicts"]
        self.inflate_list_store_combo(on_conflicts, self.on_conflict_combo)

        log.debug("building episode order combo box")
        episode_orders = combo_data["valid_episode_orders"]
        self.inflate_list_store_combo(episode_orders, self.episode_order_combo)

    def inflate_list_store_combo(self, model_data, combo_widget):
        """inflates an individual combo box"""
        list_store = gtk.ListStore(str)
        for datum in model_data:
            list_store.append([datum])

        combo_widget.set_model(list_store)
        renderer = gtk.CellRendererText()
        combo_widget.pack_start(renderer, expand=True)
        combo_widget.add_attribute(renderer, "text", 0)

    def populate_with_settings(self, settings):
        """presets the window with the last settings used in the plugin"""
        log.debug("Previous settings received: {}".format(settings))
        combo_value_pairs = [
            (self.database_combo, settings["database"]),
            (self.rename_action_combo, settings["rename_action"]),
            (self.on_conflict_combo, settings["on_conflict"]),
            (self.episode_order_combo, settings["episode_order"])
        ]

        for combo, value in combo_value_pairs:
            combo_model = combo.get_model()
            value_index = [index for index, row in enumerate(combo_model)
                           if row[0] == value][0]
            if not value_index:
                log.warning("could not set {1} to value {2}, value {2} could "
                            "not be found in {1}".format(combo, value))
            else:
                combo.set_active(value_index)

        entry_value_pairs = [
            (self.format_string_entry, settings["format_string"]),
            (self.encoding_entry, settings["encoding"]),
            (self.language_code_entry, settings["language_code"]),
            (self.query_entry, settings["query"])
        ]

        for entry, value in entry_value_pairs:
            if value:
                entry.set_text(value)

        advanced_options = self.glade.get_widget("advanced_options")
        if advanced_options.get_visible() != settings["show_advanced"]:
            self.on_toggle_advanced()

        if self.download_subs_checkbox.get_active() != settings["download_subs"]:
            self.on_download_subs_toggled()

    def build_treestore(self):
        """builds the treestore that will be used to hold the files info"""
        model = gtk.TreeStore(int, str, str)
        log.debug("loading treestore with files: {}".format(self.files))
        file_index_name_pairs = [(f["index"], f["path"]) for f in self.files]
        file_index_name_pairs = sorted(file_index_name_pairs)
        for index, file_path in file_index_name_pairs:
            model.append(None, [index, file_path, ''])
        self.files_treeview.set_model(model)
        renderer = gtk.CellRendererText()
        original_files = gtk.TreeViewColumn("Original Files", renderer, text=1)
        moved_files = gtk.TreeViewColumn("Moved Files", renderer, text=2)
        self.files_treeview.append_column(original_files)
        self.files_treeview.append_column(moved_files)
        self.files_treeview.expand_all()

        #  TODO: add allow let tree track folder hierarchy work in isoltation
        #  for speed

    def load_treestore(self):
        """populates the treestore using the torrent data given to dialog"""
        pass

    #  Section: UI actions

    def on_download_subs_toggled(self, *args):
        subs_options = self.glade.get_widget("subs_options")
        if subs_options.get_sensitive():
            subs_options.set_sensitive(False)
        else:
            subs_options.set_sensitive(True)

    def on_toggle_advanced(self, *args):
        advanced_options = self.glade.get_widget("advanced_options")
        arrow = self.glade.get_widget("advanced_arrow")
        advanced_lable = self.glade.get_widget("show_advanced_lable")

        if advanced_options.get_visible():
            advanced_options.hide()
            advanced_lable.set_text("Show Advanced")
            arrow.set(gtk.ARROW_RIGHT, gtk.SHADOW_NONE)
        else:
            advanced_options.show()
            advanced_lable.set_text("Hide Advanced")
            arrow.set(gtk.ARROW_DOWN, gtk.SHADOW_NONE)


class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("FileBotTool",
                                              self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs",
                                                     self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs",
                                                     self.on_show_prefs)

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
        rename_dialog = RenameDialog(dialog_info)

    def disable(self):
        component.get("Preferences").remove_page("FileBotTool")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)
        component.get("MenuBar").torrentmenu.remove(self.menu_item)

    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('Format expression info button was clicked')

    def on_apply_prefs(self):
        log.debug("applying prefs for FileBotTool")
        client.filebottool.set_config(self.config)

    def on_show_prefs(self):
        client.filebottool.get_config().addCallback(self.on_get_config)

    def on_get_config(self, config):
        self.config = config

    def on_get_version(self, version):
        "callback for on show_prefs"
        self.glade.get_widget("filebot_version").set_text(version)