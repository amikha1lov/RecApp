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
import multiprocessing
from locale import gettext as _
import locale
from .recapp_constants import recapp_constants as constants

from pydbus import SessionBus
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Notify', '0.7')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk,Gst,GLib,Gio,Notify,GstPbutils, Gdk
Gtk.init(sys.argv)
# initialize GStreamer
Gst.init(sys.argv)




@Gtk.Template(resource_path='/com/github/amikha1lov/RecApp/window.ui')
class RecappWindow(Gtk.ApplicationWindow):

    soundOn = ""
    coordinateMode = False
    coordinateArea = ""
    isrecording = False
    fileFormat = ".webm"
    __gtype_name__ = 'RecAppWindow'


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
        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('q'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_quit_app)
        accel.connect(Gdk.keyval_from_name('h'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_high_quality)
        accel.connect(Gdk.keyval_from_name('a'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_audio)
        accel.connect(Gdk.keyval_from_name('m'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_mouse_record)
        accel.connect(Gdk.keyval_from_name('r'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_record)
        self.cpus = multiprocessing.cpu_count() - 1
        self.quality_video = "vp8enc min_quantizer=25 max_quantizer=25 cpu-used={0} cq_level=13 deadline=1 threads={0}".format(self.cpus)
        self.add_accel_group(accel)
        self.connect("delete-event", self.on_delete_event)
        Notify.init(constants["APPID"])
        self.notification = None
        self.settings = Gio.Settings.new(constants["APPID"])
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
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) == None:

                directory = "/RecAppVideo"
                parent_dir = Popen("xdg-user-dir",shell=True,stdout=PIPE).communicate()
                parent_dir = list(parent_dir)
                parent_dir = parent_dir[0].decode().split()[0]
                path = parent_dir + directory

                if not os.path.exists(path):
                    os.makedirs(path)
                self.settings.set_string('path-to-save-video-folder',path)
            else:
                 self.settings.set_string('path-to-save-video-folder',GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS))
            self._video_folder_button.set_current_folder_uri(self.settings.get_string('path-to-save-video-folder'))
        else:
            self._video_folder_button.set_current_folder_uri(self.currentFolder)


        self.displayServer = os.environ['XDG_SESSION_TYPE'].lower()


        if self.displayServer == "wayland":
            self._select_area_button.set_visible(False)
            self._quality_video_box.set_visible(False)
            self._sound_box.set_visible(False)
            self._sound_on_switch.set_active(False)
            self._quality_video_switcher.set_active(False)
            self.bus = SessionBus()
            if os.environ['XDG_CURRENT_DESKTOP'] != 'GNOME':
                self._record_button.set_sensitive(False)
                self.notification = Notify.Notification.new(constants["APPNAME"], _("Sorry, Wayland session is unsupported right now (WIP)"))
                self.notification.show()
            else:
                self.GNOMEScreencast = self.bus.get('org.gnome.Shell.Screencast', '/org/gnome/Shell/Screencast')
        else:
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={} ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! webmmux name=mux ! queue ! filesink location='{}'.webm"


    def openFolder(self, notification, action, user_data = None):
        videoFolderForOpen = self.settings.get_string('path-to-save-video-folder')
        os.system("xdg-open "+ videoFolderForOpen)


    def openVideoFile(self, notification, action, user_data = None):
        os.system("xdg-open "+ self.fileName+".webm")

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
        listCoor = [int(i) for i in coordinate[0].decode().split()]
        if not listCoor[0] or not listCoor[1]:
            self.notification = Notify.Notification.new(constants["APPNAME"], _("Please re-select the area"))
            self.notification.show()
            return
        startx,starty,endx,endy = listCoor[2],listCoor[3],listCoor[2]+listCoor[0]-1, listCoor[1]+listCoor[3]-1
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
            self.quality_video = "vp8enc min_quantizer=5 max_quantizer=10 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(self.cpus)
        else:
            state = "off"
            self.settings.set_boolean('high-quality-switch',False)
            self.quality_video = "vp8enc min_quantizer=25 max_quantizer=25 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(self.cpus)



    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        self.start_recording()


    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        self.stop_recording()




    @Gtk.Template.Callback()
    def on__popover_about_button_clicked(self, button):
        about = Gtk.AboutDialog()
        about.set_program_name(_(constants["APPNAME"]))
        about.set_version("0.1.0")
        about.set_authors(["Alexey Mikhailov <mikha1lov@yahoo.com>", "Artem Polishchuk <ego.cordatus@gmail.com>", "@lateseal (Telegram)", "@gasinvein (Telegram)", "@dead_mozay (Telegram) <dead_mozay@opensuse.org>", "and contributors of Telegram chat https://t.me/gnome_rus"])
        about.set_artists(["Raxi Petrov <raxi2012@gmail.com>"])
        about.set_copyright("GPLv3+")
        about.set_comments(_("Simple app for recording desktop"))
        about.set_website("https://github.com/amikha1lov/RecApp")
        about.set_website_label(_("Website"))
        about.set_logo_icon_name(constants["APPID"])
        about.set_wrap_license(True)
        about.set_license_type(Gtk.License.GPL_3_0)
        about.run()
        about.destroy()



    def on_delete_event(self,w,h):
        if self.isrecording:
            self.stop_recording()



    def on_toggle_audio(self,*args):
        if not self.isrecording:
            if self._sound_on_switch.get_active():
                self._sound_on_switch.set_active(False)
            else:
                if self.displayServer == "wayland":
                    self._sound_on_switch.set_active(False)
                else:
                    self._sound_on_switch.set_active(True)


    def on_toggle_high_quality(self,*args):
        if not self.isrecording:
            if self._quality_video_switcher.get_active():
                self._quality_video_switcher.set_active(False)
            else:
                self._quality_video_switcher.set_active(True)




    def start_recording(self,*args):
        self._recording_box.set_visible(False)
        self._label_video_saved_box.set_visible(True)
        fileNameTime =_("RecApp-") + time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        videoFolder = self.settings.get_string('path-to-save-video-folder')
        self._label_video_saved.set_label(videoFolder)
        self.fileName = os.path.join(videoFolder,fileNameTime)
        if self.delayBeforeRecording > 0:
            self.notification = Notify.Notification.new(constants["APPNAME"], _("recording will start in ") + " " + str(self.delayBeforeRecording) + " "+ _(" seconds"))
            self.notification.show()

        time.sleep(self.delayBeforeRecording)

        if self.displayServer == "wayland":
                RecorderPipeline = "vp8enc min_quantizer=25 max_quantizer=25 cpu-used={0} cq_level=13 deadline=1000000 threads={0} ! queue ! webmmux".format(self.cpus)
                self.GNOMEScreencast.Screencast(self.fileName  + ".webm", {'framerate': GLib.Variant('i', int(self.videoFrames)),'draw-cursor': GLib.Variant('b',self.recordMouse), 'pipeline': GLib.Variant('s', RecorderPipeline)})
        else:
            if self.coordinateMode == True:
                video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc show-pointer={} " +self.coordinateArea +" ! video/x-raw,framerate={}/1 ! queue ! videoscale ! videoconvert ! {} ! queue ! webmmux name=mux ! queue ! filesink location='{}'.webm"
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
        self.isrecording = True


    def stop_recording(self,*args):
        self._stop_record_button.set_visible(False)
        self._record_button.set_visible(True)
        self._label_video_saved_box.set_visible(False)
        self._recording_box.set_visible(True)

        if self.displayServer == "wayland":
            self.GNOMEScreencast.StopScreencast()

        else:
            self.video.send_signal(signal.SIGINT)

        self.notification = Notify.Notification.new(constants["APPNAME"], _("Recording is complete"))
        self.notification.add_action("open_folder", _("Open Folder"),self.openFolder)
        self.notification.add_action("open_file", _("Open File"),self.openVideoFile)
        self.notification.show()
        self.isrecording = False



    def on_toggle_record(self,*args):
        if self.isrecording:
            self.stop_recording()
        else:
            self.start_recording()

    def on_quit_app(self,*args):
        if self.isrecording:
            self.stop_recording()

        self.destroy()



    def on_toggle_mouse_record(self,*args):
        if not self.isrecording:
            if self._record_mouse_switcher.get_active():
                self._record_mouse_switcher.set_active(False)
            else:
                self._record_mouse_switcher.set_active(True)

