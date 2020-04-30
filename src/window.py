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
import signal
from locale import gettext as _
import locale

from pydbus import SessionBus
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Notify', '0.7')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk,Gst,GLib,Gio,Notify,GstPbutils
Gtk.init(sys.argv)
# initialize GStreamer
Gst.init(sys.argv)




@Gtk.Template(resource_path='/com/github/amikha1lov/rec_app/window.ui')
class RecappWindow(Gtk.ApplicationWindow):

    soundOn = ""
    coordinateMode = False
    coordinateArea = ""


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
    _label_video_saved = Gtk.Template.Child()
    _quality_video_box = Gtk.Template.Child()
    _quality_video_switcher = Gtk.Template.Child()
    _popover_about_button = Gtk.Template.Child()
    _recording_box = Gtk.Template.Child()
    _video_folder_button = Gtk.Template.Child()
    _record_mouse_switcher = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Notify.init('com.github.amikha1lov.rec_app')
        self.notification = None
        self.settings = Gio.Settings.new('com.github.amikha1lov.rec_app')
        self.recordSoundOn =  self.settings.get_boolean('record-audio-switch')
        self.delayBeforeRecording = self.settings.get_int('delay')
        self.videoFrames = self.settings.get_int('frames')
        self.recordMouse = self.settings.get_boolean('record-mouse-cursor-switch')
        self._sound_on_switch.set_active(self.recordSoundOn)
        self._record_mouse_switcher.set_active(self.recordMouse)
        self._quality_video_switcher.set_active(self.settings.get_boolean("high-quality-switch"))
        self._delay_button.set_value(self.delayBeforeRecording)
        if self.videoFrames == 15:
            self._frames_combobox.set_active(0)
        elif self.videoFrames == 30:
            self._frames_combobox.set_active(1)
        else:
            self._frames_combobox.set_active(2)

        self.currentFolder = self.settings.get_string('path-to-save-video-folder')

        if self.currentFolder == "Default":
            self.settings.set_string('path-to-save-video-folder',GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS))
            self._video_folder_button.set_current_folder_uri(self.settings.get_string('path-to-save-video-folder'))
        else:
            self._video_folder_button.set_current_folder_uri(self.currentFolder)
        self.displayServer = "x11"

        if self.displayServer == "wayland":
            self._select_area_button.set_visible(False)
            self._quality_video_box.set_visible(False)
            self.bus = SessionBus()
            self.GNOMEScreencast = self.bus.get('org.gnome.Shell.Screencast', '/org/gnome/Shell/Screencast')
        else:
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={} ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"

    def openFolder(self, notification, action, user_data = None):
        videoFolderForOpen = self.settings.get_string('path-to-save-video-folder')
        os.system("xdg-open "+ videoFolderForOpen)


    def openVideoFile(self, notification, action, user_data = None):
        os.system("xdg-open "+ self.fileName+".mkv")

    @Gtk.Template.Callback()
    def on__video_folder_button_file_set(self, button):
        self.settings.set_string('path-to-save-video-folder',self._video_folder_button.get_filename())
        self._video_folder_button.set_current_folder_uri(self.settings.get_string('path-to-save-video-folder'))

    @Gtk.Template.Callback()
    def on__frames_combobox_changed(self, box):
        self.videoFrames = int(box.get_active_text())
        self.settings.set_int('frames',int(box.get_active_text()))


    @Gtk.Template.Callback()
    def on__record_mouse_switcher_state_set(self, switch, gparam):

        if switch.get_active():
            state = "on"
            self.recordMouse = True
            self.settings.set_boolean('record-mouse-cursor-switch',True )
        else:
            state = "off"
            self.recordMouse = False
            self.settings.set_boolean('record-mouse-cursor-switch',False)


    @Gtk.Template.Callback()
    def on__delay_button_change_value(self, spin):
        self.delayBeforeRecording = spin.get_value_as_int()
        self.settings.set_int('delay',spin.get_value_as_int())

    @Gtk.Template.Callback()
    def on__select_area_button_clicked(self, spin):
        coordinate = Popen("slop -n -c 0.3,0.4,0.6,0.4 -l -t 0 -f '%w %h %x %y'",shell=True,stdout=PIPE).communicate()
        listCoor = list(coordinate)
        listCoor = listCoor[0].decode().split()

        startx,starty,endx,endy=int(listCoor[2]),int(listCoor[3]),int(listCoor[2])+int(listCoor[0]),int(listCoor[1])+int(listCoor[3])
        self.coordinateArea = "startx={} starty={} endx={} endy={}".format(startx,starty,endx,endy)
        self.coordinateMode = True


    @Gtk.Template.Callback()
    def on__sound_on_switch_activate(self, switch, gparam):
        if switch.get_active():
            self.recordSoundOn = True
            with pulsectl.Pulse() as pulse:
                self.soundOnSource = pulse.sink_list()[0].name
                self.settings.set_boolean('record-audio-switch',True)

                self.soundOn = " pulsesrc provide-clock=false device='{}.monitor' buffer-time=20000000 ! 'audio/x-raw,depth=24,channels=2,rate=44100,format=F32LE,payload=96' ! queue ! audioconvert ! vorbisenc ! queue ! mux. -e".format(self.soundOnSource)

        else:
            self.recordSoundOn = False
            self.settings.set_boolean('record-audio-switch',False)


    @Gtk.Template.Callback()
    def on__quality_video_switcher_state_set(self, switch, gparam):
        if switch.get_active():
            state = "on"
            self.settings.set_boolean('high-quality-switch',True)
            self.quality_video = "vp8enc min_quantizer=10 max_quantizer=50 cq_level=13 cpu-used=5 deadline=1000000 threads=8"
        else:
            state = "off"
            self.settings.set_boolean('high-quality-switch',False)
            self.quality_video = "vp8enc min_quantizer=20 max_quantizer=20 cq_level=13 cpu-used=2 deadline=1000000 threads=2"



    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        self._recording_box.set_visible(False)
        self._label_video_saved_box.set_visible(True)
        fileNameTime =_("RecApp-") + time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        videoFolder = self.settings.get_string('path-to-save-video-folder')
        self._label_video_saved.set_label(videoFolder)
        self.fileName = os.path.join(videoFolder,fileNameTime)
        if self.delayBeforeRecording > 0:
            self.notification = Notify.Notification.new('rec_app', _("recording will start in ") + " " + str(self.delayBeforeRecording) + " "+ _(" seconds"))
            self.notification.show()

        time.sleep(self.delayBeforeRecording)

        if self.displayServer == "wayland":
            if self.recordSoundOn == True:


                RecorderPipeline = "vp8enc min_quantizer=10 max_quantizer=50 cq_level=13 cpu-used=5 deadline=1000000 threads=%T ! queue ! mux. pulsesrc buffer-time=20000000 device='{}.monitor' ! queue !  audioconvert ! vorbisenc ! queue ! mux. webmmux name=mux".format(self.soundOnSource)
                self.GNOMEScreencast.Screencast(self.fileName, {'framerate': GLib.Variant('i', int(self.videoFrames)),'draw-cursor': GLib.Variant('b',self.recordMouse), 'pipeline': GLib.Variant('s', RecorderPipeline)})
            else:
                RecorderPipeline = "vp8enc min_quantizer=10 max_quantizer=50 cq_level=13 cpu-used=5 deadline=1000000 threads=%T ! queue ! webmmux"
                self.GNOMEScreencast.Screencast(self.fileName, {'framerate': GLib.Variant('i', int(self.videoFrames)),'draw-cursor': GLib.Variant('b',self.recordMouse), 'pipeline': GLib.Variant('s', RecorderPipeline)})
        else:
            if self.coordinateMode == True:
                video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc show-pointer={} " +self.coordinateArea +" ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! matroskamux name=mux ! queue ! filesink location='{}'.mkv"
                if self.recordSoundOn == True:
                    self.video = Popen(video_str.format(self.recordMouse,self.videoFrames,self.quality_video,self.fileName) + self.soundOn, shell=True)

                else:
                    self.video = Popen(video_str.format(self.recordMouse,self.videoFrames,self.quality_video,self.fileName), shell=True)
            else:
                if self.recordSoundOn == True:
                    self.video = Popen(self.video_str.format(self.recordMouse,self.videoFrames,self.quality_video,self.fileName) + self.soundOn, shell=True)

                else:
                    self.video = Popen(self.video_str.format(self.recordMouse,self.videoFrames,self.quality_video,self.fileName), shell=True)

        self._record_button.set_visible(False)
        self._stop_record_button.set_visible(True)


    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        self._stop_record_button.set_visible(False)
        self._record_button.set_visible(True)
        self._label_video_saved_box.set_visible(False)
        self._recording_box.set_visible(True)

        if self.displayServer == "wayland":
            self.GNOMEScreencast.StopScreencast()

        else:
            self.video.send_signal(signal.SIGINT)

        self.notification = Notify.Notification.new('rec_app', _("Recording is complete"))
        self.notification.add_action("open_folder", _("Open Folder"),self.openFolder)
        self.notification.add_action("open_file", _("Open File"),self.openVideoFile)
        self.notification.show()





    @Gtk.Template.Callback()
    def on__popover_about_button_clicked(self, button):
        about = Gtk.AboutDialog()
        about.set_program_name(_("RecApp"))
        about.set_version("0.1.0")
        about.set_authors(["Alexey Mikhailov <mikha1lov@yahoo.com>", "Artem Polishchuk <ego.cordatus@gmail.com>", "@lateseal (Telegram)", "@gasinvein (Telegram)", "@dead_mozay (Telegram) <dead_mozay@opensuse.org>", "and contributors of Telegram chat https://t.me/gnome_rus"])
        about.set_artists(["Raxi Petrov <raxi2012@gmail.com>"])
        about.set_copyright("GPLv3+")
        about.set_comments(_("Simple app for recording desktop"))
        about.set_website("https://github.com/amikha1lov/rec_app")
        about.set_website_label(_("Website"))
        about.set_logo_icon_name("com.github.amikha1lov.rec_app")
        about.set_wrap_license(True)
        about.set_license_type(Gtk.License.GPL_3_0)
        about.run()
        about.destroy()

