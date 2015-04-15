__author__ = 'jaredanderson'


import gtk

from filebottool.common import get_resource
from filebottool.common import Log

log = Log()


class ConfigUI(object):
    """handles the UI portion of getting and setting preferences"""

    def __init__(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        self.config_page = self.glade.get_widget("prefs_box")
        self.auto_sort_orderer = None

    def populate_settings(self, settings):
        """populates the UI widgets with the given settings"""
        saved_handlers = settings["saved_handlers"]
        sorting_rules = settings["auto_sort_rules"]
        if not self.auto_sort_orderer:
            self.auto_sort_orderer = AutoSortOrderer(
                self.glade, saved_handlers, sorting_rules)
        else:
            self.auto_sort_orderer.rules = sorting_rules
            self.auto_sort_orderer.model = (
                self.auto_sort_orderer.build_rule_model(sorting_rules))
            self.auto_sort_orderer.handlers = saved_handlers

    def gather_settings(self, config):
        """
        Updates the given config dictionary and updates the appropriate
        settings.
        """
        self.auto_sort_orderer.reorder_rules()
        config["auto_sort_rules"] = self.auto_sort_orderer.rules
        config["saved_handlers"] = self.auto_sort_orderer.handlers
        return config


class AutoSortOrderer(object):
    def __init__(self, glade, sorting_rules, handlers):
        self.rules = sorting_rules
        self.handlers = handlers

        self.glade = glade
        self.model = self.build_rule_model(self.rules)
        self.listview = self.glade.get_widget("rule_listview")
        self.init_rule_listview(self.model, self.listview)
        self.right_click_menu = self.build_right_click_menu()

        signal_dict = {
            "on_move_selection_up_clicked": self.on_move_selection_up_clicked,
            "on_move_selection_down_clicked":
                self.on_move_selection_down_clicked,
            "on_edit_selection_clicked": self.on_edit_selection_clicked,
            "on_listview_right_click": self.on_listview_right_click

        }
        self.glade.signal_autoconnect(signal_dict)

    def build_rule_model(self, rules):
        # index, filter_str, handler name
        rule_model = gtk.ListStore(int, str, str)
        for index in sorted(rules.keys()):
            rule = rules[index]
            filter_string = " ".join([rule.field, rule.operator, rule.value])
            handler_name = rule.handler_id
            rule_model.append([index, filter_string, handler_name])
        return rule_model

    def init_rule_listview(self, model, view):
        view.set_model(model)
        renderer = gtk.CellRendererText()
        torrent_filter_column = gtk.TreeViewColumn("Torrent Filter",
                                                   renderer, text=1)
        handler_colum = gtk.TreeViewColumn("Filebot Handler", renderer, text=2)
        view.append_column(torrent_filter_column)
        view.append_column(handler_colum)

    def build_right_click_menu(self):
        menu = gtk.Menu()
        delete_rule_item = gtk.MenuItem("Delete Rule")
        menu.append(delete_rule_item)
        menu.show_all()
        return menu

    def reorder_rules(self):
        """
        rebuilds the rule dictionary, incorporating changes in rule order.
        Should always be run before sending rule dictionary back to server
        :return: the new rule dictionary
        """
        new_rules = {}
        for new_index, row in enumerate(self.model):
            new_rules[new_index] = self.rules[row[0]]
        self.rules = new_rules

    def on_move_selection_up_clicked(self, button):
        model, iterator = self.listview.get_selection().get_selected()
        selection_path = model.get_path(iterator)
        try:
            previous_iterator = model.get_iter((selection_path[0] - 1))
        except ValueError:
            return
        model.swap(previous_iterator, iterator)
        self.reorder_rules()

    def on_move_selection_down_clicked(self, button):
        model, iterator = self.listview.get_selection().get_selected()
        next_iterator = model.iter_next(iterator)
        if not next_iterator:
            return
        model.swap(next_iterator, iterator)
        self.reorder_rules()

    def on_edit_selection_clicked(self):
        pass

    def on_listview_right_click(self, widget, event):
        print event
        if event.button == 3:
            self.right_click_menu.popup(None, None, None, event.button,
                                        event.time, None)
