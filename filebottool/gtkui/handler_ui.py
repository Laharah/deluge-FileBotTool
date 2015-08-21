__author__ = 'Lunchbox'


# noinspection PyUnresolvedReferences
import gtk
# noinspection PyUnresolvedReferences
from deluge.ui.client import client

from filebottool.gtkui.common import inflate_list_store_combo
from filebottool.common import Log

log = Log()


class HandlerUI(object):
    """
    handles ui functions for initializing and manipulating filebot handler
    widgets.

    Assumes that the glade file passed has correctly named widgets.

    Args:
        glade: A gtk.glade object containing the following widgets:
            format_string_entry
            output_entry
            rename_action_combo
            database_combo
            query_entry
            episode_order_combo
            on_conflict_combo
            download_subs_checkbox
            encoding_entry
            language_code_entry
    """
    def __init__(self, glade, settings=None):
        """
        Initial setup
        :param glade: a gtk.glade object, see class doc_strings for info
        :param settings: a dict of handler settings to pre-populate with
        """
        self.glade = glade
        self.initial_settings = settings
        self.database_combo = self.glade.get_widget("database_combo")
        self.rename_action_combo = self.glade.get_widget("rename_action_combo")
        self.on_conflict_combo = self.glade.get_widget("on_conflict_combo")
        self.episode_order_combo = self.glade.get_widget("episode_order_combo")

        self.format_string_entry = self.glade.get_widget("format_string_entry")
        self.query_entry = self.glade.get_widget("query_entry")
        self.download_subs_checkbox = self.glade.get_widget("download_subs_checkbox")
        self.language_code_entry = self.glade.get_widget("language_code_entry")
        self.encoding_entry = self.glade.get_widget("encoding_entry")
        self.output_entry = self.glade.get_widget("output_entry")

        client.filebottool.get_filebot_valid_values().addCallback(
            self.init_combo_boxes)

    def init_combo_boxes(self, combo_data):
        """retrieves valid values for combo boxes and inflates them"""

        log.debug("building database combo box")
        databases = combo_data["valid_databases"]
        inflate_list_store_combo(databases, self.database_combo)

        log.debug("building rename action combo box")
        rename_actions = combo_data["valid_rename_actions"]
        inflate_list_store_combo(rename_actions, self.rename_action_combo)

        log.debug("building on conflict combo box")
        on_conflicts = combo_data["valid_on_conflicts"]
        inflate_list_store_combo(on_conflicts, self.on_conflict_combo)

        log.debug("building episode order combo box")
        episode_orders = combo_data["valid_episode_orders"]
        inflate_list_store_combo(episode_orders, self.episode_order_combo)

        if self.initial_settings:
            self.populate_with_settings(self.initial_settings)

    def populate_with_settings(self, settings):
        """populates the UI with the desired settings dictionary
        Args:
          settings: The settings dict to populate.
        """
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
            (self.query_entry, settings["query_override"]),
            (self.output_entry, settings["output"])
        ]

        log.debug("Setting entry widgets")
        for entry, value in entry_value_pairs:
            if value:
                entry.set_text(value)

        if settings["download_subs"]:
            self.download_subs_checkbox.set_active(True)

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
            current_iter = combos[setting].get_active_iter()
            if current_iter:
                settings[setting] = combo_model[current_iter][0]

        entries = {
            "format_string": self.format_string_entry,
            "encoding": self.encoding_entry,
            "language_code": self.language_code_entry,
            "query_override": self.query_entry,
            "output": self.output_entry
        }
        for setting in entries:
            settings[setting] = entries[setting].get_text()

        settings["show_advanced"] = self.glade.get_widget(
            "advanced_options").get_visible()
        settings["download_subs"] = self.download_subs_checkbox.get_active()

        log.debug("Collected settings for server: {0}".format(settings))
        return settings