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
import pulsectl
import gi
import os
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk,GLib, Wnck



@Gtk.Template(resource_path='/com/github/amikha1lov/recApp/window.ui')
class RecappWindow(Gtk.ApplicationWindow):
    video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true ! video/x-raw,framerate=30/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
    active_radio = "Fullscreen"
    soundOn = ""
    active_window_id = None
    recordSoundOn = False
    quality_video = "vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2"
    __gtype_name__ = 'recAppWindow'

    _record_button = Gtk.Template.Child()
    _stop_record_button = Gtk.Template.Child()
    _sound_on_switch = Gtk.Template.Child()
    _sound_box = Gtk.Template.Child()
    _radio_full = Gtk.Template.Child()
    _radio_window = Gtk.Template.Child()
    _recording_mode_box = Gtk.Template.Child()
    _select_window_box = Gtk.Template.Child()
    _label_video_saved_box = Gtk.Template.Child()
    _select_window_combobox = Gtk.Template.Child()
    _window_research_button = Gtk.Template.Child()
    _quality_video_switcher = Gtk.Template.Child()
    _popover_about_button = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def on__sound_on_switch_activate(self, switch, gparam):

        if switch.get_active():
            state = "on"
            with pulsectl.Pulse() as pulse:
                print(pulse.sink_list())
                soundOnSource = pulse.sink_list()[0].name
                self.recordSoundOn = True
                print(soundOnSource)
                self.soundOn = " pulsesrc provide-clock=false device='{}.monitor' ! 'audio/x-raw,channels=2,rate=48000,format=F32LE,payload=96' ! queue ! audioconvert ! vorbisenc ! queue ! mux. -e".format(soundOnSource)
                print(self.soundOn)
        else:
            state = "off"
            self.recordSoundOn = False
        print("Switch was turned", state)


    @Gtk.Template.Callback()
    def on__quality_video_switcher_state_set(self, switch, gparam):
        if switch.get_active():
            state = "on"
            self.quality_video = "vp8enc min_quantizer=10 max_quantizer=50 cq_level=13 cpu-used=5 deadline=1000000 threads=8"
        else:
            state = "off"
            self.quality_video = "vp8enc min_quantizer=20 max_quantizer=20 cq_level=13 cpu-used=2 deadline=1000000 threads=2"
        print("Switch was turned", state)



    @Gtk.Template.Callback()
    def on_button_toggled(self, button):

        if button.get_active():
            activeRadioName = button.get_name()
            if (activeRadioName == "Fullscreen"):
                self._select_window_box.set_visible(False)
                self._record_button.set_sensitive(True)
                self.active_radio = "Fullscreen"
                self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true ! video/x-raw,framerate=30/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
            elif (activeRadioName == "Window"):
                if (self.active_window_id is None):
                    self._record_button.set_sensitive(False)
                screen = Wnck.Screen.get_default()
                screen.force_update()
                screen.get_windows()

                self._select_window_combobox.remove_all()
                for window in screen.get_windows():
                        self._select_window_combobox.insert(-1,str(window.get_xid()),window.get_name()[0:80])


                self._select_window_box.set_visible(True)
                self.active_radio = "Window"
                self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer=true xid={} ! video/x-raw,framerate=30/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"

    @Gtk.Template.Callback()
    def on__window_research_button_clicked(self, button):
        print("1")s
        screen = Wnck.Screen.get_default()
        screen.force_update()
        screen.get_windows()

        self._select_window_combobox.remove_all()
        for window in screen.get_windows():
            self._select_window_combobox.insert(-1,str(window.get_xid()),window.get_name()[0:80])






    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        fileNameTime ="Recording-from-" + time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())
        fileName = os.path.join(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS),fileNameTime)
        if (self.active_radio == "Fullscreen"):
            if self.recordSoundOn == True:
                self.video = Popen(self.video_str.format(self.quality_video,fileName) + self.soundOn, shell=True)

            else:
                self.video = Popen(self.video_str.format(self.quality_video,fileName), shell=True)
        elif (self.active_radio == "Window"):
            print(self.active_window_id)
            if self.recordSoundOn == True:
                 self.video_str = self.video_str.format(self.active_window_id,self.quality_video,fileName) + self.soundOn
                 self.video = Popen(self.video_str, shell=True)

            else:
                self.video_str = self.video_str.format(self.active_window_id,self.quality_video,fileName)
                self.video = Popen(self.video_str, shell=True)



        self._record_button.set_visible(False)
        self._recording_mode_box.set_visible(False)
        self._select_window_box.set_visible(False)
        self._label_video_saved_box.set_visible(True)
        self._sound_box.set_visible(False)
        self._stop_record_button.set_visible(True)




    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        if (self.active_radio == "Window"):
            self._select_window_box.set_visible(True)
        self._label_video_saved_box.set_visible(False)
        self._stop_record_button.set_visible(False)
        self._recording_mode_box.set_visible(True)
        self._record_button.set_visible(True)
        self._sound_box.set_visible(True)
        self.video.kill()


    @Gtk.Template.Callback()
    def on__select_window_combobox_changed(self, box):
        self.active_window_id = hex(int(box.get_active_id()))
        print(self.active_window_id)
        if (self.active_window_id is not None):
            self._record_button.set_sensitive(True)
        self.video_str = "gst-launch-1.0 ximagesrc use-damage=0 num-buffers=-1 show-pointer=true xid={} ! video/x-raw,framerate=30/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
        print(self.video_str)




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




