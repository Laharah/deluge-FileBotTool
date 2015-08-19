__author__ = 'jaredanderson'

# noinspection PyUnresolvedReferences
import gtk
import webbrowser
import os

# noinspection PyUnresolvedReferences
from deluge.ui.client import client

from twisted.internet import defer

from filebottool.common import Log
from filebottool.common import get_resource
from filebottool.gtkui.handler_ui import HandlerUI
import user_messenger

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
        self.messenger = user_messenger.UserMessenger()
        self.torrent_ids = dialog_settings["torrent_ids"]
        self.torrent_id = None
        self.files = []
        self.current_save_path = ""
        if len(dialog_settings["torrent_ids"]) == 1:
            self.torrent_id = dialog_settings["torrent_ids"][0]
            self.files = dialog_settings["files"]
            self.current_save_path = dialog_settings["torrent_save_path"]

        self.ui_settings = dialog_settings["rename_dialog_last_settings"]
        self.server_filebot_version = dialog_settings["filebot_version"]

        self.glade = gtk.glade.XML(get_resource("rename.glade"))
        self.handler_ui = HandlerUI(self.glade, self.ui_settings)
        self.window = self.glade.get_widget("rename_dialog")

        self.original_files_treeview = self.glade.get_widget("files_treeview")
        self.new_files_treeview = self.glade.get_widget("new_files_treeview")
        self.history_files_treeview = self.glade.get_widget("history_files_treeview")

        if not self.torrent_id:
            self.glade.get_widget("tree_pane").hide()
            self.glade.get_widget("dialog_notebook").set_show_tabs(False)
            self.glade.get_widget("do_dry_run").hide()
            self.glade.get_widget("query_entry").set_sensitive(False)
            self.glade.get_widget("query_label").set_sensitive(False)

        signal_dictionary = {
            "on_toggle_advanced": self.on_toggle_advanced,
            "on_do_dry_run_clicked": self.on_do_dry_run_clicked,
            "on_format_help_clicked": self.on_format_help_clicked,
            "on_execute_filebot_clicked": self.on_execute_filebot_clicked,
            "on_revert_button_clicked": self.on_revert_button_clicked,
            "on_download_subs_toggled": self.on_download_subs_toggled,
        }

        self.glade.signal_autoconnect(signal_dictionary)

        self.glade.get_widget("filebot_version").set_text(self.server_filebot_version)

        advanced_options = self.glade.get_widget("advanced_options")
        show_advanced = dialog_settings['rename_dialog_last_settings']['show_advanced']
        if advanced_options.get_visible() != show_advanced:
            self.on_toggle_advanced()

        download_subs = self.handler_ui.download_subs_checkbox
        if download_subs.get_active() != self.glade.get_widget"subs_options").get_sensitive():
            self.on_download_subs_toggled()

        self.init_treestore(self.original_files_treeview,
                            "Original File Structure at {0}".format(
                                self.current_save_path))
        self.init_treestore(self.new_files_treeview, "New File Structure")
        self.init_treestore(self.history_files_treeview,
                            "Current File Structure at {0}".format(
                            self.current_save_path))
        self.load_treestore((None, self.files), self.original_files_treeview)
        self.load_treestore((None, self.files), self.history_files_treeview)
        treeview = self.glade.get_widget("files_treeview")
        treeview.expand_all()

        self.window.show()

        tree_pane = self.glade.get_widget("tree_pane")
        tree_pane.set_position(tree_pane.allocation.width / 2)

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
        # TODO: look into deluge's internal treestore functions
        if clear:
            if save_path:
                for column in treeview.get_columns():
                    treeview.remove_column(column)
                self.init_treestore(treeview, "New File Structure at {0}".format(save_path))
            model = gtk.TreeStore(str, str)
            treeview.set_model(model)
        if not file_data:
            return
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
                                parent, ['', path_parts[path_depth]])
                            folder_iterators[path_depth] = folder_iterator

        treeview.expand_all()

    @defer.inlineCallbacks
    def refresh_files(self, *args):
        """
        Refreshes the file data from the server and updates the treestore model
        """
        log.debug("refreshing filedata for torrent {0}".format(self.torrent_id))

        torrent_data = yield client.core.get_torrent_status(self.torrent_id,
                                                            ["save_path",
                                                             "files"])
        log.debug("recieved response from server{0}".format(torrent_data))
        save_path = torrent_data["save_path"]
        files = torrent_data["files"]
        self.load_treestore((save_path, files), self.original_files_treeview, clear=True)
        self.load_treestore((save_path, files), self.history_files_treeview, clear=True)

    # Section: UI actions

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
        advanced_label = self.glade.get_widget("show_advanced_label")

        if advanced_options.get_visible():
            advanced_options.hide()
            advanced_label.set_text("Show Advanced")
            arrow.set(gtk.ARROW_RIGHT, gtk.SHADOW_NONE)
        else:
            advanced_options.show()
            advanced_label.set_text("Hide Advanced")
            arrow.set(gtk.ARROW_DOWN, gtk.SHADOW_NONE)

    def on_do_dry_run_clicked(self, button):
        """
        executes a dry run to show the user how the torrent is expected to
        look after filebot run.
        """
        handler_settings = self.handler_ui.collect_dialog_settings()
        log.info("sending dry run request to server for torrent {0}".format(
            self.torrent_id))
        log.debug("using settings: {0}".format(handler_settings))
        self.toggle_button(button)

        def error_check(((success, errors), new_info)):
            '''closure to pop off error reporting'''
            if not success:
                message = 'The dry run found the following errors'
                self.messenger.display_errors(
                    errors,
                    title="Dry Run Warning",
                    message=message,
                    show_details=True)
            return new_info

        d = client.filebottool.do_dry_run(self.torrent_id, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(error_check)
        d.addCallback(self.load_treestore, self.new_files_treeview, clear=True)
        d.addCallback(self.toggle_button, button)

    def on_execute_filebot_clicked(self, button):
        """collects and sends settings, and tells server to execute run using
         them.
        """
        handler_settings = self.handler_ui.collect_dialog_settings()
        log.info("Sending execute request to server for torrents {0}".format(
            self.torrent_ids))
        log.debug("Using settings: {0}".format(handler_settings))
        self.toggle_button(button)

        client.filebottool.save_rename_dialog_settings(handler_settings)
        d = client.filebottool.do_rename(self.torrent_ids, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(self.rename_complete)
        d.addCallback(self.toggle_button, button)

    def on_revert_button_clicked(self, button):
        log.info("Sending revert request to server for torrent {0}".format(
            self.torrent_id))
        self.toggle_button(button)

        d = client.filebottool.do_revert(self.torrent_id)
        d.addCallback(self.log_response)
        d.addCallback(self.toggle_button, button)
        d.addCallback(self.refresh_files)

    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('Format expression info button was clicked')

    def rename_complete(self, (success, errors)):
        """
        Executed when do_rename has returned from server. Reports errors as well.
        """
        if success:
            log.debug("Rename Completed.")
            self.window.destroy()
        else:
            log.warning("rename failed with errors: {0}".format(errors))
            self.messenger.display_errors(errors)

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
