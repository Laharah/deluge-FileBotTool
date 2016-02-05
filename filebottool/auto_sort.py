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

FilterRule = namedtuple("FilterRule", ["id", "field", "operator", "value",
                                       "handler_name"])


def check_rules(torrent_id, sorting_rules):
    """
    match sorting rules to a torrent id and get appropriate handler
    Args:
        torrent_id: torrent_id
        sorting_rules: list of rule tuples

    Returns: handler name or None
    """
    torrent = component.get("TorrentManager")[torrent_id]
    sorting_rules = [FilterRule(*rule) for rule in sorting_rules]
    for rule in sorted(sorting_rules):
        # noinspection PyCallingNonCallable
        if OPERATOR_MAP[rule.operator](torrent.get_status([rule.field])[rule.field],
                                       rule.value):
            log.info("Torrent {0} matched rule {1}".format(torrent_id, rule.id))
            return rule.handler_name

    else:
        log.debug("No rule filter matched for torrent {}".format(torrent_id))
        return None
