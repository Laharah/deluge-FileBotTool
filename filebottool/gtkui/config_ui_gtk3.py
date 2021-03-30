from __future__ import absolute_import
__author__ = 'laharah'


from gi.repository import Gtk
import os
import time
import webbrowser

from twisted.internet import defer

from deluge.ui.client import client
import deluge.component as component

from filebottool.common import get_resource
from filebottool.common import LOG
from filebottool.gtkui.common_gtk3 import EditableList
from filebottool.gtkui.handler_editor_gtk3 import HandlerEditor
import filebottool.auto_sort

from . import user_messenger_gtk3

SORT_OPERATORS = list(filebottool.auto_sort.OPERATOR_MAP.keys())
VALID_FIELDS = filebottool.auto_sort.VALID_FIELDS

FilterRule = filebottool.auto_sort.FilterRule

log = LOG


class ConfigUI(object):
    """handles the UI portion of getting and setting preferences"""

    def __init__(self, settings=None):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(get_resource("config.ui"))
        self.config_page = self.builder.get_object("prefs_box")
        self.pref_dialog = component.get("Preferences").pref_dialog

        fb_icon = self.builder.get_object("fb_icon")
        image = get_resource("fb_icon16.png")
        fb_icon.set_from_file(image)

        model = Gtk.ListStore(str)
        view = self.builder.get_object('saved_handlers_listview')
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Profile Name", renderer, text=0)
        view.append_column(column)
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.handlers_list = EditableList(view, model)

        model = Gtk.ListStore(str, str, str, str)
        view = self.builder.get_object('rule_listview')
        options = [
            ("Field:", VALID_FIELDS),
            ("Comparison Operator:", SORT_OPERATORS),
        ]
        for col_index, tup in enumerate(options):
            name, items = tup
            combo_model = Gtk.ListStore(str)
            for item in items:
                combo_model.append([item])
            cb = build_combo_renderer_cb(model, col_index, items)
            renderer = build_combo_cellrenderer(combo_model, cb)
            column = Gtk.TreeViewColumn(name, renderer, text=col_index)
            view.append_column(column)
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        def text_edited(widget, path, text):
            model[path][2] = text
        renderer.connect("edited", text_edited)
        column = Gtk.TreeViewColumn("Pattern to Match:", renderer, text=2)
        view.append_column(column)
        self.rules_list = EditableList(view, model)

        self.builder.connect_signals({
            "on_add_handler": self.on_add_handler,
            "on_remove_handler": self.handlers_list.remove,
            "on_edit_handler": self.on_edit_handler,
            "on_move_rule_up": self.rules_list.move_up,
            "on_move_rule_down": self.rules_list.move_down,
            "on_remove_rule": self.rules_list.remove,
            "on_add_rule": self.on_add_rule,
            "on_auto_sort_help_clicked": self.on_auto_sort_help_clicked,
            "on_debug_button_clicked": self.on_debug_button_clicked,
            "on_license_button_clicked": self.on_license_button_clicked,
        })
        self.gather_time = None
        if settings:
            self.populate_settings(settings)

    def populate_settings(self, settings):
        """populates the UI widgets with the given settings"""
        # workaround for new settings being overwritten by previous settings
        if self.gather_time:
            if time.time() - self.gather_time < 1:
                return

        self.config = settings
        self.saved_handlers = settings["saved_handlers"]
        self.handlers_list.clear()
        for name in self.saved_handlers:
            self.handlers_list.add([name])

        rules = settings["auto_sort_rules"]
        if len(self.rules_list.view.get_columns()) == 4:  # force refresh
            self.rules_list.view.remove_column(self.rules_list.view.get_column(3))
        self.rule_handler_combo = build_combo_cellrenderer(
            self.handlers_list.model, self.on_rule_handler_combo_changed)
        column_name = "Profile to Use:"
        column = Gtk.TreeViewColumn(column_name, self.rule_handler_combo, text=3)
        self.rules_list.view.append_column(column)
        self.rules_list.clear()
        for rule in rules:
            self.rules_list.add(rule[1:])
        for column in self.rules_list.view.get_columns():
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column.set_resizable(True)

        if not rules:
            for column in self.rules_list.view.get_columns():
                column.set_expand(True)

    def gather_settings(self):
        """
        Updates the given config dictionary and updates the appropriate
        settings.
        """
        self.gather_time = time.time()
        handlers = {}
        for row in self.handlers_list.get_data():
            handlers[row[0]] = self.saved_handlers[row[0]]
        self.saved_handlers = handlers
        self.config["saved_handlers"] = self.saved_handlers

        rules = []
        log.debug(self.rules_list.get_data())
        for index, row in enumerate(self.rules_list.get_data()):
            field, op, pat, handler = row
            rules.append([index, field, op, pat, handler])

        self.config['auto_sort_rules'] = rules
        return self.config

