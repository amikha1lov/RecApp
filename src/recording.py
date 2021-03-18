# recording.py
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

from locale import gettext as _
import signal
import os
import datetime
import gi
from .recapp_constants import recapp_constants as constants
from subprocess import PIPE, Popen

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gst, GstPbutils


class Recording:
    is_recording = False
    coordinateMode = False
    isrecordingwithdelay = False

    def __init__(self, window):
        self.win = window

    def start_recording(self, *args):
        if self.win.isFullscreenMode:
            self.coordinateMode = False
            self.record(self)
        elif self.win.isWindowMode:
            print('window mode')
        else:
            if self.win.displayServer == "wayland":
                self.on__select_area_wayland()  # was self
            else:
                self.on__select_area()  # was self
            self.record(self)

    def record(self, *args):
        if self.win.delayBeforeRecording > 0:
            self.win._main_stack.set_visible_child(self.win._delay_box)
            self.win._record_stop_record_button_stack.set_visible_child(self.win._cancel_button)
            self.win._menu_stack_revealer.set_reveal_child(False)
            self.isrecordingwithdelay = True
            self.delay(self, *args)
        else:
            self.record_logic(self, *args)

    def on__select_area_wayland(self):
        self.waylandcoordinates = self.win.GNOMESelectArea.call_sync("SelectArea", None, Gio.DBusProxyFlags.NONE, -1, None)
        self.coordinateMode = True

    def on__select_area(self):
        coordinate = Popen("slop -n -c 0.3,0.4,0.6,0.4 -l -t 0 -f '%w %h %x %y'", shell=True,
                           stdout=PIPE).communicate()
        listCoor = [int(i) for i in coordinate[0].decode().split()]
        if not listCoor[0] or not listCoor[1]:
            notification = Gio.Notification.new(constants["APPNAME"])
            notification.set_body(_("Please re-select the area"))
            self.win.application.send_notification(None, notification)
            return

        startx, starty, endx, endy = listCoor[2], listCoor[3], listCoor[2] + listCoor[0] - 1, listCoor[
            1] + listCoor[3] - 1
        if listCoor[0] % 2 == 0 and listCoor[1] % 2 == 0:
            self.widthArea = endx - startx + 1
            self.heightArea = endy - starty + 1
        elif listCoor[0] % 2 == 0 and listCoor[1] % 2 == 1:
            self.widthArea = endx - startx + 1
            self.heightArea = endy - starty + 2
        elif listCoor[0] % 2 == 1 and listCoor[1] % 2 == 1:
            self.widthArea = endx - startx
            self.heightArea = endy - starty
        elif listCoor[0] % 2 == 1 and listCoor[1] % 2 == 0:
            self.widthArea = endx - startx + 2
            self.heightArea = endy - starty + 1

        self.coordinateArea = "startx={} starty={} endx={} endy={}".format(startx, starty, endx, endy)
        self.coordinateMode = True

    def delay(self, *args):
        self.win.time_delay = (self.win.delayBeforeRecording * 100)

        def countdown(*args):
            if self.win.time_delay > 0:
                self.win.time_delay -= 10
                GLib.timeout_add(100, countdown)
                self.win._delay_label.set_label(str((self.win.time_delay // 100) + 1))
            else:
                self.isrecordingwithdelay = False
                self.win._menu_stack_revealer.set_reveal_child(True)
                self.record_logic(self, *args)
                self.win.time_delay = (self.win.delayBeforeRecording * 100)

        countdown(*args)

    def record_logic(self, *args):
        if self.win.iscancelled:
            self.win._main_stack.set_visible_child(self.win._main_screen_box)
            self.win._record_stop_record_button_stack.set_visible_child(self.win._record_button)
            self.win._menu_stack.set_visible_child(self.win._menu_button)
            self.win.iscancelled = False
        else:
            self.win._record_stop_record_button_stack.set_visible_child(self.win._stop_record_button)
            self.win._main_stack.set_visible_child(self.win._paused_start_stack_box)
            self.win._menu_stack.set_visible_child(self.win._pause_record_button)
            self.win.label_context = self.win._time_recording_label.get_style_context()
            self.win.label_context.add_class("recording")

            self.quality_video = self.on__quality_changed(self, *args)
            self.videoFrames = self.on__frames_changed(self, *args)
            self.recordFormat = self.on__formats_changed(self, *args)

            self.soundOn = self.on__sound_switch(self, *args)
            fileNameTime = _(constants["APPNAME"]) + "-" + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            videoFolder = self.win.settings.get_string('path-to-save-video-folder')
            self.win.fileName = os.path.join(videoFolder, fileNameTime)

            if self.recordFormat == "webm":
                self.mux = "webmmux"
                self.win.extension = ".webm"

            elif self.recordFormat == "mkv":
                self.mux = "matroskamux"
                self.win.extension = ".mkv"

            elif self.recordFormat == "mp4":
                self.mux = "mp4mux"
                self.win.extension = ".mp4"

            if self.win.displayServer == "wayland":
                RecorderPipeline = "{0} ! queue ! {1}".format(self.quality_video, self.mux)
                if self.coordinateMode is True:
                    self.win.GNOMEScreencast.call_sync(
                        "ScreencastArea",
                        GLib.Variant.new_tuple(
                            GLib.Variant("i", self.waylandcoordinates[0]),
                            GLib.Variant("i", self.waylandcoordinates[1]),
                            GLib.Variant("i", self.waylandcoordinates[2]),
                            GLib.Variant("i", self.waylandcoordinates[3]),
                            GLib.Variant.new_string(self.win.fileName + self.win.extension),
                            GLib.Variant("a{sv}",
                                         {"framerate": GLib.Variant("i", int(self.videoFrames)),
                                          "draw-cursor": GLib.Variant("b", self.win.recordMouse),
                                          "pipeline": GLib.Variant("s", RecorderPipeline)}
                                         ),
                        ),
                        Gio.DBusProxyFlags.NONE,
                        -1,
                        None)
                    self.coordinateMode = False
                else:
                    self.win.GNOMEScreencast.call_sync(
                        "Screencast",
                        GLib.Variant.new_tuple(
                            GLib.Variant.new_string(self.win.fileName + self.win.extension),
                            GLib.Variant("a{sv}",
                                         {"framerate": GLib.Variant("i", int(self.videoFrames)),
                                          "draw-cursor": GLib.Variant("b", self.win.recordMouse),
                                          "pipeline": GLib.Variant("s", RecorderPipeline)}
                                         ),
                        ),
                        Gio.DBusProxyFlags.NONE,
                        -1,
                        None)
            else:
                if self.coordinateMode is True:
                    video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc show-pointer={0} " + self.coordinateArea + "! videoscale ! video/x-raw,width={1},height={2},framerate={3}/1 ! queue ! videoscale ! videoconvert ! {4} ! queue ! {5} name=mux ! queue ! filesink location='{6}'{7} "
                    if self.recordSoundOn is True:
                        self.video = Popen(
                            video_str.format(self.win.recordMouse, self.widthArea, self.heightArea,
                                             self.videoFrames, self.quality_video, self.mux, self.win.fileName,
                                             self.win.extension) + self.soundOn, shell=True)

                    else:
                        self.video = Popen(
                            video_str.format(self.win.recordMouse, self.widthArea, self.heightArea,
                                             self.videoFrames, self.quality_video, self.mux, self.win.fileName,
                                             self.win.extension), shell=True)

                    self.coordinateMode = False
                else:
                    if self.recordSoundOn is True:
                        self.video = Popen(
                            self.win.video_str.format(self.win.recordMouse, self.videoFrames, self.quality_video,
                                                      self.mux, self.win.fileName, self.win.extension) + self.soundOn,
                            shell=True)
                    else:
                        self.video = Popen(
                            self.win.video_str.format(self.win.recordMouse, self.videoFrames, self.quality_video,
                                                  self.mux, self.win.fileName, self.win.extension), shell=True)

            self.isrecording = True
            self.istimerrunning = True
            self.playsound('/com/github/amikha1lov/RecApp/sounds/chime.ogg')

    def on__quality_changed(self, *args):
        quality = self.win.settings.get_boolean("high-video-quality")
        self.recordFormat = self.on__formats_changed(self, *args)
        if quality:  # high quality
            if self.recordFormat == "webm" or self.recordFormat == "mkv":
                self.quality_video = "vp8enc min_quantizer=25 max_quantizer=25 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(
                    self.win.cpus)
            elif self.recordFormat == "mp4":
                self.win.quality_video = "x264enc qp-min=17 qp-max=17 speed-preset=1 threads={0} ! h264parse ! video/x-h264, profile=baseline".format(
                    self.win.cpus)
        else:
            if self.recordFormat == "webm" or self.recordFormat == "mkv":
                self.quality_video = "vp8enc min_quantizer=5 max_quantizer=10 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(
                    self.win.cpus)
            elif self.recordFormat == "mp4":
                self.win.quality_video = "x264enc qp-min=5 qp-max=5 speed-preset=1 threads={0} ! h264parse ! video/x-h264, profile=baseline".format(
                    self.win.cpus)
        return self.quality_video

    def on__formats_changed(self, *args):
        format = self.win.settings.get_enum("video-format")
        if format == 0:
            self.win.recordFormat = "webm"
        if format == 1:
            self.win.recordFormat = "mkv"
        if format == 2:
            self.win.recordFormat = "mp4"
        return self.win.recordFormat

    def on__frames_changed(self, *args):
        frames = self.win.settings.get_enum("frames-per-second")
        if frames == 0:
            self.videoFrames = 15
        if frames == 1:
            self.videoFrames = 30
        if frames == 2:
            self.videoFrames = 60
        return self.videoFrames

    def on__sound_switch(self, *args):
        if self.win._sound_on_computer.get_active():
            self.recordSoundOn = True

            import pulsectl
            with pulsectl.Pulse() as pulse:
                self.soundOnSource = pulse.sink_list()[0].name
                self.win.settings.set_boolean('sound-on-computer', True)
                if self.recordFormat == "webm" or self.recordFormat == "mkv":
                    self.soundOn = " pulsesrc provide-clock=false device='{}.monitor' buffer-time=20000000 ! 'audio/x-raw,depth=24,channels=2,rate=44100,format=F32LE,payload=96' ! queue ! audioconvert ! vorbisenc ! queue ! mux.".format(
                        self.soundOnSource)

                elif self.recordFormat == "mp4":
                    self.soundOn = " pulsesrc buffer-time=20000000 device='{}.monitor' ! 'audio/x-raw,channels=2,rate=48000' ! queue ! audioconvert ! queue ! opusenc bitrate=512000 ! queue ! mux.".format(
                        self.soundOnSource)
            return self.soundOn
        else:
            self.recordSoundOn = False
            self.win.settings.set_boolean('sound-on-computer', False)

    def stop_recording(self, *args):
        if self.win.displayServer == "wayland":
            self.win.GNOMEScreencast.call_sync(
                "StopScreencast",
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None)

        else:
            self.video.send_signal(signal.SIGINT)

        notification = Gio.Notification.new(constants["APPNAME"])
        notification.set_body(_("Recording is complete!"))
        notification.add_button(_("Open Folder"), "app.open-folder")
        notification.add_button(_("Open File"), "app.open-file")
        notification.set_default_action("app.open-file")
        self.win.application.send_notification(None, notification)

        self.win.isrecording = False
        self.win.istimerrunning = False

        self.win._record_stop_record_button_stack.set_visible_child(self.win._record_button)
        self.win._paused_start_stack.set_visible_child(self.win._recording_label)
        self.win._main_stack.set_visible_child(self.win._main_screen_box)
        self.win._menu_stack.set_visible_child(self.win._menu_button)
        self.win.label_context.remove_class("recording")

        self.win.elapsed_time = datetime.timedelta()
        self.win._time_recording_label.set_label(str(self.win.elapsed_time).replace(":", "∶"))

    def quit_app(self, *args):
        if self.isrecording:
            self.stop_recording(self)
        self.win.destroy()

    def cancel_delay(self, *args):
        self.win.time_delay = 0
        self.win.iscancelled = True

    def playsound(self, sound):
        playbin = Gst.ElementFactory.make('playbin', 'playbin')
        playbin.props.uri = 'resource://' + sound
        set_result = playbin.set_state(Gst.State.PLAYING)
        bus = playbin.get_bus()
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
        playbin.set_state(Gst.State.NULL)
