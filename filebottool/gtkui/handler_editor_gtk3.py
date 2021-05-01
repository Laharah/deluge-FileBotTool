from __future__ import absolute_import
__author__ = 'laharah'

from gi.repository import Gtk

from filebottool.common import LOG
from filebottool.common import get_resource
from filebottool.gtkui.handler_ui_gtk3 import HandlerUI
from filebottool.gtkui.common_gtk3 import inflate_list_store_combo
from filebottool.gtkui.user_messenger_gtk3 import InfoDialog, ResponseDialog


log = LOG

class HandlerEditor(HandlerUI):
    def __init__(self, handlers=None, initial=None, cb=None, parent=None):
        """
        :param handlers: dictionary of saved handlers from server
        :param initial: handler_id of handler to load initially
        :return:
        """
        self.handlers = handlers if handlers else {}
        self.cb = cb

        try:
            initial_settings = handlers[initial]
        except KeyError:
            initial_settings = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file(get_resource("handler_editor.ui"))
        super().__init__(self.builder, initial_settings)
        self.window = self.builder.get_object("window1")
        self.window.set_modal(True)
        self.handler_name_combo_entry = self.builder.get_object("handler_name_combo_entry")
        inflate_list_store_combo(list(handlers.keys()), self.handler_name_combo_entry)
        if initial:
            self.handler_name_combo_entry.get_child().set_text(initial)

        signal_dictionary = {
            "on_handler_name_combo_changed": self.on_handler_changed,
            "on_save_changes_clicked": self.on_save_changes_clicked,
            "on_cancel_changes_clicked": self.on_cancel_changes_clicked,
            "on_query_checkbox_toggled": self.on_query_checkbox_toggled,
            "on_download_subs_checkbox_toggled": self.on_download_subs_checkbox_toggled,
        }
        self.builder.connect_signals(signal_dictionary)

        if parent:
            self.set_transient_for(parent)
        self.window.show_all()

    def populate_with_settings(self, *args, **kwargs):
        super(self.__class__, self).populate_with_settings(*args, **kwargs)
        check_box = self.builder.get_object('query_checkbox')
        if self.query_entry.get_text():
            check_box.set_active(True)
        else:
            check_box.set_active(False)

    def collect_dialog_settings(self):
        settings = super(self.__class__, self).collect_dialog_settings()
        if not self.builder.get_object('query_checkbox').get_active():
            settings['query_override'] = ''
        return settings

    def on_handler_changed(self, *args):
        """New handler chosen, re-populate widgets with handler settings"""
        combo_model = self.handler_name_combo_entry.get_model()
        current_iter = self.handler_name_combo_entry.get_active_iter()
        if not current_iter:
            return
        handler_name = combo_model[current_iter][0]
        if current_iter >= 0:
            handler = self.handlers[handler_name]
            self.populate_with_settings(handler)
        self.handler_name_combo_entry.get_child().set_text(handler_name)

    def on_save_changes_clicked(self, *args):
        """send updated handlers dictionary to server, call the callback if supplied"""
        settings = self.collect_dialog_settings()
        handler_id = self.handler_name_combo_entry.get_child().get_text().strip()
        if not handler_id:
            dialog = InfoDialog("Identifier Required",
                                "The Handler requires a Name.",
                                modal=True)
            dialog.run()
            dialog.destroy()
            return
        if handler_id in self.handlers:
            buttons = (Gtk.STOCK_CANCEL,
                       Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OK,
                       Gtk.ResponseType.OK,)

            dialog = ResponseDialog("Overwrite?",
                                    "Overwrite the profile named {0}? "
                                    "Auto-sort rules that use this handler will "
                                    "be affected.".format(handler_id),
                                    buttons=buttons)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
        self.handlers[handler_id] = settings
        self.window.destroy()
        if self.cb:
            self.cb(handler_id, self.handlers)

    def on_cancel_changes_clicked(self, *args):
        self.window.destroy()

    def on_query_checkbox_toggled(self, box):
        """show message about query overriding and enable query_entry"""
        text = self.query_entry.get_text()
        if box.get_active():
            if not text:
                dialog = InfoDialog("Override Query Warning!",
                                    "Using A Search Query in a saved profile "
                                    "will force every run to match against the same"
                                    " title!",
                                    modal=True)
                dialog.run()
                dialog.destroy()

            self.query_entry.set_sensitive(True)

        else:
            self.query_entry.set_sensitive(False)

    def on_download_subs_checkbox_toggled(self, box):
        log.debug("subs box toggled")
        subs_options = self.builder.get_object('subs_options')
        if box.get_active():
            subs_options.set_sensitive(True)
        else:
            subs_options.set_sensitive(False)
