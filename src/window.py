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
import gi
import os
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk,GLib, Wnck


@Gtk.Template(resource_path='/com/github/amikha1lov/recApp/window.ui')
class RecappWindow(Gtk.ApplicationWindow):
    video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true ! video/x-raw,framerate=25/1 ! queue ! videoscale ! videoconvert ! vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2 ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.webm"
    active_radio = "Fullscreen"

    active_window_id = ""

    __gtype_name__ = 'recAppWindow'

    _record_button = Gtk.Template.Child()
    _stop_record_button = Gtk.Template.Child()
    _radio_full = Gtk.Template.Child()
    _radio_window = Gtk.Template.Child()
    _select_window_box = Gtk.Template.Child()
    _select_window_combobox = Gtk.Template.Child()
    _popover_about_button = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def on_button_toggled(self, button):
        if button.get_active():
            name = button.get_label()
            if (name == "Fullscreen"):
                self._select_window_box.set_visible(False)
                self.active_radio = "Fullscreen"
                self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true ! video/x-raw,framerate=25/1 ! queue ! videoscale ! videoconvert ! vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2 ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.webm"
            elif (name == "Window"):
                screen = Wnck.Screen.get_default()
                screen.force_update()
                screen.get_windows()
                self._select_window_combobox.remove_all()
                for window in screen.get_windows():
                    self._select_window_combobox.append_text(window.get_name()[0:50] + " id:" + str(window.get_xid()))

                self._select_window_combobox.set_active(0)
                self._select_window_box.set_visible(True)
                self.active_radio = "Window"
                self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true xid={} ! video/x-raw,framerate=25/1 ! queue ! videoscale ! videoconvert ! vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2 ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.webm"




    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        fileNameTime ="Recording-from-gg" + time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())
        fileName = os.path.join(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS),fileNameTime)



        print(fileName)
        if (self.active_radio == "Fullscreen"):
            self.video = Popen(self.video_str.format(fileName), shell=True)
        elif (self.active_radio == "Window"):
            self.video_str = self.video_str.format(self.active_window_id,fileName)
            print(self.video_str)
            self.video = Popen(self.video_str, shell=True)


        self._record_button.set_visible(False)
        self._stop_record_button.set_visible(True)




    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        self._stop_record_button.set_visible(False)
        self._record_button.set_visible(True)
        self.video.terminate()


    @Gtk.Template.Callback()
    def on__select_window_combobox_changed(self, box):
        self.active_window_id = box.get_active_text().rsplit('id:', 1)[1]
        self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true xid={} ! video/x-raw,framerate=25/1 ! queue ! videoscale ! videoconvert ! vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2 ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.webm"



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




