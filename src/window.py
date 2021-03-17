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

import os
import datetime
from locale import gettext as _

import gi

from .rec import mouse_switcher, start_recording, on__sound_switch, stop_recording, delete_event
from .recapp_constants import recapp_constants as constants
from .preferences import PreferencesWindow
from .about import AboutWindow
from .shortcuts import RecAppShortcuts

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gdk, Gio, GLib, Gst, GstPbutils, Gtk, Handy


# TODO Not working yet: record computer sounds (keyboard shortcut already working)

@Gtk.Template(resource_path=constants['RESOURCEID'] + '/window.ui')
class RecappWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'RecAppWindow'

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
    _delay_button = Gtk.Template.Child()
    _sound_on_computer = Gtk.Template.Child()
    _record_mouse_switcher = Gtk.Template.Child()
    _fullscreen_mode_button = Gtk.Template.Child()
    _window_mode_button = Gtk.Template.Child()
    _selection_mode_button = Gtk.Template.Child()
    _pause_record_button = Gtk.Template.Child()
    _continue_record_button = Gtk.Template.Child()
    _sound_rowbox = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()
    _paused_start_stack = Gtk.Template.Child()
    _menu_stack = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _time_recording_label = Gtk.Template.Child()
    _recording_label = Gtk.Template.Child()
    _paused_label = Gtk.Template.Child()
    _sound_on_microphone = Gtk.Template.Child()
    main_popover = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs["application"]
        self._menu_button.set_popover(self.main_popover)

        # Initialize recording timer
        GLib.timeout_add(1000, self.refresh_time)
        self.elapsed_time = datetime.timedelta()
        self._time_recording_label.set_label(str(self.elapsed_time).replace(":", "∶"))

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('q'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_quit_app)
        self.add_accel_group(accel)

        self.cpus = os.cpu_count() - 1
        self.connect("delete-event", self.on_delete_event)

        self.settings = Gio.Settings.new(constants["APPID"])
        self.delayBeforeRecording = self.settings.get_int('delay')
        self.recordMouse = self.settings.get_boolean('record-mouse-cursor-switch')
        self._sound_on_computer.set_active(self.settings.get_boolean('sound-on-computer'))
        self._sound_on_microphone.set_active(self.settings.get_boolean('sound-on-microphone'))
        self._record_mouse_switcher.set_active(self.recordMouse)
        self._delay_button.set_value(self.delayBeforeRecording)

        # Notification actions
        action = Gio.SimpleAction.new("open-folder", None)
        action.connect("activate", self.openFolder)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("open-file", None)
        action.connect("activate", self.openVideoFile)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("selectlocation", None)
        action.connect("activate", self.open_selectlocation)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("shortcuts", None)
        action.connect("activate", self.open_shortcuts_window)
        self.application.add_action(action)

        self.currentFolder = self.settings.get_string('path-to-save-video-folder')

        if self.currentFolder == "Default":
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) is None:

                directory = "/RecAppVideo"
                parent_dir = GLib.get_home_dir()
                path = parent_dir + directory

                if not os.path.exists(path):
                    os.makedirs(path)
                self.settings.set_string('path-to-save-video-folder', path)
            else:
                self.settings.set_string('path-to-save-video-folder', GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_VIDEOS))

        self.displayServer = GLib.getenv('XDG_SESSION_TYPE').lower()

        if self.displayServer == "wayland":
            # self._sound_rowbox.set_visible(False)
            # self._sound_on_computer.set_active(False)
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if GLib.getenv('XDG_CURRENT_DESKTOP') != 'GNOME':
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
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={0} ! video/x-raw," \
                             "framerate={1}/1 ! queue ! videoscale ! videoconvert ! {2} ! queue ! {3} name=mux ! " \
                             "queue ! filesink location='{4}'{5} "

        for encoder in self.encoders:
            plugin = Gst.ElementFactory.find(encoder)
            if plugin:
                if encoder == "vp8enc":
                    self.formats.append("webm")
                    self.formats.append("mkv")
                elif encoder == "x264enc":
                    self.formats.append("mp4")
            else:
                pass

    def playsound(self, sound):
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

    def open_selectlocation(self, action, widget):
        dialog = Gtk.Builder.new_from_resource(constants['RESOURCEID'] + '/selectlocation.ui').get_object(
            'selectlocation')
        dialog.set_transient_for(self)
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            directory = dialog.get_filenames()
        else:
            directory = None
        dialog.destroy()

        try:
            if not os.access(directory[0], os.W_OK) or not directory[0][:5] == '/home':  # not ideal solution
                error = Gtk.MessageDialog(
                    transient_for=self,
                    type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Inaccessible location")
                )
                error.format_secondary_text(
                    _("Please choose another location and retry.")
                )
                error.run()
                error.destroy()
            else:
                self.settings.set_string("path-to-save-video-folder", directory[0])
        except:
            return

    @Gtk.Template.Callback()
    def on_about_button_clicked(self, widget):
        about = AboutWindow(self)
        about.set_program_name(_(constants["APPNAME"]))
        about.set_logo_icon_name(constants["APPID"])
        about.set_version(constants["APPVERSION"])
        about.set_transient_for(self)
        about.run()
        about.destroy()

    @Gtk.Template.Callback()
    def on_shortcuts_button_clicked(self, button):
        shortcuts = RecAppShortcuts(self)
        shortcuts.set_transient_for(self)
        shortcuts.present()

    def on_delete_event(self, w, h):
        delete_event(self, w, h)

    def on_quit_app(self, *args):
        quit_app(self, *args)  # TODO fix this

    def refresh_time(self):
        if self.istimerrunning:
            self.elapsed_time += datetime.timedelta(seconds=1)
            self._time_recording_label.set_label(str(self.elapsed_time).replace(":", "∶"))
        return True

    @Gtk.Template.Callback()
    def on__record_mouse_switcher_state_set(self, switch, gparam):
        mouse_switcher(self, switch, gparam)

    @Gtk.Template.Callback()
    def on__delay_button_change_value(self, spin):
        self.delayBeforeRecording = spin.get_value_as_int()
        self.settings.set_int('delay', spin.props.value)

    @Gtk.Template.Callback()
    def on__sound_on_computer_state_set(self, switcher, state):
        self.settings.set_boolean('sound-on-computer', state)

    @Gtk.Template.Callback()
    def on__sound_on_microphone_state_set(self, switcher, state):
        self.settings.set_boolean('sound-on-microphone', state)

    @Gtk.Template.Callback()
    def on__record_button_clicked(self, widget):
        start_recording(self)

    @Gtk.Template.Callback()
    def on__stop_record_button_clicked(self, widget):
        stop_recording(self)

    @Gtk.Template.Callback()
    def onQuit(self, window):
        print('onQuit')  # TODO this called by click exit button

    @Gtk.Template.Callback()
    def on_preferences_button_clicked(self, button):
        preferences = PreferencesWindow(self)
        preferences.show()

    # TODO
    # Connect pause and continue to something

    @Gtk.Template.Callback()
    def on__pause_record_button_clicked(self, widget):
        self._menu_stack.set_visible_child(self._continue_record_button)
        self._paused_start_stack.set_visible_child(self._paused_label)
        self.label_context.remove_class("recording")
        self.istimerrunning = False

    @Gtk.Template.Callback()
    def on__continue_record_button_clicked(self, widget):
        self._menu_stack.set_visible_child(self._pause_record_button)
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
