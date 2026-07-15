import threading

import numpy as np
import sounddevice as sd
import soundfile as sf


class Player:
    STATE_STOPPED = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2

    def __init__(self):
        self._file: sf.SoundFile | None = None
        self._stream: sd.OutputStream | None = None
        self._file_path: str | None = None

        self._playing = False
        self._paused = False
        self._volume = 0.8

        self._lock = threading.Lock()
        self._seek_frame: int | None = None
        self._current_frame = 0
        self._total_frames = 0
        self._samplerate = 44100
        self._channels = 2
        self._song_ended = False
        self._on_end_callback = None

    def set_on_end(self, callback):
        self._on_end_callback = callback

    def load(self, path: str) -> bool:
        self.stop()
        try:
            with sf.SoundFile(path) as f:
                self._total_frames = f.frames
                self._samplerate = f.samplerate
                self._channels = f.channels
            self._file_path = path
            self._current_frame = 0
            self._song_ended = False
            return True
        except Exception:
            self._file_path = None
            return False

    def play(self):
        if self._file_path is None:
            return

        if self._stream is not None:
            if self._paused:
                self._paused = False
                self._playing = True
                return
            self.stop()

        self._playing = True
        self._paused = False
        self._song_ended = False

        self._file = sf.SoundFile(self._file_path)
        if self._current_frame > 0:
            self._file.seek(self._current_frame)

        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=self._channels,
            callback=self._audio_callback,
            blocksize=2048,
            dtype="float32",
        )
        self._stream.start()

    def _audio_callback(self, outdata, frames, _time, _status):
        with self._lock:
            if self._seek_frame is not None:
                if self._file is not None:
                    self._file.seek(self._seek_frame)
                    self._current_frame = self._seek_frame
                self._seek_frame = None

            if self._paused or not self._playing or self._file is None:
                outdata.fill(0)
                return

            try:
                data = self._file.read(frames, dtype="float32", fill_value=0)
                frames_read = data.shape[0]

                if frames_read < frames:
                    outdata[:frames_read] = data * self._volume
                    outdata[frames_read:] = 0
                    self._playing = False
                    self._song_ended = True
                    raise sd.CallbackStop

                outdata[:] = data * self._volume
                self._current_frame += frames_read

            except sd.CallbackStop:
                raise
            except Exception:
                outdata.fill(0)

    def pause(self):
        if self._playing and not self._paused:
            self._paused = True

    def stop(self):
        with self._lock:
            self._playing = False
            self._paused = False
            self._current_frame = 0
            self._seek_frame = None
        self._close_stream()

    def _close_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def get_state(self) -> int:
        if self._song_ended:
            self._song_ended = False
            if self._on_end_callback:
                self._on_end_callback()
            return self.STATE_STOPPED
        if not self._playing:
            return self.STATE_STOPPED
        if self._paused:
            return self.STATE_PAUSED
        return self.STATE_PLAYING

    def get_position(self) -> float:
        with self._lock:
            return self._current_frame / self._samplerate if self._samplerate > 0 else 0.0

    def get_duration(self) -> float:
        return self._total_frames / self._samplerate if self._samplerate > 0 else 0.0

    def seek(self, seconds: float):
        with self._lock:
            frame = int(seconds * self._samplerate)
            frame = max(0, min(frame, self._total_frames - 1))
            self._seek_frame = frame

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))

    def get_volume(self) -> float:
        return self._volume

    def release(self):
        self._on_end_callback = None
        self.stop()