#########
#  Section: signal handlers
#########

    def on_add_handler(self, widget):
        def new_handler_cb(id, handlers):
            self.handlers_list.add([id])
            self.saved_handlers = handlers
            log.debug(self.saved_handlers)

        HandlerEditor(handlers=self.saved_handlers, cb=new_handler_cb,
                      parent=self.pref_dialog)

    def on_edit_handler(self, widget):
        handler_name = self.handlers_list.get_row()[0]
        def edited_cb(id, handlers):
            self.saved_handlers = handlers
            if id != handler_name:
                del self.saved_handlers[handler_name]
                self.handlers_list.clear()
                for name in self.saved_handlers:
                    self.handlers_list.add([name])

        HandlerEditor(handlers=self.saved_handlers, initial=handler_name,
                      cb=edited_cb, parent=self.pref_dialog)


    def on_add_rule(self, *args):
        self.rules_list.add(['', "is exactly", '', ''])
        path = self.rules_list.model.get_string_from_iter(self.rules_list.model[-1].iter)
        self.rules_list.view.set_cursor(path)

    def on_rule_handler_combo_changed(self, widget, path, text):
        self.rules_list.model[path][3] = text

    def on_auto_sort_help_clicked(self, *args):
        webbrowser.open('https://github.com/Laharah/deluge-FileBotTool/wiki/Auto-Sorting',
                        new=2)

    @defer.inlineCallbacks
    def on_debug_button_clicked(self, button):
        log.debug("Sending request for FileBot debug info...")
        button.set_sensitive(False)
        info = yield client.filebottool.get_filebot_debug()
        log.debug("Displaying debug info")
        dialog = user_messenger.UserMessenger()
        dialog.display_text("Filebot Debug Info", info)
        button.set_sensitive(True)

    @defer.inlineCallbacks
    def on_license_button_clicked(self, button):
        log.debug("License button clicked.")
        chooser = Gtk.FileChooserDialog(_("Choose your FileBot license file"),
            None,
            Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
                        Gtk.ResponseType.OK))

        chooser.set_transient_for(self.pref_dialog)
        chooser.set_property("skip-taskbar-hint", True)
        chooser.set_local_only(False)

        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("FileBot license files"))
        file_filter.add_pattern("*." + "psm")
        chooser.add_filter(file_filter)
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("All files"))
        file_filter.add_pattern("*")
        chooser.add_filter(file_filter)

        # Run the dialog
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            license = chooser.get_filenames()[0]
        else:
            chooser.destroy()
            return
        chooser.destroy()

        # License file should definetly be under 10K
        size = os.stat(license).st_size
        if size > 10*1000:
            e = user_messenger.InfoDialog("Error", "License file is too big.")
            e.resize(220, 125)
            e.run_async()
            defer.returnValue()

        with open(license, 'rb') as l:
            license_data = l.read()
        log.debug("Sending license data to server.")
        result = yield client.filebottool.activate_filebot_license(license_data)
        log.debug("Recieved reply from server: %s", result)
        if result.startswith("FilebotLicenseError: "):
            title = "Error with License File"
            msg = result[21:]
        else:
            title = "Success!"
            msg = result

        dialog = user_messenger.InfoDialog(title, msg)
        dialog.resize(220, 125)
        dialog.run_async()




#########
#  Section: Utilities
#########

def build_combo_renderer_cb(list_store, column_number, allowed=None):
    def cb(widget, path, text):
        if allowed:
            if text not in allowed:
                return
        log.debug('{0} {1} {2}'.format(widget, path, text))
        list_store[path][column_number] = text
    return cb

def build_combo_cellrenderer(model, cb):
    renderer = Gtk.CellRendererCombo()
    if model:
        renderer.set_property("model", model)
    renderer.set_property("editable", True)
    renderer.set_property("text-column", 0)
    renderer.connect("edited", cb)
    return renderer
