__author__ = 'laharah'

import gtk

from deluge.ui.client import client

from filebottool.common import Log
from filebottool.common import get_resource
from filebottool.gtkui.handler_ui import HandlerUI
from filebottool.gtkui.common import inflate_list_store_combo
from filebottool.gtkui.user_messenger import InfoDialog, ResponseDialog


class HandlerEditor(HandlerUI):
    def __init__(self, handlers=None, initial=None, cb=None):
        """
        :param handlers: dictionary of saved handlers from server
        :param initial: handler_id of handler to load initially
        :return:
        """
        self.handlers = handlers if handlers else {}
        self.cb = cb

        if initial is not None:
            try:
                initial = handlers[initial]
            except KeyError:
                initial = None

        self.glade = gtk.glade.XML(get_resource("handler_editor.glade"))
        super(self.__class__, self).__init__(self.glade, initial)
        self.window = self.glade.get_widget("handler_editor")
        self.window.set_modal(True)
        self.handler_name_combo_entry = self.glade.get_widget("handler_name_combo_entry")
        inflate_list_store_combo(handlers.keys(), self.handler_name_combo_entry)

        signal_dictionary = {
            "on_handler_name_combo_entry_focus_out_event": self.on_new_handler_id,
            "on_handler_name_combo_entry_changed": self.on_handler_changed,
            "on_save_changes_clicked": self.on_save_changes_clicked,
            "on_cancel_changes_clicked": self.on_cancel_changes_clicked,
        }
        self.glade.signal_autoconnect(signal_dictionary)

        self.window.show()

    def on_handler_changed(self, *args):
        """New handler chosen, re-populate widgets with handler settings"""
        try:
            settings = self.handlers[self.handler_name_combo_entry.child.get_text()]
        except KeyError:
            return
        else:
            self.populate_with_settings(settings)

    def on_save_changes_clicked(self, *args):
        """send updated handlers dictionary to server, call the callback if supplied"""
        settings = self.collect_dialog_settings()
        handler_id = self.handler_name_combo_entry.child.get_text().strip()
        if not handler_id:
            dialog = InfoDialog("Identifier Required",
                                "The Handler requires a Name.",
                                modal=True)
            dialog.run()
            return
        if handler_id in self.handlers:
            buttons = (gtk.STOCK_CANCEL,
                       gtk.RESPONSE_CANCEL,
                       gtk.STOCK_APPLY,
                       gtk.RESPONSE_APPLY,)

            dialog = ResponseDialog("Overwrite?",
                                    "Overwrite the handler named {0}? "
                                    "Profiles that use this handler will "
                                    "be affected.".format(handler_id),
                                    buttons=buttons)
            response = dialog.run()
            if response != gtk.RESPONSE_APPLY:
                return
        self.handlers[handler_id] = settings
        client.filebottool.update_handlers(self.handlers)
        self.window.destroy()
        if self.cb:
            self.cb(handler_id)

    def on_cancel_changes_clicked(self, *args):
        self.window.destroy()
