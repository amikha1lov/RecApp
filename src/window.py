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
import sys
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk,Gst,GLib
Gtk.init(sys.argv)
# initialize GStreamer
Gst.init(sys.argv)




@Gtk.Template(resource_path='/com/github/amikha1lov/rec_app/window.ui')
class RecappWindow(Gtk.ApplicationWindow):
    video_str = "gst-launch-1.0 ximagesrc use-damage=0 show-pointer={} ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
    soundOn = ""
    coordinateMode = False
    coordinateArea = ""
    recordSoundOn = False
    delayBeforeRecording = 0
    videoFrames = 30
    recordMouse = False
    quality_video = "vp8enc min_quantizer=20 max_quantizer=20 cpu-used=2 deadline=1000000 threads=2"
    __gtype_name__ = 'recAppWindow'

    _record_button = Gtk.Template.Child()
    _stop_record_button = Gtk.Template.Child()
    _frames_combobox = Gtk.Template.Child()
    _delay_button = Gtk.Template.Child()
    _select_area_button = Gtk.Template.Child()
    _sound_on_switch = Gtk.Template.Child()
    _sound_box = Gtk.Template.Child()
    _label_video_saved_box = Gtk.Template.Child()
    _quality_video_switcher = Gtk.Template.Child()
    _popover_about_button = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    @Gtk.Template.Callback()
    def on__frames_combobox_changed(self, box):
        print("combo change")
        self.videoFrames = box.get_active_text()
        print(box.get_active_text())


    @Gtk.Template.Callback()
    def on__record_mouse_switcher_state_set(self, switch, gparam):
        print("Active mouse")
        if switch.get_active():
            state = "on"
            self.recordMouse = True
        else:
            state = "off"
            self.recordMouse = False
        print("Switch was turned", state)

    @Gtk.Template.Callback()
    def on__delay_button_change_value(self, spin):
        self.delayBeforeRecording = spin.get_value_as_int()
        print(spin.get_value_as_int())


    @Gtk.Template.Callback()
    def on__select_area_button_clicked(self, spin):
        print("clicccc")
        coordinate = Popen("slop -n -c 0.3,0.4,0.6,0.4 -l -t 0 -f '%w %h %x %y'",shell=True,stdout=PIPE).communicate()
        print(coordinate)
        listCoor = list(coordinate)
        listCoor = listCoor[0].decode().split()

        startx,starty,endx,endy=int(listCoor[2]),int(listCoor[3]),int(listCoor[2])+int(listCoor[0]),int(listCoor[1])+int(listCoor[3])
        self.coordinateArea = "startx={} starty={} endx={} endy={}".format(startx,starty,endx,endy)
        print(self.coordinateArea)
        self.coordinateMode = True



    @Gtk.Template.Callback()
    def on__sound_on_switch_activate(self, switch, gparam):
        print("Active sound")
        if switch.get_active():
            state = "on"
            with pulsectl.Pulse() as pulse:
                print(pulse.sink_list())
                soundOnSource = pulse.sink_list()[0].name
                self.recordSoundOn = True
                print(soundOnSource)
                self.soundOn = " pulsesrc provide-clock=false device='{}.monitor' buffer-time=20000000 ! 'audio/x-raw,depth=24,channels=2,rate=44100,format=F32LE,payload=96' ! queue ! audioconvert ! vorbisenc ! queue ! mux. -e".format(soundOnSource)
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
    def on__record_button_clicked(self, button):
        fileNameTime ="Recording-from-" + time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())
        fileName = os.path.join(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS),fileNameTime)
        time.sleep(self.delayBeforeRecording)
        if self.coordinateMode == True:
            video_str = "gst-launch-1.0 ximagesrc show-pointer={} " +self.coordinateArea +" ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
            print(video_str)
            if self.recordSoundOn == True:
                self.video = Popen(video_str.format(self.recordMouse,self.videoFrames,self.quality_video,fileName) + self.soundOn, shell=True)

            else:
                self.video = Popen(video_str.format(self.recordMouse,self.videoFrames,self.quality_video,fileName), shell=True)
        else:
            if self.recordSoundOn == True:
                self.video = Popen(self.video_str.format(self.recordMouse,self.videoFrames,self.quality_video,fileName) + self.soundOn, shell=True)

            else:
                self.video = Popen(self.video_str.format(self.recordMouse,self.videoFrames,self.quality_video,fileName), shell=True)




        self._record_button.set_visible(False)
        self._stop_record_button.set_visible(True)


    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):

        self.video.terminate()
        self._stop_record_button.set_visible(False)
        self._record_button.set_visible(True)



    @Gtk.Template.Callback()
    def on__popover_about_button_clicked(self, button):
        print("About")
        about = Gtk.AboutDialog()
        about.set_program_name(_("RecApp"))
        about.set_version("0.0.1")
        about.set_authors(["Alexey Mikhailov","Artem Polishchuk","@Letalis (Telegram)", "@gasinvein (Telegram)", "@dead_mozay (Telegram)"])
        about.set_artists(["Raxi Petrov"])
        about.set_copyright("GPLv3+")
        about.set_comments(_("Simple app for recording desktop"))
        about.set_website("https://github.com/amikha1lov/recApp")
        about.set_website_label(_("Website"))
        about.set_wrap_license(True)
        about.set_license_type(Gtk.License.GPL_3_0)
        about.run()
        about.destroy()




