__author__ = 'Lunchbox'


import gtk

class InfoDialog(gtk.Dialog):
    """
    Loads and shows a dialog to the user informing them of some even.
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