import traceback

from deluge.event import DelugeEvent



class FileBotToolTorrentFinished(DelugeEvent):
    """
    A replacement for deluge's TorrentFinishedEvent that emits after FileBotTool has had
    a chance to complete any actions.
    """

    def __init__(self, torrent_id, handler_name):
        """
        :param torrent_id: The id of the torrent completed.
        :param handler_name: The handler name associated (can be None).
        """
        self._args = [torrent_id, handler_name]

class FileBotToolProcessingError(DelugeEvent):
    """
    emitted when a torrent FileBotTool was processing errored out
    """

    def __init_(self, torrent_id, handler_name, error=None):
        """
        :param torrent_id: The id of the torrent completed.
        :param handler_name: The handler name associated (can be None).
        :param error: optional message or exception object
        """
        if error:
            if isinstance(error, Exception):
                msg = "Exception {0} encountered during processing: {1}"
                msg = msg.format(err.__class__.__name__, traceback.format_exc())
                error = msg
            elif not isinstance(error, str):
                error = str(error)
        else:
            error = ''
        self._args = [torrent_id, handler_name, error]
