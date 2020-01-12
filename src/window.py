# window.py
#
# Copyright 2020 Alexey Mikhailov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from subprocess import Popen, PIPE
import time
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/amikha1lov/recApp/window.ui')
class RecappWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'recAppWindow'

    _record_button = Gtk.Template.Child()
    _stop_record_button = Gtk.Template.Child()
    _popover_about_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        self._record_button.set_visible(False)
        self._stop_record_button.set_visible(True)
        print("RECORD")
        fileName ="Recording from " + time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())
        self.video = Popen("gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true ! video/x-raw,framerate=25/1 ! queue ! videoscale ! videoconvert ! vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2 ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.webm".format(fileName), shell=True)


    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        self._stop_record_button.set_visible(False)
        self._record_button.set_visible(True)
        print("STOP")
        self.video.terminate()

    @Gtk.Template.Callback()
    def on__popover_about_button_clicked(self, button):
        print("About")
        about = Gtk.AboutDialog()
        about.set_program_name(_("RecApp"))
        about.set_version("0.0.1")
        about.set_authors(["Alexey Mikhailov"])
        about.set_copyright("GPLv3+")
        about.set_comments(_("Simple app for recording desktop"))
        about.set_website("https://github.com/amikha1lov/recApp")
        about.set_website_label(_("Website"))
        about.set_wrap_license(True)
        about.set_license_type(Gtk.License.GPL_3_0)
        about.run()
        about.destroy()




