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
import multiprocessing
import os
import signal
import sys
import time
import datetime
from locale import gettext as _
from subprocess import PIPE, Popen

import gi
import pulsectl
from pydbus import SessionBus

from .recapp_constants import recapp_constants as constants

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Notify', '0.7')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gdk, Gio, GLib, Gst, GstPbutils, Gtk, Notify

Gtk.init(sys.argv)
# initialize GStreamer
Gst.init(sys.argv)


def formats_combobox_changed(self, box):
    self.recordFormat = box.get_active_text()
    self.settings.set_string('format-video', self.recordFormat)


def video_folder_button(self, button):
    self.settings.set_string('path-to-save-video-folder', self._video_folder_button.get_filename())
    self._video_folder_button.set_current_folder_uri(
        self.settings.get_string('path-to-save-video-folder'))


def quality_video_switcher(self, *args):
    if self._quality_video_switcher.get_active():
        state = "on"
        self.settings.set_boolean('high-quality-switch', True)
        if self.recordFormat == "webm" or self.recordFormat == "mkv":
            self.quality_video = "vp8enc min_quantizer=5 max_quantizer=10 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(
                self.cpus)
        elif self.recordFormat == "mp4":
            self.quality_video = "x264enc qp-min=5 qp-max=5 speed-preset=1 threads={0} ! h264parse ! video/x-h264, profile=baseline".format(
                self.cpus)
        return self.quality_video
    else:
        state = "off"
        self.settings.set_boolean('high-quality-switch', False)
        if self.recordFormat == "webm" or self.recordFormat == "mkv":
            self.quality_video = "vp8enc min_quantizer=25 max_quantizer=25 cpu-used={0} cq_level=13 deadline=1000000 threads={0}".format(
                self.cpus)
        elif self.recordFormat == "mp4":
            self.quality_video = "x264enc qp-min=17 qp-max=17 speed-preset=1 threads={0} ! h264parse ! video/x-h264, profile=baseline".format(
                self.cpus)
        return self.quality_video


def delay_button_change(self, spin):
    self.delayBeforeRecording = spin.get_value_as_int()
    self.settings.set_int('delay', spin.get_value_as_int())


def frames_combobox_changed(self, box):
    self.videoFrames = int(box.get_active_text())
    self.settings.set_int('frames', int(box.get_active_text()))


def mouse_switcher(self, switch, gparam):
    if switch.get_active():
        state = "on"
        self.recordMouse = True
        self.settings.set_boolean('record-mouse-cursor-switch', True)
    else:
        state = "off"
        self.recordMouse = False
        self.settings.set_boolean('record-mouse-cursor-switch', False)


def on__select_area(self):
    coordinate = Popen("slop -n -c 0.3,0.4,0.6,0.4 -l -t 0 -f '%w %h %x %y'", shell=True,
                       stdout=PIPE).communicate()
    listCoor = [int(i) for i in coordinate[0].decode().split()]
    if not listCoor[0] or not listCoor[1]:
        self.notification = Notify.Notification.new(constants["APPNAME"],
                                                    _("Please re-select the area"))
        self.notification.show()
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


def on__sound_switch(self, *args):
    if self._sound_on_switch.get_active():
        self.recordSoundOn = True
        with pulsectl.Pulse() as pulse:
            self.soundOnSource = pulse.sink_list()[0].name
            self.settings.set_boolean('record-audio-switch', True)
            if self.recordFormat == "webm" or self.recordFormat == "mkv":
                self.soundOn = " pulsesrc provide-clock=false device='{}.monitor' buffer-time=20000000 ! 'audio/x-raw,depth=24,channels=2,rate=44100,format=F32LE,payload=96' ! queue ! audioconvert ! vorbisenc ! queue ! mux.".format(
                    self.soundOnSource)

            elif self.recordFormat == "mp4":
                self.soundOn = " pulsesrc buffer-time=20000000 device='{}.monitor' ! 'audio/x-raw,channels=2,rate=48000' ! queue ! audioconvert ! queue ! opusenc bitrate=512000 ! queue ! mux.".format(
                    self.soundOnSource)
        return self.soundOn
    else:
        self.recordSoundOn = False
        self.settings.set_boolean('record-audio-switch', False)


def start_recording(self, *args):
    if self.isFullscreenMode:
        self.coordinateMode = False
        record(self)
    elif self.isWindowMode:
        print('window mode')
    else:
        on__select_area(self)
        record(self)


def record(self, *args):
    if self.delayBeforeRecording > 0:
        self._main_stack.set_visible_child(self._delay_box)
        self._record_stop_record_button_stack.set_visible_child(self._cancel_button)
        self._preferences_back_stack_revealer.set_reveal_child(False)
        self.isrecordingwithdelay = True
        delay(self, *args)
    else:
        self._preferences_back_stack_revealer.set_reveal_child(False)
        record_logic(self, *args)


