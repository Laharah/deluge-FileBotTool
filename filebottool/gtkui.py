#
# gtkui.py
#
# Copyright (C) 2009 laharah <laharah+fbt@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import gtk
import webbrowser

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import get_resource

class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        self.glade.signal_autoconnect({
            "on_format_help_clicked": self.on_format_help_clicked
        })

        component.get("Preferences").add_page("FileBotTool", self.glade.get_widget("prefs_box"))
        log.debug('filebot tool added to pref pages')
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

    def disable(self):
        component.get("Preferences").remove_page("FileBotTool")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('button was clicked')
        self.glade.get_widget("filebot_version").set_text("CLICKED!!!")

    def on_apply_prefs(self):
        log.debug("applying prefs for FileBotTool")
        config = {
            "test":self.glade.get_widget("txt_test").get_text()
        }
        #client.filebottool.set_config(config)

    def on_show_prefs(self):
        client.filebottool.get_filebot_version().addCallback(
            self.cb_get_config)

    def cb_get_config(self, version):
        "callback for on show_prefs"
        self.glade.get_widget("filebot_version").set_text(version)
