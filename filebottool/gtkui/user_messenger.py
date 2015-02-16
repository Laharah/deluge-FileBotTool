__author__ = 'jaredanderson'

import gtk

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
            OR tuple in format (errortype, error_message)
        :return:
        """
        if isinstance(errors, tuple):
            errors = {0: errors}


        message = """One or more errors occurred in FileBotTool. Click
                  \"Show Details\" for more info."""
        dialog = InfoDialog("FilebotTool Error", message, parent, modal)
        dialog.error_details = self.format_errors(errors)

        info_button = gtk.Button("Show Details")
        info_button.connect("clicked", self._show_details)
        dialog.action_area.pack_start(info_button)
        info_button.show()
        return dialog.run()

    def format_errors(self, errors):
        """formats errors into human_readable text."""
        error_list = []

        for id in errors:
            if id != 0:
                text = "{} error on torrent{}:\n".format(errors[id][0], id)
            else:
                text = "{} error:\n".format(errors[id][0])

            text += "    {}".format(errors[id][1])
            error_list.append(text)

        return '\n'.join(error_list)

    def _show_details(self, button):
        dialog = button.get_parent_window()
        DetailDialog("FilebotTool Errors", dialog.error_details)
        dialog.destroy()

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
        gtk.Dialog.__init__(self, title, parent, modal,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.message = message
        label = gtk.Label(message)
        self.get_content_area().add(label)
        self.show_all()

class DetailDialog(gtk.Dialog):
    """A version of dialog that has a text field for displaying details"""
    def __init__(self, title, details, parent=None, modal=False):
        if modal:
            modal = gtk.DIALOG_MODAL
        else:
            modal = 0
        gtk.Dialog.__init__(self, title, parent, modal,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.details = gtk.TextBuffer().set_text(details)
        self.text_view = gtk.TextView(details)
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.add(self.text_view)
        self.get_content_area().add(scrolled_window)
        self.show_all()