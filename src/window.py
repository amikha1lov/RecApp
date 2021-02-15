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

import locale
import os
import signal
import sys
import datetime
from locale import gettext as _

import gi

from .rec import *
from .recapp_constants import recapp_constants as constants

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
gi.require_version('Handy', '1')
from gi.repository import Gdk, Gio, GLib, Gst, GstPbutils, Gtk, Handy

Gtk.init(sys.argv)
# initialize GStreamer
Gst.init(sys.argv)

# TODO Not working yet: record computer sounds (keyboard shortcut already working)

@Gtk.Template(resource_path='/com/github/amikha1lov/RecApp/window.ui')
class RecappWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'RecAppWindow'

    Handy.init()

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
    iscancelled = False
    istimerrunning = False
    isrecordingwithdelay = False
    isFullscreenMode = True
    encoders = ["vp8enc", "x264enc"]
    formats = []
    _record_button = Gtk.Template.Child()
    _stop_record_button = Gtk.Template.Child()
    _frames_combobox = Gtk.Template.Child()
    _delay_button = Gtk.Template.Child()
    _sound_on_switch = Gtk.Template.Child()
    _quality_video_switcher = Gtk.Template.Child()
    _video_folder_button = Gtk.Template.Child()
    _record_mouse_switcher = Gtk.Template.Child()
    _formats_combobox = Gtk.Template.Child()
    _record_stop_record_button_stack = Gtk.Template.Child()
    _fullscreen_mode_button = Gtk.Template.Child()
    _window_mode_button = Gtk.Template.Child()
    _selection_mode_button = Gtk.Template.Child()
    _showpointer_rowbox = Gtk.Template.Child()
    _pause_record_button = Gtk.Template.Child()
    _continue_record_button = Gtk.Template.Child()
    _main_stack = Gtk.Template.Child()
    _main_screen_box = Gtk.Template.Child()
    _capture_mode_box = Gtk.Template.Child()
    _sound_rowbox = Gtk.Template.Child()
    _preferences_box = Gtk.Template.Child()
    _preferences_button = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()
    _about_button = Gtk.Template.Child()
    _paused_start_stack_box = Gtk.Template.Child()
    _paused_start_stack = Gtk.Template.Child()
    _preferences_back_stack_revealer = Gtk.Template.Child()
    _back_button = Gtk.Template.Child()
    _preferences_back_stack = Gtk.Template.Child()
    _record_stop_record_button_stack_revealer = Gtk.Template.Child()
    _delay_box = Gtk.Template.Child()
    _delay_label = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _time_recording_label = Gtk.Template.Child()
    _recording_label = Gtk.Template.Child()
    _paused_label = Gtk.Template.Child()
    _sound_on_microphone = Gtk.Template.Child()
    _title_stack = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _preferences_label = Gtk.Template.Child()
    _blank_label = Gtk.Template.Child()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs["application"]

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource('/com/github/amikha1lov/RecApp/style.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Initialize popover
        builder = Gtk.Builder()
        builder.add_from_resource('/com/github/amikha1lov/RecApp/primary-menu.ui')
        primaryMenuModel = builder.get_object('primary-menu')
        self.popover = Gtk.Popover.new_from_model(self._menu_button, primaryMenuModel)
        self._menu_button.set_popover(self.popover)

        # Initialize recording timer
        GLib.timeout_add(1000, self.refresh_time)
        self.elapsed_time = datetime.timedelta()
        self._time_recording_label.set_label(str(self.elapsed_time).replace(":","∶"))

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('q'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_quit_app)
        accel.connect(Gdk.keyval_from_name('h'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_toggle_high_quality)
        accel.connect(Gdk.keyval_from_name('a'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_toggle_audio)
        accel.connect(Gdk.keyval_from_name('p'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_toggle_mouse_record)
        accel.connect(Gdk.keyval_from_name('r'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_toggle_record)
        accel.connect(Gdk.keyval_from_name('m'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_toggle_microphone)
        accel.connect(Gdk.keyval_from_name('c'), Gdk.ModifierType.CONTROL_MASK, 0,
                      self.on_cancel_record)
        self.cpus = os.cpu_count() - 1
        self.add_accel_group(accel)
        self.connect("delete-event", self.on_delete_event)
        self.settings = Gio.Settings.new(constants["APPID"])
        self.recordSoundOn = self.settings.get_boolean('record-audio-switch')
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

        # Notification actions
        action = Gio.SimpleAction.new("open-folder", None)
        action.connect("activate", self.openFolder)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("open-file", None)
        action.connect("activate", self.openVideoFile)
        self.application.add_action(action)

        # Popover actions
        action = Gio.SimpleAction.new("shortcuts", None)
        action.connect("activate", self.open_shortcuts_window)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.open_about_dialog)
        self.application.add_action(action)

        self.currentFolder = self.settings.get_string('path-to-save-video-folder')

        if self.currentFolder == "Default":
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) == None:

                directory = "/RecAppVideo"
                parent_dir = os.path.expanduser("~")
                path = parent_dir + directory

                if not os.path.exists(path):
                    os.makedirs(path)
                self.settings.set_string('path-to-save-video-folder', path)
            else:
                self.settings.set_string('path-to-save-video-folder', GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_VIDEOS))
            self._video_folder_button.set_current_folder_uri(
                self.settings.get_string('path-to-save-video-folder'))
        else:
            self._video_folder_button.set_current_folder_uri(self.currentFolder)

        self.displayServer = os.environ['XDG_SESSION_TYPE'].lower()

        if self.displayServer == "wayland":
            self._sound_rowbox.set_visible(False)
            self._sound_on_switch.set_active(False)
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if os.environ['XDG_CURRENT_DESKTOP'] != 'GNOME':
                self._record_button.set_sensitive(False)
                notification = Gio.Notification.new(constants["APPNAME"])
                notification.set_body(_("Sorry, Wayland session is not supported yet."))

                self.application.send_notification(None, notification)
            else:
                self.GNOMEScreencast = Gio.DBusProxy.new_sync(
                    self.bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    "org.gnome.Shell.Screencast",
                    "/org/gnome/Shell/Screencast",
                    "org.gnome.Shell.Screencast",
                    None)
                self.GNOMESelectArea = Gio.DBusProxy.new_sync(
                    self.bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    "org.gnome.Shell.Screenshot",
                    "/org/gnome/Shell/Screenshot",
                    "org.gnome.Shell.Screenshot",
                    None)
        else:
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={0} ! video/x-raw,framerate={1}/1 ! queue ! videoscale ! videoconvert ! {2} ! queue ! {3} name=mux ! queue ! filesink location='{4}'{5}"

        for encoder in self.encoders:
            plugin = Gst.ElementFactory.find(encoder)
            if plugin:
                if (encoder == "vp8enc"):
                    self.formats.append("webm")
                    self.formats.append("mkv")
                elif (encoder == "x264enc"):
                    self.formats.append("mp4")
            else:
                pass
        formats_store = Gtk.ListStore(str)
        for format in self.formats:
            formats_store.append([format])
        self._formats_combobox.set_model(formats_store)
        self._formats_combobox.set_active(
            self.formats.index(self.settings.get_string('format-video')))
        self.recordFormat = self._formats_combobox.get_active_text()

    def playsound(self, sound):
        '''
        Copyright (c) 2016 Taylor Marks <taylor@marksfam.com>
        The MIT License
        '''
        playbin = Gst.ElementFactory.make('playbin', 'playbin')
        playbin.props.uri = 'resource://' + sound

        set_result = playbin.set_state(Gst.State.PLAYING)

        bus = playbin.get_bus()
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
        playbin.set_state(Gst.State.NULL)

    def openFolder(self, notification, action, user_data=None):
        try:
            videoFolderForOpen = self.settings.get_string('path-to-save-video-folder')
            Gio.AppInfo.launch_default_for_uri("file:///" + videoFolderForOpen.lstrip("/"))

        except Exception as error:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Unable to open folder")
            )
            dialog.format_secondary_text(str(error))
            dialog.run()
            dialog.destroy()

    def openVideoFile(self, notification, action, user_data=None):
        try:
            Gio.AppInfo.launch_default_for_uri(
                "file:///" + self.fileName.lstrip("/") + self.extension
            )

        except Exception as error:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Unable to open file")
            )
            dialog.format_secondary_text(str(error))
            dialog.run()
            dialog.destroy()

    def on_delete_event(self, w, h):
        delete_event(self, w, h)

    def on_toggle_audio(self, *args):
        toggle_audio(self, *args)

    def on_toggle_high_quality(self, *args):
        toggle_high_quality(self, *args)

    def on_toggle_record(self, *args):
        toggle_record(self, *args)

    def on_quit_app(self, *args):
        quit_app(self, *args)

    def on_toggle_mouse_record(self, *args):
        toggle_mouse_record(self, *args)

    def on_toggle_microphone(self, *args):
        toggle_microphone(self, *args)

    def on_cancel_record(self, *args):
        cancel_record(self, *args)

    def refresh_time(self):
        if self.istimerrunning:
            self.elapsed_time += datetime.timedelta(seconds=1)
            self._time_recording_label.set_label(str(self.elapsed_time).replace(":","∶"))
        return True

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
    def on__sound_on_switch_activate(self, switch, gparam):
        on__sound_switch(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__quality_video_switcher_state_set(self, switch, gparam):
        quality_video_switcher(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__formats_combobox_changed(self, box):
        formats_combobox_changed(self, box)

    @Gtk.Template.Callback()
    def on__record_button_clicked(self, widget):
        start_recording(self)

    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, widget):
        stop_recording(self)
# TODO
# Connect pause and continue to something

    @Gtk.Template.Callback()
    def on__pause_record_button_clicked(self, widget):
        self._preferences_back_stack.set_visible_child(self._continue_record_button)
        self._paused_start_stack.set_visible_child(self._paused_label)
        self.label_context.remove_class("recording")
        self.istimerrunning = False

    @Gtk.Template.Callback()
    def on__continue_record_button_clicked(self, widget):
        self._preferences_back_stack.set_visible_child(self._pause_record_button)
        self._paused_start_stack.set_visible_child(self._recording_label)
        self.label_context.add_class("recording")
        self.istimerrunning = True

    @Gtk.Template.Callback()
    def on__cancel_button_clicked(self, widget):
        cancel_delay(self)

# TODO
# Connect window mode to something

    @Gtk.Template.Callback()
    def on__fullscreen_mode_pressed(self, widget):
        if self._fullscreen_mode_button.get_active():
            self.isFullscreenMode = True
            self.isWindowMode = False
            self.isSelectionMode = False

    @Gtk.Template.Callback()
    def on__window_mode_pressed(self, widget):
        if self._window_mode_button.get_active():
            self.isWindowMode = True
            self.isFullscreenMode = False
            self.isSelectionMode = False

    @Gtk.Template.Callback()
    def on__selection_mode_pressed(self, widget):
        if self._selection_mode_button.get_active():
            self.isSelectionMode = True
            self.isFullscreenMode = False
            self.isWindowMode = False

    @Gtk.Template.Callback()
    def on__preferences_button_clicked(self, widget):
        self._main_stack.set_visible_child(self._preferences_box)
        self._preferences_back_stack.set_visible_child(self._back_button)
        self._record_stop_record_button_stack_revealer.set_reveal_child(False)
        self._title_stack.set_visible_child(self._preferences_label)

    @Gtk.Template.Callback()
    def on__back_button_clicked(self, widget):
        self._main_stack.set_visible_child(self._main_screen_box)
        self._record_stop_record_button_stack.set_visible_child(self._record_button)
        self._preferences_back_stack.set_visible_child(self._menu_button)
        self._record_stop_record_button_stack_revealer.set_reveal_child(True)
        self._title_stack.set_visible_child(self._title_label)
        self.set_size_request(462, 300)

    def open_shortcuts_window(self, action, widget):
        window = Gtk.Builder.new_from_resource('/com/github/amikha1lov/RecApp/shortcuts.ui').get_object('shortcuts')
        window.set_transient_for(self)
        window.present()

    def open_about_dialog(self, action, widget):
        dialog = Gtk.Builder.new_from_resource('/com/github/amikha1lov/RecApp/about.ui').get_object('about')
        dialog.set_program_name(_(constants["APPNAME"]))
        dialog.set_logo_icon_name(constants["APPID"])
        dialog.set_version(constants["APPVERSION"])
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
