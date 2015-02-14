__author__ = 'Lunchbox'


import gtk

class InfoDialog(gtk.Dialog):
    """
    Loads and shows a dialog to the user informing them of some even.
    used to display errors.
    """
    def __init__(self, title, message, parent=None, modal=False):
        gtk.Dialog.__init__(self, title, parent, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK))
        self.message = message
        label = gtk.Label(message)
        self.get_content_area().add(label)
        self.show_all()