"""
Module that watches for finished torrents and decides if filebottool should
sort them.
"""
__author__ = 'jaredanderson'

from collections import namedtuple
import re

# noinspection PyUnresolvedReferences
import deluge.component as component

from filebottool.common import Log

log = Log()

OPERATOR_MAP = {
    "is": lambda x, y: x == y,
    "contains": lambda x, y: x in y,
    "starts with": lambda x, y: x.startswith(y),
    "ends with": lambda x, y: x.endswith(y),
    "matches(regex)": lambda x, y: re.search(y, x),
}

FilterRule = namedtuple("FilterRule", ["field", "operator", "value",
                                       "handler_id"])


class AutoSortManager(object):
    """
    class to monitor new torrents and execute filebot sorts on them if
    appropriate
    """

    def __init__(self, filebottool_parent, sorting_rules=None):
        """
        inits the manager, optionally takes in set of sort rules
        :param sorting_rules: dictionary of rules to pre-set
        sorting_rules = {index(int): filter_rule
        :return:
        """
        self.torrent_manager = component.get("TorrentManager")
        self.filebottool = filebottool_parent
        self.listener_registered = False
        self._sorting_rules = None
        self.sorting_rules = sorting_rules

    @property
    def sorting_rules(self):
        return self._sorting_rules

    @sorting_rules.setter
    def sorting_rules(self, rules):
        """registers or de-registers the listener if required."""
        if not self.listener_registered and rules:
            self._register_listener()
        if self.listener_registered and not rules:
            self._deregister_listener()

        self._sorting_rules = rules

    def _register_listener(self):
        component.get("EventManager").register_event_handler(
            "TorrentFinishedEvent", self.check_rules)
        self.listener_registered = True

    def _deregister_listener(self):
        component.get("EventManager").deregister_event_handler(
            "TorrentFinishedEvent", self.check_rules)

    def check_rules(self, torrent_id):
        """
        Goes through the sort rules in order, and executes on the first rule
        that succeeds.

        Is executed by the listener when any torrent completes.

        :param torrent_id:
        :return:
        """
        torrent = self.torrent_manager[torrent_id]
        for rule_id in sorted(self.sorting_rules):
            rule = self.sorting_rules[rule_id]
            # noinspection PyCallingNonCallable
            if OPERATOR_MAP[rule.operator](torrent.get_status([rule.field])[
                                           rule.field], rule.value):
                log.debug("executing filebot rename on torrent {0} with "
                          "handler, {1}".format(torrent_id, rule.handler_id))
                self.filebottool.do_rename(
                    torrent_id,
                    handler_settings=self.filebottool.config["saved_handlers"][
                        rule.handler_id]
                )
                break
        else:
            log.debug("No rule filter matched for torrent {}".format(
                torrent_id))