def record_logic(self, *args):
    if self.iscancelled:
        self._main_stack.set_visible_child(self._main_screen_box)
        self._record_stop_record_button_stack.set_visible_child(self._record_button)
        self._preferences_back_stack_revealer.set_reveal_child(True)
        self.iscancelled = False
    else:
        self._record_stop_record_button_stack.set_visible_child(self._stop_record_button)
        self._pause_continue_record_button_stack_revealer.set_reveal_child(True)
        self._main_stack.set_visible_child(self._paused_start_stack_box)

        self.istimerrunning = True

        self.label_context = self._time_recording_label.get_style_context()
        self.label_context.add_class("recording")

        self.quality_video = quality_video_switcher(self, *args)
        self.soundOn = on__sound_switch(self, *args)
        fileNameTime = _(constants["APPNAME"]) + "-" + time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        videoFolder = self.settings.get_string('path-to-save-video-folder')
        self.fileName = os.path.join(videoFolder, fileNameTime)

        if self.recordFormat == "webm":
            self.mux = "webmmux"
            self.extension = ".webm"

        elif self.recordFormat == "mkv":
            self.mux = "matroskamux"
            self.extension = ".mkv"

        elif self.recordFormat == "mp4":
            self.mux = "mp4mux"
            self.extension = ".mp4"

        if self.displayServer == "wayland":

            RecorderPipeline = "{0} ! queue ! {1}".format(self.quality_video, self.mux)
            self.GNOMEScreencast.Screencast(self.fileName + self.extension,
                                            {'framerate': GLib.Variant('i', int(self.videoFrames)),
                                             'draw-cursor': GLib.Variant('b', self.recordMouse),
                                             'pipeline': GLib.Variant('s', RecorderPipeline)})
        else:
            if self.coordinateMode == True:
                video_str = "gst-launch-1.0 --eos-on-shutdown ximagesrc show-pointer={0} " + self.coordinateArea + " ! videoscale ! video/x-raw,width={1},height={2},framerate={3}/1 ! queue ! videoscale ! videoconvert ! {4} ! queue ! {5} name=mux ! queue ! filesink location='{6}'{7}"
                if self.recordSoundOn == True:
                    self.video = Popen(
                        video_str.format(self.recordMouse, self.widthArea, self.heightArea,
                                         self.videoFrames, self.quality_video, self.mux, self.fileName,
                                         self.extension) + self.soundOn, shell=True)

                else:
                    self.video = Popen(
                        video_str.format(self.recordMouse, self.widthArea, self.heightArea,
                                         self.videoFrames, self.quality_video, self.mux, self.fileName,
                                         self.extension), shell=True)

                self.coordinateMode = False
            else:
                if self.recordSoundOn == True:
                    self.video = Popen(
                        self.video_str.format(self.recordMouse, self.videoFrames, self.quality_video,
                                              self.mux, self.fileName, self.extension) + self.soundOn,
                        shell=True)
                else:
                    self.video = Popen(
                        self.video_str.format(self.recordMouse, self.videoFrames, self.quality_video,
                                              self.mux, self.fileName, self.extension), shell=True)

        self.isrecording = True


def delay(self, *args):
    self.time_delay = self.delayBeforeRecording
    def countdown(*args):
        self._delay_label.set_label(str(self.time_delay))
        if self.time_delay > 0:
            self.time_delay -=1
            GLib.timeout_add_seconds(1, countdown)
        else:
            self.isrecordingwithdelay = False
            record_logic(self, *args)
            self.time_delay = self.delayBeforeRecording
    countdown(*args)


def cancel_delay(self, *args):
    self.time_delay = 0
    self.iscancelled = True


def stop_recording(self, *args):

    if self.displayServer == "wayland":
        self.GNOMEScreencast.StopScreencast()

    else:
        self.video.send_signal(signal.SIGINT)

    self.notification = Notify.Notification.new(constants["APPNAME"], _("Recording is complete!"))
    self.notification.add_action("open_folder", _("Open Folder"), self.openFolder)
    self.notification.add_action("open_file", _("Open File"), self.openVideoFile)
    self.notification.show()
    self.isrecording = False
    self.istimerrunning = False

    self._record_stop_record_button_stack.set_visible_child(self._record_button)
    self._pause_continue_record_button_stack_revealer.set_reveal_child(False)
    self._pause_continue_record_button_stack.set_visible_child(self._pause_record_button)
    self._paused_start_stack.set_visible_child(self._recording_label)
    self._main_stack.set_visible_child(self._main_screen_box)
    self._preferences_back_stack_revealer.set_reveal_child(True)

    self.label_context.remove_class("recording")

    self.elapsed_time = datetime.timedelta()
    self._time_recording_label.set_label(str(self.elapsed_time).replace(":","∶"))


def delete_event(self, w, h):
    if self.isrecording:
        stop_recording(self)


def toggle_audio(self, *args):
    if not self.isrecordingwithdelay:
        if not self.isrecording:
            if self._sound_on_switch.get_active():
                self._sound_on_switch.set_active(False)
            else:
                if self.displayServer == "wayland":
                    self._sound_on_switch.set_active(False)
                else:
                    self._sound_on_switch.set_active(True)


def toggle_high_quality(self, *args):
    if not self.isrecordingwithdelay:
        if not self.isrecording:
            if self._quality_video_switcher.get_active():
                self._quality_video_switcher.set_active(False)
            else:
                self._quality_video_switcher.set_active(True)


def toggle_record(self, *args):
    if not self.isrecordingwithdelay:
        if self.isrecording:
            stop_recording(self)
        else:
            start_recording(self)


def quit_app(self, *args):
    if self.isrecording:
        stop_recording(self)

    self.destroy()


def toggle_mouse_record(self, *args):
    if not self.isrecordingwithdelay:
        if not self.isrecording:
            if self._record_mouse_switcher.get_active():
                self._record_mouse_switcher.set_active(False)
            else:
                self._record_mouse_switcher.set_active(True)


def toggle_microphone(self, *args):
    if not self.isrecordingwithdelay:
        if not self.isrecording:
            if self._sound_on_microphone.get_active():
                self._sound_on_microphone.set_active(False)
            else:
                self._sound_on_microphone.set_active(True)


def cancel_record(self, *args):
    if self.isrecordingwithdelay:
        cancel_delay(self)
