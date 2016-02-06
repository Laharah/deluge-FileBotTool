__author__ = 'laharah'


import gtk
import time

import deluge.component as component

from filebottool.common import get_resource
from filebottool.common import Log
from filebottool.gtkui.common import EditableList
from filebottool.gtkui.handler_editor import HandlerEditor
import filebottool.auto_sort

SORT_OPERATORS = filebottool.auto_sort.OPERATOR_MAP.keys()
FilterRule = filebottool.auto_sort.FilterRule

log = Log()


class ConfigUI(object):
    """handles the UI portion of getting and setting preferences"""

    def __init__(self, settings=None):
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        self.config_page = self.glade.get_widget("prefs_box")
        self.pref_dialog = component.get("Preferences").pref_dialog

        model = gtk.ListStore(str)
        view = self.glade.get_widget('saved_handlers_listview')
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Profile Name", renderer, text=0)
        view.append_column(column)
        model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.handlers_list = EditableList(view, model)

        model = gtk.ListStore(str, str, str, str)
        view = self.glade.get_widget('rule_listview')
        options = [
            ("Field:", ('label', 'tracker', 'save_path')),
            ("Comparison Operator:", SORT_OPERATORS),
        ]
        for col_index, tup in enumerate(options):
            name, items= tup
            combo_model = gtk.ListStore(str)
            for item in items:
                combo_model.append([item])
            cb = build_combo_renderer_cb(model, col_index, items)
            renderer = build_combo_cellrenderer(combo_model, cb)
            column = gtk.TreeViewColumn(name, renderer, text=col_index)
            view.append_column(column)
        renderer = gtk.CellRendererText()
        renderer.set_property("editable", True)
        def text_edited(widget, path, text):
            model[path][2] = text
        renderer.connect("edited", text_edited)
        column = gtk.TreeViewColumn("Pattern to Match:", renderer, text=2)
        view.append_column(column)
        self.rules_list = EditableList(view, model)

        self.glade.signal_autoconnect({
            "on_add_handler": self.on_add_handler,
            "on_remove_handler": self.handlers_list.remove,
            "on_edit_handler": self.on_edit_handler,
            "on_move_rule_up": self.rules_list.move_up,
            "on_move_rule_down": self.rules_list.move_down,
            "on_remove_rule": self.rules_list.remove,
            "on_add_rule": self.on_add_rule,
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
        column = gtk.TreeViewColumn(column_name, self.rule_handler_combo, text=3)
        self.rules_list.view.append_column(column)
        self.rules_list.clear()
        for rule in rules:
            self.rules_list.add(rule[1:])
        for column in self.rules_list.view.get_columns():
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
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


#########
#  Section: Utilities
#########

def build_combo_renderer_cb(list_store, column_number, allowed=None):
    def cb(widget, path, text):
        if allowed:
            if text not in allowed:
                return
        log.debug('{} {} {}'.format(widget, path, text))
        list_store[path][column_number] = text
    return cb

def build_combo_cellrenderer(model, cb):
    renderer = gtk.CellRendererCombo()
    if model:
        renderer.set_property("model", model)
    renderer.set_property("editable", True)
    renderer.set_property("text-column", 0)
    renderer.connect("edited", cb)
    return renderer