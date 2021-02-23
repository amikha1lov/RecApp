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

import gi
import os
import sys
import datetime

from locale import gettext as _
from pydbus import SessionBus
from subprocess import PIPE, Popen

from .rec import cancel_delay, cancel_record, delay_button_change, delete_event, \
    formats_combobox_changed, frames_combobox_changed, mouse_switcher, on__sound_switch, \
    quality_video_switcher, quit_app, start_recording, stop_recording, toggle_audio, \
    toggle_high_quality, toggle_microphone, toggle_mouse_record, toggle_record, video_folder_button

from .recapp_constants import recapp_constants as constants

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Handy', '1')

from gi.repository import Gdk, Gio, GLib, Gst, Gtk, Handy  # noqa: E402

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
    _pause_continue_record_button_stack_revealer = Gtk.Template.Child()
    _pause_continue_record_button_stack = Gtk.Template.Child()
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs["application"]

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource('/com/github/amikha1lov/RecApp/style.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        GLib.timeout_add(1000, self.refresh_time)
        self.elapsed_time = datetime.timedelta()
        self._time_recording_label.set_label(str(self.elapsed_time).replace(":", "∶"))

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

        # Extend the functionality of our GtkButton
        self._video_folder_button = FileChooserButton(
            self._video_folder_button,
            parent=self,
            chooser_type="folder",
            selected_function=self.on__video_folder_button_file_set
        )

        self.currentFolder = self.settings.get_string('path-to-save-video-folder')

        if self.currentFolder == "Default":
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) is None:

                directory = "/RecAppVideo"
                parent_dir = os.path.expanduser("~")
                path = parent_dir + directory

                if not os.path.exists(path):
                    os.makedirs(path)
                self.settings.set_string('path-to-save-video-folder', path)
            else:
                self.settings.set_string('path-to-save-video-folder', GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_VIDEOS))
            self._video_folder_button.set_path(
                self.settings.get_string('path-to-save-video-folder'))
        else:
            self._video_folder_button.set_path(self.currentFolder)

        self.displayServer = os.environ['XDG_SESSION_TYPE'].lower()

        if self.displayServer == "wayland":
            self._capture_mode_box.set_visible(False)
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
        else:
            self.video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc use-damage=1 show-pointer={0} " \
                "! video/x-raw,framerate={1}/1 ! queue ! videoscale ! videoconvert ! {2} ! queue ! " \
                "{3} name=mux ! queue ! filesink location='{4}'{5}"

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

    def openFolder(self, action, parameter):
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

    def openVideoFile(self, action, parameter):
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
            self._time_recording_label.set_label(str(self.elapsed_time).replace(":", "∶"))
        return True

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
        self._pause_continue_record_button_stack.set_visible_child(self._continue_record_button)
        self._paused_start_stack.set_visible_child(self._paused_label)
        self.label_context.remove_class("recording")
        self.istimerrunning = False

    @Gtk.Template.Callback()
    def on__continue_record_button_clicked(self, widget):
        self._pause_continue_record_button_stack.set_visible_child(self._pause_record_button)
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

    @Gtk.Template.Callback()
    def on__back_button_clicked(self, widget):
        self._main_stack.set_visible_child(self._main_screen_box)
        self._record_stop_record_button_stack.set_visible_child(self._record_button)
        self._preferences_back_stack.set_visible_child(self._menu_button)
        self._record_stop_record_button_stack_revealer.set_reveal_child(True)
        self.set_size_request(462, 300)

    @Gtk.Template.Callback()
    def on__keyboardshortcuts_button_clicked(self, widget):
        window = Gtk.Builder.new_from_resource('/com/github/amikha1lov/RecApp/shortcuts.ui').get_object('shortcuts')
        window.set_transient_for(self)
        window.present()

    @Gtk.Template.Callback()
    def on__about_button_clicked(self, widget):
        dialog = AboutDialog(self)
        dialog.set_program_name(_(constants["APPNAME"]))
        dialog.set_logo_icon_name(constants["APPID"])
        dialog.set_version(constants["APPVERSION"])
        dialog.run()
        dialog.destroy()


@Gtk.Template(resource_path='/com/github/amikha1lov/RecApp/about.ui')
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = 'AboutDialog'

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self, transient_for=parent)

class FileChooserButton:
    # This class extends the functionality of a GtkButton to open a file
    # chooser and display the name of a selected folder or file

    def __init__(self, button, parent=None, chooser_type="file", selected_function=None):

        self.parent = parent
        self.button = button
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.path = ""

        box = Gtk.Box()
        box.set_spacing(6)
        self.icon = Gtk.Image.new()

        if chooser_type == "folder":
            self.icon.set_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.icon.set_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.BUTTON)

        self.label = Gtk.Label.new(_("(None)"))

        box.add(self.icon)
        box.add(self.label)

        self.button.add(box)
        self.button.show_all()

        self.button.connect("clicked", self.open_file_chooser)

    def choose_dir(self, parent=None, initialdir="~", title=_("Select a Folder"), multichoice=True):
        try:
            dialog = Gtk.FileChooserNative.new(
                title,
                parent,
                Gtk.FileChooserAction.SELECT_FOLDER,
                _("_Open"),
                _("_Cancel")
            )
        except AttributeError:
            dialog = Gtk.FileChooserDialog(
                title,
                parent,
                Gtk.FileChooserAction.SELECT_FOLDER
            )
            dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

        if multichoice:
            dialog.set_select_multiple(True)

        folder = os.path.expanduser(initialdir)

        if os.path.exists(folder):
            dialog.set_current_folder(folder)
        else:
            dialog.set_current_folder(os.path.expanduser("~"))

        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            res = dialog.get_filenames()
        else:
            res = None

        dialog.destroy()

        return res

    def choose_file(self, parent=None, initialdir="~", title=_("Select a File"), multiple=False):
        try:
            dialog = Gtk.FileChooserNative.new(
                title,
                parent,
                Gtk.FileChooserAction.OPEN,
                _("_Open"),
                _("_Cancel")
            )
        except AttributeError:
            dialog = Gtk.FileChooserDialog(
                title,
                parent,
                Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

        dialog.set_select_multiple(multiple)
        folder = os.path.expanduser(initialdir)

        if os.path.exists(folder):
            dialog.set_current_folder(folder)
        else:
            dialog.set_current_folder(os.path.expanduser("~"))

        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            res = dialog.get_filenames()
        else:
            res = None

        dialog.destroy()

        return res

    def open_file_chooser(self, widget):

        if self.chooser_type == "folder":
            selected = self.choose_dir(self.parent, self.path, multichoice=False)

        else:
            if self.path:
                folder_path = os.path.dirname(self.path)
            else:
                folder_path = ""

            selected = self.choose_file(self.parent, folder_path)

        if selected:
            self.set_path(selected[0])

            try:
                self.selected_function(self)

            except TypeError as e:
                # No function defined
                return

    def get_path(self):
        return self.path

    def set_path(self, path):

        if not path:
            return

        self.path = path
        self.label.set_label(os.path.basename(path))

    def clear(self):
        self.path = ""
        self.label.set_label(_("(None)"))
