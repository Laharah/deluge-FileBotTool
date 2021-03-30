__author__ = 'laharah'


# noinspection PyUnresolvedReferences
from gi.repository import Gtk
# noinspection PyUnresolvedReferences
from deluge.ui.client import client

from filebottool.gtkui.common_gtk3 import inflate_list_store_combo
from filebottool.common import LOG
import user_messenger_gtk3

log = LOG


class HandlerUI(object):
    """
    handles ui functions for initializing and manipulating filebot handler
    widgets.

    Assumes that the ui file passed has correctly named widgets.

    Args:
        builder: A Gtk.ui object containing the following widgets:
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
            subs_language_entry
    """
    def __init__(self, builder, settings=None):
        """
        Initial setup
        :param builder: a Gtk.builder object, see class doc_strings for info
        :param settings: a dict of handler settings to pre-populate with
        """
        self.builder = builder
        self.initial_settings = settings
        self.database_combo = self.builder.get_object("database_combo")
        self.rename_action_combo = self.builder.get_object("rename_action_combo")
        self.on_conflict_combo = self.builder.get_object("on_conflict_combo")
        self.episode_order_combo = self.builder.get_object("episode_order_combo")

        self.format_string_entry = self.builder.get_object("format_string_entry")
        self.query_entry = self.builder.get_object("query_entry")
        self.download_subs_checkbox = self.builder.get_object("download_subs_checkbox")
        self.subs_language_entry = self.builder.get_object("subs_language_entry")
        self.language_code_entry = self.builder.get_object("language_code_entry")
        self.encoding_entry = self.builder.get_object("encoding_entry")
        self.output_entry = self.builder.get_object("output_entry")

        self.populated = False
        self.monitor_changes = True

        self.builder.connect_signals(
            {'on_conflict_combo_changed': self.on_conflict_combo_changed}
        )

        client.filebottool.get_filebot_valid_values().addCallback(
            self.init_combo_boxes)

    def init_combo_boxes(self, combo_data):
        """retrieves valid values for combo boxes and inflates them"""
        self.monitor_changes = False

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
        self.populated = True
        self.monitor_changes = True

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
            try:
                value_index = [index for index, row in enumerate(combo_model)
                               if row[0] == value][0]
            except IndexError:
                log.warning("could not set {0} to value {1}, value {1} could "
                            "not be found in {0}".format(combo, value))
            else:
                combo.set_active(value_index)

        entry_value_pairs = [
            (self.format_string_entry, settings.get("format_string", '')),
            (self.encoding_entry, settings.get("encoding", '')),
            (self.subs_language_entry, settings.get("subs_language", '')),
            (self.language_code_entry, settings.get("language_code", '')),
            (self.query_entry, settings.get("query_override", '')),
            (self.output_entry, settings.get("output", '')),
        ]

        log.debug("Setting entry widgets")
        for entry, value in entry_value_pairs:
            if value:
                entry.set_text(value)
            else:
                entry.set_text('')

        if settings["download_subs"]:
            self.download_subs_checkbox.set_active(True)
        else:
            self.download_subs_checkbox.set_active(False)

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
            else:
                settings[setting] = None

        entries = {
            "format_string": self.format_string_entry,
            "encoding": self.encoding_entry,
            "language_code": self.language_code_entry,
            "subs_language": self.subs_language_entry,
            "query_override": self.query_entry,
            "output": self.output_entry
        }
        for setting in entries:
            if not entries[setting]:
                entries[setting] = ''
            settings[setting] = entries[setting].get_text()

        settings["show_advanced"] = self.builder.get_object(
            "advanced_options").get_visible()
        settings["download_subs"] = self.download_subs_checkbox.get_active()

        log.debug("Collected settings for server: {0}".format(settings))
        return settings

    def on_conflict_combo_changed(self, on_conflict, *args):
        if not self.monitor_changes:
            return
        model = on_conflict.get_model()
        current_iter = on_conflict.get_active_iter()
        if current_iter:
            setting = model[current_iter][0]
        else:
            setting = None

        if setting == 'override':
            msg = 'Warning, override conflict resolution may overwrite files! Use Carefully!'
            warning = user_messenger.InfoDialog('FilebotTool Warning!', msg, modal=True)
            warning.run_async()
        return
