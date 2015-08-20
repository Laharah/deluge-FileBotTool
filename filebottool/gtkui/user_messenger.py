"""
Classes and functions for displaying error/warning/info dialogs to the user.
"""
__author__ = 'jaredanderson'


# noinspection PyUnresolvedReferences
import gtk
from filebottool.common import Log

log = Log()


class UserMessenger(object):
    """
    handles the formatting and creation of dialogs to display info to the user.
    """

    def __init__(self):
        pass

    def display_error(self, errors, parent=None, modal=False):
        """
        Given a dictionary of errors, display them as a dialog for the user.
        :param errors:dictionary in format {torrent_id; (error, error_message)
            OR tuple in format (error, error_message)
        :param parent: Optional parent of the new dialog displayed.
        :param modal: Make dialog modal
        :return:
        """
        if isinstance(errors, tuple):
            errors = {0: errors}

        message = ("One or more errors occurred in FileBotTool. Click \"Show"
                   " Details\" for more info.")
        dialog = InfoDialog("FilebotTool Error", message, parent, modal)
        error_details = format_errors(errors)
        text_view = gtk.TextView()
        text_view.get_buffer().set_text(error_details)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.show()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.show()
        sw.add(text_view)
        detail_view = gtk.Frame()
        detail_view.set_shadow_type(gtk.SHADOW_IN)
        detail_view.add(sw)
        detail_view.set_border_width(6)
        dialog.vbox.add(detail_view)
        text_view.set_size_request(485, 300)

        info_button = gtk.Button("Show Details")

        def _show_details(_):
            detail_view.show()

        info_button.connect("clicked", _show_details)
        dialog.action_area.pack_start(info_button)
        dialog.action_area.reorder_child(info_button, 0)
        info_button.show()

        response = None
        while response not in [gtk.RESPONSE_OK, gtk.RESPONSE_DELETE_EVENT]:
            response = dialog.run()
        dialog.destroy()
        return response


def format_errors(errors):
    """
    formats errors into a human readable text blob.

    :param errors: dictionary in format {torrent_id: (error, error_msg),...}
    """
    error_list = []

    for torrent_id in errors:
        if torrent_id != 0:
            text = "{} error on torrent {}:\n".format(errors[torrent_id][0], torrent_id)
        else:
            text = "{} error:\n".format(errors[torrent_id][0])

        text += ''.join("    {}\n".format(l) for l in errors[torrent_id][1].splitlines())
        error_list.append(text)

    return '\n'.join(error_list)


class InfoDialog(gtk.Dialog):
    """
    Loads and shows a dialog to the user informing them of some event.
    used to display errors.
    """

    def __init__(self, title, message, parent=None, modal=False):
        if modal:
            modal = gtk.DIALOG_MODAL
        else:
            modal = 0
        gtk.Dialog.__init__(self, title, parent, modal, (gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.message = message
        label = gtk.Label(message)
        self.get_content_area().add(label)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_gravity(gtk.gdk.GRAVITY_CENTER)
        self.show_all()
