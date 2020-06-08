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
from .rec import *

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
    mux = ""
    extension = ""
    quality_video = ""
    coordinateArea = ""
    recordFormat = ""
    widthArea = 0
    heightArea = 0
    coordinateMode = False
    isrecording = False
    __gtype_name__ = 'RecAppWindow'
    encoders = ["vp8enc","x264enc"]
    formats = []
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
    _quality_rowbox = Gtk.Template.Child()
    _audio_rowbox = Gtk.Template.Child()
    _formats_combobox = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('q'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_quit_app)
        accel.connect(Gdk.keyval_from_name('h'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_high_quality)
        accel.connect(Gdk.keyval_from_name('a'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_audio)
        accel.connect(Gdk.keyval_from_name('m'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_mouse_record)
        accel.connect(Gdk.keyval_from_name('r'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_toggle_record)
        self.cpus = multiprocessing.cpu_count() - 1
        self.add_accel_group(accel)
        self.connect("delete-event", self.on_delete_event)
        Notify.init(constants["APPID"])
        self.notification = None
        self.settings = Gio.Settings.new(constants["APPID"])
        self.recordSoundOn =  self.settings.get_boolean('record-audio-switch')
        self.delayBeforeRecording = self.settings.get_int('delay')
        self.videoFrames = self.settings.get_int('frames')
        self.recordMouse = self.settings.get_boolean('record-mouse-cursor-switch')
        self.recordFormat = self.settings.get_string('format-video')
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
            self._sound_box.set_visible(False)
            self._sound_on_switch.set_active(False)
            self._audio_rowbox.set_visible(False)
            self.bus = SessionBus()
            if os.environ['XDG_CURRENT_DESKTOP'] != 'GNOME':
                self._record_button.set_sensitive(False)
                self.notification = Notify.Notification.new(constants["APPNAME"], _("Sorry, Wayland session is not supported yet"))
                self.notification.show()
            else:
                self.GNOMEScreencast = self.bus.get('org.gnome.Shell.Screencast', '/org/gnome/Shell/Screencast')
        else:
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={0} ! video/x-raw,framerate={1}/1 ! queue ! videoscale ! videoconvert ! {2} ! queue ! {3} name=mux ! queue ! filesink location='{4}'{5}"

        for encoder in self.encoders:
           plugin = Gst.ElementFactory.find(encoder)
           if plugin:
               if(encoder == "vp8enc"):
                   self.formats.append("webm")
                   self.formats.append("mkv")
               elif(encoder == "x264enc"):
                   self.formats.append("mp4")
           else:
               pass
        formats_store = Gtk.ListStore(str)
        for format in self.formats:
            formats_store.append([format])
        self._formats_combobox.set_model(formats_store)
        self._formats_combobox.set_active(self.formats.index(self.settings.get_string('format-video')))
        self.recordFormat = self._formats_combobox.get_active_text()



    def openFolder(self, notification, action, user_data = None):
        videoFolderForOpen = self.settings.get_string('path-to-save-video-folder')
        os.system("xdg-open "+ videoFolderForOpen)

    def openVideoFile(self, notification, action, user_data = None):

        os.system("xdg-open "+ self.fileName+self.extension)

    @Gtk.Template.Callback()
    def on__video_folder_button_file_set(self, button):
        video_folder_button(self, button)

    @Gtk.Template.Callback()
    def on__frames_combobox_changed(self, box):
        frames_combobox_changed(self, box)

    @Gtk.Template.Callback()
    def on__record_mouse_switcher_state_set(self, switch, gparam):
        mouse_switcher(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__delay_button_change_value(self, spin):
        delay_button_change(self, spin)

    @Gtk.Template.Callback()
    def on__select_area_button_clicked(self, spin):
        on__select_area(self)

    @Gtk.Template.Callback()
    def on__sound_on_switch_activate(self, switch, gparam):
        on__sound_switch(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__quality_video_switcher_state_set(self, switch, gparam):
        quality_video_switcher(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__record_button_clicked(self, button):
        start_recording(self)

    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, button):
        stop_recording(self)

    @Gtk.Template.Callback()
    def on__popover_about_button_clicked(self, button):
        popover_init()

    @Gtk.Template.Callback()
    def on__formats_combobox_changed(self,box):
        formats_combobox_changed(self,box)

    def on_delete_event(self,w,h):
        delete_event(self,w,h)

    def on_toggle_audio(self,*args):
        toggle_audio(self,*args)

    def on_toggle_high_quality(self,*args):
        toggle_high_quality(self,*args)

    def on_toggle_record(self,*args):
        toggle_record(self,*args)

    def on_quit_app(self,*args):
        quit_app(self,*args)

    def on_toggle_mouse_record(self,*args):
        toggle_mouse_record(self,*args)



    
