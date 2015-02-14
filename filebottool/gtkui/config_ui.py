__author__ = 'jaredanderson'


import gtk

from filebottool.common import get_resource

class ConfigUI(object):
    """handles the UI portion of getting and setting preferences"""
    def __init__(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        self.config_page = self.glade.get_widget("prefs_box")

    def populate_settings(self, settings):
        """populates the UI widgets with the given settings"""
        pass

    def gather_settings(self):
        """gathers the settings from the UI widgets and returns them as a
        dict"""
        pass