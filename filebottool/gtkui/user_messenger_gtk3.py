"""
Classes and functions for displaying error/warning/info dialogs to the user.
"""
from __future__ import absolute_import
__author__ = 'laharah'

# noinspection PyUnresolvedReferences
from gi.repository import Gtk, Gdk
import pprint
from filebottool.common import LOG

log = LOG


class InfoDialog(Gtk.Dialog):
    """
    Loads and shows a dialog to the user informing them of some event.
    used to display errors.
    """

    def __init__(self, title, message, parent=None, modal=False):
        if modal:
            modal = Gtk.DialogFlags.MODAL
        else:
            modal = 0
        Gtk.Dialog.__init__(self, title, parent, modal, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        #GObject.GObject.__init__(self, title, parent, modal, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.message = message
        self.modal = modal
        label = Gtk.Label(label=message)
        self.get_content_area().add(label)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_gravity(Gdk.Gravity.CENTER)
        self.show_all()

    def run_async(self):
        """a version of run that does not block"""

        def dialog_response_cb(dialog, response_id):
            dialog.destroy()

        if not self.modal:
            self.set_modal(True)
        self.connect('response', dialog_response_cb)
        self.show()


class ResponseDialog(Gtk.Dialog):
    """
    Loads and shows a dialog that presents a user with options, one of which they must
    choose to continue. Defaults to OK and Cancle Buttons.
    """

    def __init__(self, title, message, parent=None, modal=True, buttons=None):
        if not buttons:
            buttons = (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT, Gtk.STOCK_CANCEL,
                       Gtk.ResponseType.CANCEL)
        modal = Gtk.DialogFlags.MODAL if modal else 0
        super(self.__class__, self).__init__(title, parent, modal, buttons)
        self.message = message
        label = Gtk.Label(label=message)
        self.get_content_area().add(label)
        self.set_gravity(Gdk.Gravity.CENTER)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.show_all()


class UserMessenger(object):
    """
    handles the formatting and creation of dialogs to display info to the user.
    """

    def __init__(self):
        pass

    def show_new_files(self, files):
        """
        Given a list of new files, display message showing them to the user
        Args:
            files: list of files or file => linked file pairs
        """
        message = """FileBot has created the following new files:\n"""
        title = "New Files Created"
        dialog = InfoDialog(title, message)
        files = [' => '.join(f) if isinstance(f, tuple) else f for f in files]
        files = pprint.pformat(files)
        text_view = Gtk.TextView()
        text_view.get_buffer().set_text(files)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.show()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.show()
        sw.add(text_view)
        detail_view = Gtk.Frame()
        detail_view.set_shadow_type(Gtk.ShadowType.IN)
        detail_view.add(sw)
        detail_view.set_border_width(6)
        dialog.vbox.add(detail_view)
        text_view.set_size_request(485, 300)
        detail_view.show()
        dialog.run_async()
        return

    def display_errors(self,
                       errors,
                       title=None,
                       message=None,
                       parent=None,
                       modal=False,
                       show_details=False,
                       response_needed=False):
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

        if message is None:
            message = ("One or more errors occurred in FileBotTool. Click \"Show"
                       " Details\" for more info.")
        if title is None:
            title = "FilebotTool Error"
        dialog = InfoDialog(title, message, parent, modal)
        error_details = format_errors(errors)
        text_view = Gtk.TextView()
        text_view.get_buffer().set_text(error_details)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.show()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.show()
        sw.add(text_view)
        detail_view = Gtk.Frame()
        detail_view.set_shadow_type(Gtk.ShadowType.IN)
        detail_view.add(sw)
        detail_view.set_border_width(6)
        dialog.vbox.add(detail_view)
        text_view.set_size_request(485, 300)

        info_button = Gtk.Button("Show Details")

        def _show_details(_):
            detail_view.show()

        if show_details:
            _show_details(None)

        info_button.connect("clicked", _show_details)
        dialog.action_area.pack_start(info_button, True, True, 0)
        dialog.action_area.reorder_child(info_button, 0)
        info_button.show()

        if response_needed:
            response = None
            while response not in [Gtk.ResponseType.OK, Gtk.ResponseType.DELETE_EVENT]:
                response = dialog.run()
            dialog.destroy()
            return response
        else:
            dialog.run_async()
            return

    def display_text(self, title, text, parent=None, modal=False):
        dialog = InfoDialog(title, None, parent, modal)
        text_view = Gtk.TextView()
        text_view.get_buffer().set_text(text.decode('utf8'))
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.show()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.show()
        sw.add(text_view)
        detail_view = Gtk.Frame()
        detail_view.set_shadow_type(Gtk.ShadowType.IN)
        detail_view.add(sw)
        detail_view.set_border_width(6)
        dialog.get_content_area().add(detail_view)
        detail_view.show()
        text_view.set_size_request(485, 300)
        dialog.run_async()
        return


def format_errors(errors):
    """
    formats errors into a human readable text blob.

    :param errors: dictionary in format {torrent_id: (error, error_msg),...}
    """
    error_list = []

    for torrent_id in errors:
        if torrent_id != 0:
            text = "{0} error on torrent {1}:\n".format(errors[torrent_id][0], torrent_id)
        else:
            text = "{0} error:\n".format(errors[torrent_id][0])

        text += ''.join("    {0}\n".format(l) for l in errors[torrent_id][1].splitlines())
        error_list.append(text)

    return '\n'.join(error_list)
