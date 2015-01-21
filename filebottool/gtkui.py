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
import os

from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import Log
from common import get_resource

log = Log()

class RenameDialog(object):
    """builds and runs the rename dialog.
    """
    def __init__(self, dialog_settings):
        """sets up the dialog using the settings supplied by the server
        Also loads relevant glade widgets as members

        Args:
         dialog_settings: A dictionary containing the settings to populate.
        """
        self.torrent_id = dialog_settings["torrent_id"]
        self.files = dialog_settings["files"]
        self.current_torrent_save_path = dialog_settings["torrent_save_path"]
        self.ui_settings = dialog_settings["rename_dialog_last_settings"]

        self.glade = gtk.glade.XML(get_resource("rename.glade"))
        self.window = self.glade.get_widget("rename_dialog")

        self.original_files_treeview = self.glade.get_widget("files_treeview")
        self.new_files_treeview = self.glade.get_widget("new_files_treeview")

        self.database_combo = self.glade.get_widget("database_combo")
        self.rename_action_combo = self.glade.get_widget("rename_action_combo")
        self.on_conflict_combo = self.glade.get_widget("on_conflict_combo")
        self.episode_order_combo = self.glade.get_widget("episode_order_combo")

        self.format_string_entry = self.glade.get_widget("format_string_entry")
        self.query_entry = self.glade.get_widget("query_entry")
        self.download_subs_checkbox = self.glade.get_widget(
            "download_subs_checkbox")
        self.language_code_entry = self.glade.get_widget("language_code_entry")
        self.encoding_entry = self.glade.get_widget("encoding_entry")
        self.output_entry = self.glade.get_widget("output_entry")

        signal_dictionary = {
            "on_toggle_advanced": self.on_toggle_advanced,
            "on_do_dry_run_clicked": self.on_do_dry_run_clicked,
            "on_format_help_clicked": self.on_format_help_clicked,
            "on_execute_filebot_clicked": self.on_execute_filebot_clicked
        }

        self.glade.signal_autoconnect(signal_dictionary)

        combo_data = {}
        for key in dialog_settings:
            try:
                if key.startswith('valid_'):
                    combo_data[key] = dialog_settings[key]
            except KeyError:
                pass

        self.build_combo_boxes(combo_data)
        self.populate_with_settings(self.ui_settings)

        self.init_treestore(self.original_files_treeview,
                            "Original File Structure at {}".format(
                                self.current_torrent_save_path))
        self.init_treestore(self.new_files_treeview, "New File Structure")
        self.load_treestore((None, self.files), self.original_files_treeview)
        treeview = self.glade.get_widget("files_treeview")
        treeview.expand_all()

        self.window.show()

        tree_pane = self.glade.get_widget("tree_pane")
        tree_pane.set_position(tree_pane.allocation.width/2)

    def build_combo_boxes(self, combo_data):
        """builds the combo boxes for the dialog
        Args:
          combo_data: dict of data to be loaded into combo boxes
        """
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
        """inflates an individual combo box
        Args:
          model_data: data to be loaded into a list store (list)
          combo_widget: the widget to load data into.
        """
        list_store = gtk.ListStore(str)
        for datum in model_data:
            list_store.append([datum])

        combo_widget.set_model(list_store)
        renderer = gtk.CellRendererText()
        combo_widget.pack_start(renderer, expand=True)
        combo_widget.add_attribute(renderer, "text", 0)

    def populate_with_settings(self, settings):
        """presets the window with the last settings used in the plugin
        Args:
          settings: The settings dict given by the server.
        """
        log.debug("Previous settings received: {}".format(settings))
        combo_value_pairs = [
            (self.database_combo, settings["database"]),
            (self.rename_action_combo, settings["rename_action"]),
            (self.on_conflict_combo, settings["on_conflict"]),
            (self.episode_order_combo, settings["episode_order"])
        ]

        log.debug("Setting combo boxes")
        for combo, value in combo_value_pairs:
            combo_model = combo.get_model()
            value_index = [index for index, row in enumerate(combo_model)
                           if row[0] == value][0]
            if not value_index:
                log.warning("could not set {0} to value {1}, value {1} could "
                            "not be found in {0}".format(combo, value))
            else:
                combo.set_active(value_index)

        entry_value_pairs = [
            (self.format_string_entry, settings["format_string"]),
            (self.encoding_entry, settings["encoding"]),
            (self.language_code_entry, settings["language_code"]),
            (self.query_entry, settings["query"]),
            (self.output_entry, settings["output"])
        ]

        log.debug("Setting entry widgets")
        for entry, value in entry_value_pairs:
            if value:
                entry.set_text(value)

        log.debug("Setting advanced and subs widgets")
        advanced_options = self.glade.get_widget("advanced_options")
        if advanced_options.get_visible() != settings["show_advanced"]:
            self.on_toggle_advanced()

        if self.download_subs_checkbox.get_active() != settings[
            "download_subs"]:
            self.on_download_subs_toggled()

    def init_treestore(self, treeview, header):
        """builds the treestore that will be used to hold the files info
        Args:
          treeview: treeview widget to initialize.
          header: the column Header to use.
        """
        model = gtk.TreeStore(str, str)
        treeview.set_model(model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(header, renderer, text=1)
        treeview.append_column(column)

    def load_treestore(self, (save_path, file_data), treeview, clear=False):
        """populates a treestore using a torrents filedata and savepath
        Args:
          (save_path, file_data): tuple conting the save path and files dict.
          treeview: the treeview widget you would like to load data into.
          clear: a bool to notify clearing of treeview widget before writing.
        """
        # TODO: more extensive path testing, Allow for reformatting with moves!
        if clear:
            if save_path:
                for column in treeview.get_columns():
                    treeview.remove_column(column)
                self.init_treestore(treeview, "New File Structure at {"
                                              "}".format(save_path))
            model = gtk.TreeStore(str, str)
            treeview.set_model(model)

        index_path_pairs = [(f["index"], f["path"]) for f in file_data]
        model = treeview.get_model()
        folder_iterators = {}
        folder_structure = {}
        for index, path in index_path_pairs:
            path_parts = path.split('/')
            if len(path_parts) == 1:
                model.append(None, [index, path])

            else:  # not a single file, torrent is a folder.
                for path_depth in range(len(path_parts)):
                    try:
                        folder_structure[path_depth]
                    except KeyError:
                        folder_structure[path_depth] = []

                    if path_parts[path_depth] not in folder_structure[
                        path_depth]:
                        folder_structure[path_depth].append(path_parts[
                            path_depth])

                        try:
                            parent = folder_iterators[path_depth - 1]
                        except KeyError:
                            parent = None

                        if path_parts[path_depth] == os.path.basename(path):
                            model.append(parent, [str(index), path_parts[
                                path_depth]])
                        else:
                            folder_iterator = model.append(parent,
                                                           ['', path_parts[path_depth]])
                            folder_iterators[path_depth] = folder_iterator

        treeview.expand_all()

    def collect_dialog_settings(self):
        """collects the settings on the widgets and serializes them into
        a dict for sending to the server.
        returns: a dictionary containing the user's setting values
        """
        settings = {}

        combos = {
            "database": self.database_combo,
            "rename_action": self.rename_action_combo,
            "on_conflict": self.on_conflict_combo,
            "episode_order": self.episode_order_combo
        }
        for setting in combos:
            combo_model = combos[setting].get_model()
            iter = combos[setting].get_active_iter()
            if iter:
                settings[setting] = combo_model[iter][0]

        entries = {
            "format_string": self.format_string_entry,
            "encoding": self.encoding_entry,
            "language_code": self.language_code_entry,
            "query": self.query_entry,
            "output": self.output_entry
        }
        for setting in entries:
            settings[setting] = entries[setting].get_text()

        settings["show_advanced"] = self.glade.get_widget(
            "advanced_options").get_visible()
        settings["download_subs"] = self.download_subs_checkbox.get_active()

        log.debug("Collected settings for server: {}".format(settings))
        return settings

    #  Section: UI actions

    def on_download_subs_toggled(self, *args):
        """download subs has been toggled.
        toggles "greying out" of subs options.
        """
        subs_options = self.glade.get_widget("subs_options")
        if subs_options.get_sensitive():
            subs_options.set_sensitive(False)
        else:
            subs_options.set_sensitive(True)

    def on_toggle_advanced(self, *args):
        """Advanced dropdown has been toggled, Show or hide options
        """
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

    def on_do_dry_run_clicked(self, *args):
        """
        executes a dry run to show the user how the torrent is expected to
        look after filebot run.
        """
        handler_settings = self.collect_dialog_settings()
        log.info("sending dry run request to server for torrent {}".format(
            self.torrent_id))
        d = client.filebottool.do_dry_run(self.torrent_id, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(self.load_treestore, self.new_files_treeview, clear=True)

    def on_execute_filebot_clicked(self, *args):
        """collects and sends settings, and tells server to execute run using
         them.
        """
        handler_settings = self.collect_dialog_settings()
        log.info("Sending execute request to server for torrent {}".format(
            self.torrent_id))
        log.debug("Using settings: {}".format(handler_settings))
        client.filebottool.save_rename_dialog_settings(handler_settings)
        d = client.filebottool.do_rename(self.torrent_id, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(self.rename_complete)

    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('Format expression info button was clicked')

    def rename_complete(self, success, msg=None):
        if success:
            del self.window
        else:
            log.warning("rename failed with message: {}".format(msg))

    def log_response(self, response):
        log.debug("response from server: {}".format(response))
        return response



class GtkUI(GtkPluginBase):


    def enable(self):
        """actions to take on plugin enabled.
        loads preference page, and context menu.
        """
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
        """context menu has been selected on a specific torrent.
        asks server for torrent info and builds rename dialog on reply"""
        torrent_id = component.get("TorrentView").get_selected_torrent()
        client.filebottool.get_rename_dialog_info(torrent_id).addCallback(
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
        log.debug("applying prefs for FileBotTool")
        client.filebottool.set_config(self.config)

    def on_show_prefs(self):
        client.filebottool.get_config().addCallback(self.on_get_config)

    def on_get_config(self, config):
        self.config = config

    def on_get_version(self, version):
        "callback for on show_prefs"
        self.glade.get_widget("filebot_version").set_text(version)