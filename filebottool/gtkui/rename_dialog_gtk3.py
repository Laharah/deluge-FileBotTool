from __future__ import absolute_import
from filebottool.six.moves import range

__author__ = "laharah"

# noinspection PyUnresolvedReferences
from gi.repository import Gtk
import webbrowser
import os

# noinspection PyUnresolvedReferences
from deluge.ui.client import client
import deluge.component as component

from twisted.internet import defer

from filebottool.common import LOG, version_tuple
from filebottool.common import get_resource
from filebottool.gtkui.common_gtk3 import inflate_list_store_combo
from filebottool.gtkui.handler_ui_gtk3 import HandlerUI
from . import user_messenger_gtk3 as user_messenger

log = LOG


class RenameDialog(object):
    """builds and runs the rename dialog."""

    def __init__(self, dialog_settings, server_plugin_version):
        """sets up the dialog using the settings supplied by the server
        Also loads relevant ui widgets as members

        Args:
         dialog_settings: A dictionary containing the settings to populate.
        """
        self.server_plugin_version = server_plugin_version
        self.watch_for_setting_change = False
        self.messenger = user_messenger.UserMessenger()
        self.torrent_ids = dialog_settings["torrent_ids"]
        self.torrent_id = None
        self.files = []
        self.current_save_path = ""
        self.builder = Gtk.Builder()
        self.builder.add_from_file(get_resource("rename.ui"))

        signal_dictionary = {
            "on_toggle_advanced": self.on_toggle_advanced,
            "on_do_dry_run_clicked": self.on_do_dry_run_clicked,
            "on_format_help_clicked": self.on_format_help_clicked,
            "on_execute_filebot_clicked": self.on_execute_filebot_clicked,
            "on_revert_button_clicked": self.on_revert_button_clicked,
            "on_download_subs_toggled": self.on_download_subs_toggled,
            "on_setting_changed": self.on_setting_changed,
            "on_save_handlers_clicked": self.on_save_handlers_clicked,
            "on_load_saved_handler": self.on_load_saved_handler,
            "on_saved_handlers_entry_focus": self.on_saved_handers_entry_focus,
        }

        self.builder.connect_signals(signal_dictionary)

        if len(dialog_settings["torrent_ids"]) == 1:
            self.torrent_id = dialog_settings["torrent_ids"][0]
            self.files = dialog_settings["files"]
            self.current_save_path = dialog_settings["torrent_save_path"]

        self.ui_settings = dialog_settings["rename_dialog_last_settings"]
        handler_name = self.ui_settings["handler_name"]
        if handler_name in dialog_settings["saved_handlers"]:
            try:
                self.ui_settings = dialog_settings["saved_handlers"][handler_name]
            except KeyError:
                log.error("handler {0} could not be found".format(handler_name))

        self.handler_ui = HandlerUI(self.builder, self.ui_settings)

        self.server_filebot_version = dialog_settings["filebot_version"]

        self.window = self.builder.get_object("rename_dialog")
        self.window.set_transient_for(component.get("MainWindow").window)

        fb_icon = self.builder.get_object("execute_icon")
        image = get_resource("fb_icon24.png")
        fb_icon.set_from_file(image)

        self.original_files_treeview = self.builder.get_object("files_treeview")
        self.new_files_treeview = self.builder.get_object("new_files_treeview")
        self.history_files_treeview = self.builder.get_object("history_files_treeview")
        self.previous_treeview = self.builder.get_object("previous_treeview")

        if not self.torrent_id:
            self.builder.get_object("tree_pane").hide()
            self.builder.get_object("do_dry_run").hide()
            self.history_files_treeview.hide()
            self.previous_treeview.hide()
            # self.glade.get_object("dialog_notebook").set_show_tabs(False)
            # self.glade.get_object("query_entry").set_sensitive(False)
            # self.glade.get_object("query_label").set_sensitive(False)

        if self.server_filebot_version:
            self.builder.get_object("filebot_version").set_text(
                self.server_filebot_version.decode("utf8")
            )
        else:

            def open_filebot_homepage(*args):
                webbrowser.open(r"http://www.filebot.net", new=2)
                log.debug("opening filebot homepage")

            signal = {"on_filebot_version_clicked": open_filebot_homepage}
            self.builder.connect_signals(signal)
            self.toggle_button(self.builder.get_object("do_dry_run"))
            self.toggle_button(self.builder.get_object("execute_filebot"))

        advanced_options = self.builder.get_object("advanced_options")
        show_advanced = dialog_settings["rename_dialog_last_settings"]["show_advanced"]
        if advanced_options.get_visible() != show_advanced:
            self.on_toggle_advanced()

        download_subs = self.handler_ui.download_subs_checkbox
        if (
            download_subs.get_active()
            != self.builder.get_object("subs_options").get_sensitive()
        ):
            self.on_download_subs_toggled()

        self.init_treestore(self.new_files_treeview, "New File Structure")
        self.init_treestore(
            self.original_files_treeview,
            "Original File Structure at {0}".format(self.current_save_path),
        )
        self.load_treestore(self.original_files_treeview, self.files)
        self.init_treestore(
            self.history_files_treeview,
            "Current File Structure at {0}".format(self.current_save_path),
        )
        self.load_treestore(self.history_files_treeview, self.files)
        if self.server_plugin_version > (1, 1, 12):
            self.init_treestore(self.previous_treeview, "Awaiting FileBot History...")
            self.get_history(self.torrent_id)
        else:
            header = "Server version does not support History!"
            self.init_treestore(self.previous_treeview, header)

        treeview = self.builder.get_object("files_treeview")
        treeview.expand_all()

        self.saved_handlers = dialog_settings["saved_handlers"]
        combo = self.builder.get_object("saved_handlers_combo")
        if combo is None:
            log.critical("HANDLER COMBO NOT FOUND!")
        else:
            log.critical("COMBO HANDLER EXISTS!")
        inflate_list_store_combo(
            list(self.saved_handlers.keys()),
            combo,
        )

        if handler_name:
            entry = self.builder.get_object("saved_handlers_combo").get_child()
            log.debug("Setting text to {0}".format(handler_name))
            entry.set_text(handler_name)

        self.watch_for_setting_change = True

        self.window.show()

        tree_pane = self.builder.get_object("tree_pane")
        tree_pane.set_position(tree_pane.get_allocation().width / 2)

    def init_treestore(self, treeview, header):
        """builds the treestore that will be used to hold the files info
        Args:
          treeview: treeview widget to initialize.
          header: the column Header to use.
        """
        model = Gtk.TreeStore(str, str)
        treeview.set_model(model)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(header, renderer, text=1)
        treeview.append_column(column)

    def load_treestore(self, treeview, file_data, clear=False, title=None):
        """
        Loads file_data into given treeview
        Args:
            file_data: dict containing file info from deluge
            treeview: treeview widget to load into
            clear: clear the treestore of old data
            title: The title at the top of treeview widget (requires clear)

        Returns: None
        """
        if clear:
            if title:
                for column in treeview.get_columns():
                    treeview.remove_column(column)
                self.init_treestore(treeview, title)
            model = Gtk.TreeStore(str, str)
            treeview.set_model(model)
        if not file_data:
            return
        index_path_pairs = [(f["index"], f["path"]) for f in file_data]
        model = treeview.get_model()
        folder_iterators = {}
        folder_structure = {}
        for index, path in index_path_pairs:
            path_parts = path.split("/")
            if len(path_parts) == 1:
                model.append(None, [index, path])

            else:  # not a single file, torrent is a folder.
                for path_depth in range(len(path_parts)):
                    try:
                        folder_structure[path_depth]
                    except KeyError:
                        folder_structure[path_depth] = []

                    if path_parts[path_depth] not in folder_structure[path_depth]:
                        folder_structure[path_depth].append(path_parts[path_depth])

                        try:
                            parent = folder_iterators[path_depth - 1]
                        except KeyError:
                            parent = None

                        if path_parts[path_depth] == os.path.basename(path):
                            model.append(parent, [str(index), path_parts[path_depth]])
                        else:
                            folder_iterator = model.append(
                                parent, ["", path_parts[path_depth]]
                            )
                            folder_iterators[path_depth] = folder_iterator

        treeview.expand_all()

    @defer.inlineCallbacks
    def refresh_files(self, *args):
        """
        Refreshes the file data from the server and updates the treestore model
        """
        log.debug("refreshing filedata for torrent {0}".format(self.torrent_id))

        torrent_data = yield client.core.get_torrent_status(
            self.torrent_id, ["save_path", "files"]
        )

        log.debug("recieved response from server{0}".format(torrent_data))
        save_path = torrent_data["save_path"]
        files = torrent_data["files"]
        header = "Current File Structure at {0}".format(save_path)
        self.load_treestore(
            self.original_files_treeview, files, clear=True, title=header
        )
        self.load_treestore(
            self.history_files_treeview, files, clear=True, title=header
        )
        if self.server_plugin_version > (1, 1, 12):
            header = "Awaiting Filebot History..."
            self.load_treestore(self.previous_treeview, None, clear=True, title=header)
            self.get_history(self.torrent_id)

    # Section: UI actions

    @defer.inlineCallbacks
    def get_history(self, torrent_id):
        """
        requests torrent history from server/filebot in backround, gracefully handles
        failure
        """
        if not torrent_id:
            defer.returnValue(None)
        log.debug("requesting filebot history for torrent {0}".format(torrent_id))
        try:
            reply = yield client.filebottool.get_filebot_history(torrent_id)
        except Exception as e:
            log.info("history error encountered!", exc_info=True)
            raise
        else:
            log.debug("History reply from server: {0}".format(reply))
        success, data = reply
        if not success:
            err = data
            log.error(err)
            defer.returnValue(None)
        prev_path, files = data
        if prev_path is None and files is None:
            log.debug("No history to populate.")
            header = "No History found."
            self.load_treestore(self.previous_treeview, None, clear=True, title=header)
            defer.returnValue(None)
        log.debug("Populating torrent history...")
        header = "Previous File Structure at {0}".format(prev_path)
        self.load_treestore(self.previous_treeview, files, clear=True, title=header)

    def on_download_subs_toggled(self, *args):
        """download subs has been toggled.
        toggles "greying out" of subs options.
        """
        subs_options = self.builder.get_object("subs_options")
        if subs_options.get_sensitive():
            subs_options.set_sensitive(False)
        else:
            subs_options.set_sensitive(True)

    def on_toggle_advanced(self, *args):
        """Advanced dropdown has been toggled, Show or hide options"""
        advanced_options = self.builder.get_object("advanced_options")
        arrow = self.builder.get_object("advanced_arrow")
        advanced_label = self.builder.get_object("show_advanced_label")

        if advanced_options.get_visible():
            advanced_options.hide()
            advanced_label.set_text("Show Advanced")
            arrow.set(Gtk.ArrowType.RIGHT, Gtk.ShadowType.NONE)
        else:
            advanced_options.show()
            advanced_label.set_text("Hide Advanced")
            arrow.set(Gtk.ArrowType.DOWN, Gtk.ShadowType.NONE)

    @defer.inlineCallbacks
    def on_do_dry_run_clicked(self, button):
        """
        executes a dry run to show the user how the torrent is expected to
        look after filebot run.
        """
        handler_settings = self.handler_ui.collect_dialog_settings()
        log.info(
            "sending dry run request to server for torrent {0}".format(self.torrent_id)
        )
        log.debug("using settings: {0}".format(handler_settings))
        self.toggle_button(button)

        spinner = self.builder.get_object("dry_run_spinner")
        self.swap_spinner(spinner)

        result = yield client.filebottool.do_dry_run(self.torrent_id, handler_settings)
        self.swap_spinner(spinner)
        self.toggle_button(button)
        self.log_response(result)

        (success, errors), (new_save_path, files) = result
        if not success:
            message = "The dry run found the following errors"
            self.messenger.display_errors(
                errors, title="Dry Run Warning", message=message, show_details=True
            )

        else:
            header = "New File Structure at: {0}".format(new_save_path)
            self.load_treestore(
                self.new_files_treeview, files, clear=True, title=header
            )

    @defer.inlineCallbacks
    def on_execute_filebot_clicked(self, button):
        """collects and sends settings, and tells server to execute run using
        them.
        """
        handler_settings = self.handler_ui.collect_dialog_settings()

        handler_name = (
            self.builder.get_object("saved_handlers_combo").get_child().get_text()
        )
        log.debug("got %s for handler name in from combobox", handler_name)
        if (
            handler_name in self.saved_handlers
            and handler_settings == self.saved_handlers[handler_name]
        ):
            log.debug(
                "handler matches saved handler, setting name to %s.", handler_name
            )

            handler_settings["handler_name"] = handler_name
        else:
            log.debug(
                'handler "%s" did not match saved handler. Setting to None.',
                handler_name,
            )
            # new, saved = set(list(handler_settings.keys())), set(list(handler_settings.keys()))
            # missing = new ^ saved
            # if missing:
            #     log.debug('Key mismatch: %s.', missing)
            # shared = new & saved
            # for k in shared:
            #     new, saved = handler_settings[k], self.saved_handlers[handler_name][k]
            #     if new != saved:
            #         log.debug('mismatch on key "%s": %s != %s', k, new, saved)
            handler_settings["handler_name"] = None

        log.info(
            "Sending execute request to server for torrents {0}".format(
                self.torrent_ids
            )
        )
        log.debug("Using settings: {0}".format(handler_settings))
        self.toggle_button(button)

        spinner = self.builder.get_object("execute_spinner")
        self.swap_spinner(spinner)
        client.filebottool.save_rename_dialog_settings(handler_settings)

        result = yield client.filebottool.do_rename(self.torrent_ids, handler_settings)
        self.swap_spinner(spinner)
        self.toggle_button(button)
        self.log_response(result)
        success, errors, new_files = result
        if new_files:
            self.messenger.show_new_files(new_files)
        if not success:
            log.warning("rename failed with errors: {0}".format(errors))
            self.messenger.display_errors(errors)
        else:
            log.info("rename successful on {0}".format(self.torrent_ids))
            self.window.destroy()

    @defer.inlineCallbacks
    def on_revert_button_clicked(self, button):
        log.info(
            "Sending revert request to server for torrents {0}".format(self.torrent_ids)
        )
        self.toggle_button(button)

        result = yield client.filebottool.do_revert(self.torrent_ids)
        self.toggle_button(button)
        success, errors = result
        if success:
            log.info("Successfully reverted torrents: {0}".format(self.torrent_ids))
            if self.torrent_id:
                self.refresh_files()
        else:
            log.warning(
                "Error while reverting torrents: {0}".format(list(errors.keys()))
            )
            self.messenger.display_errors(errors)

    def on_saved_handers_entry_focus(self, entry, *args):
        entry.select_region(0, -1)

    def on_setting_changed(self, *args):
        if not self.watch_for_setting_change or not self.handler_ui.populated:
            return
        entry = self.builder.get_object("saved_handlers_combo").get_child()
        if entry.get_text() in self.saved_handlers:
            entry.set_text("")

    def on_save_handlers_clicked(self, *args):
        handler_combo = self.builder.get_object("saved_handlers_combo")
        handler_name = handler_combo.get_child().get_text()
        if not handler_name:
            return
        data = self.handler_ui.collect_dialog_settings()
        data["query_override"] = None

        if handler_name in self.saved_handlers:
            message = "Overwrite the {0} profile?".format(handler_name)
            dialog = user_messenger.ResponseDialog(
                "Confirm Overwrite", message=message, modal=True
            )
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return
            #  preserve query override for pre-exsisting handlers (from config only)
            data["query_override"] = self.saved_handlers[handler_name]["query_override"]

        self.saved_handlers[handler_name] = data
        log.debug("Sending handler configurations to server.")
        client.filebottool.update_handlers(self.saved_handlers)
        inflate_list_store_combo(self.saved_handlers, handler_combo)

    def on_load_saved_handler(self, saved_handler_combo, *args):
        self.watch_for_setting_change = False
        combo_model = saved_handler_combo.get_model()
        current_iter = saved_handler_combo.get_active_iter()
        if not current_iter:
            return
        handler_name = combo_model[current_iter][0]
        log.debug(handler_name)
        if current_iter >= 0:
            handler = self.saved_handlers[handler_name]
            self.handler_ui.populate_with_settings(handler)
        saved_handler_combo.get_child().set_text(handler_name)
        self.watch_for_setting_change = True

    def on_format_help_clicked(self, *args):
        webbrowser.open(r"http://www.filebot.net/naming.html", new=2)
        log.debug("Format expression info button was clicked")

    def log_response(self, response):
        log.debug("response from server: {0}".format(response))
        return response

    def toggle_button(self, *args):
        """
        toggles the sensitivity of a given button widget.
        NOTE: The final argument passed must be the button widget to toggle!!!
              (This allows toggle button to be the final callback in a twisted callback
              chain)
        """
        button_widget = args[-1]  # workaround for deferd argument passing
        if button_widget.get_sensitive():
            button_widget.set_sensitive(False)
        else:
            button_widget.set_sensitive(True)

    def swap_spinner(self, *args):
        spinner = args[-1]
        if spinner is self.builder.get_object("dry_run_spinner"):
            hide = self.builder.get_object("dry_run_icon")
        else:
            hide = self.builder.get_object("execute_icon")

        if spinner.get_visible():
            spinner.hide()
            spinner.stop()
            hide.show()
        else:
            spinner.show()
            spinner.start()
            hide.hide()
