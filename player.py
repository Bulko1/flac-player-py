"""Motor de audio.

Decodifica en un hilo productor y entrega los frames ya listos al callback
del dispositivo de ``miniaudio``, evitando E/S de disco dentro del hilo de
tiempo real.
"""

import logging
import queue
import threading
import time
from array import array

import miniaudio

log = logging.getLogger(__name__)

#: Tamaño de bloque del hilo productor, en frames.
BLOCK_FRAMES = 4096
#: Número máximo de bloques decodificados en espera (~0.37 s a 44.1 kHz).
BUFFER_BLOCKS = 8
#: Latencia del buffer interno del dispositivo de audio, en milisegundos.
DEVICE_BUFFER_MSEC = 100

#: Centinela que marca el fin de pista dentro de la cola de audio.
_END_OF_SONG = object()


class Player:
    STATE_STOPPED = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2

    def __init__(self):
        self._file_path: str | None = None
        self._device: miniaudio.PlaybackDevice | None = None
        self._device_gen = None

        self._samplerate = 44100
        self._channels = 2
        self._total_frames = 0

        self._volume = 0.8
        self._playing = False
        self._paused = False
        self._current_frame = 0

        self._lock = threading.Lock()
        self._buffer: queue.Queue = queue.Queue(maxsize=BUFFER_BLOCKS)
        self._pending_block: array | None = None
        self._producer: threading.Thread | None = None
        self._producer_stop = threading.Event()
        self._song_ended = threading.Event()
        self._underruns = 0

    # ── carga / ciclo de vida ─────────────────────────────────────────
    def load(self, path: str) -> bool:
        """Carga un archivo y deja el reproductor listo (sin reproducir)."""
        self.stop()
        try:
            info = miniaudio.get_file_info(path)
            self._total_frames = info.num_frames
            self._samplerate = info.sample_rate
            self._channels = info.nchannels
            self._file_path = path
            self._current_frame = 0
            self._song_ended.clear()
            return True
        except Exception:
            log.warning("No se pudo cargar el archivo: %s", path, exc_info=True)
            self._file_path = None
            return False

    def play(self) -> bool:
        """Inicia o reanuda la reproducción. Devuelve ``False`` si falla."""
        if self._file_path is None:
            return False

        # Reanudar una pausa sin recrear el dispositivo.
        if self._device is not None and self._playing:
            if self._paused:
                self._paused = False
                return True
            return True

        # Reinicio (fin de pista previo o dispositivo cerrado).
        self._close_stream()
        with self._lock:
            start_frame = self._current_frame

        self._playing = True
        self._paused = False
        self._song_ended.clear()
        self._reset_buffer()
        self._start_producer(start_frame)
        self._prefill()

        if not self._start_stream():
            self._playing = False
            self._stop_producer()
            return False
        return True

    def pause(self):
        if self._playing and not self._paused:
            self._paused = True

    def stop(self):
        self._playing = False
        self._paused = False
        self._stop_producer()
        self._close_stream()
        with self._lock:
            self._current_frame = 0
        self._song_ended.clear()
        self._reset_buffer()

    def release(self):
        self.stop()
        self._file_path = None

    # ── dispositivo ───────────────────────────────────────────────────
    def _start_stream(self) -> bool:
        try:
            self._device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=self._channels,
                sample_rate=self._samplerate,
                buffersize_msec=DEVICE_BUFFER_MSEC,
            )
            self._device_gen = self._output_generator()
            next(self._device_gen)  # el generador debe estar iniciado
            self._device.start(self._device_gen)
            return True
        except Exception:
            log.error("No se pudo abrir el dispositivo de audio", exc_info=True)
            if self._device is not None:
                try:
                    self._device.close()
                except Exception:
                    log.debug("Error al limpiar el dispositivo fallido", exc_info=True)
            self._device = None
            self._device_gen = None
            return False

    def _close_stream(self):
        if self._device is not None:
            try:
                self._device.stop()
                self._device.close()
            except Exception:
                log.debug("Error al cerrar el dispositivo", exc_info=True)
            self._device = None
            self._device_gen = None

    def _output_generator(self):
        """Genera los frames que pide el dispositivo (hilo de tiempo real).

        Recibe la cantidad de frames pedida y devuelve exactamente esa
        cantidad, tomando bloques de la cola, aplicando el volumen y
        completando con silencio si no hay datos (underrun). En pausa emite
        silencio sin avanzar la posición, y tras el fin de pista sigue
        emitiendo silencio hasta que el reproductor cierre el dispositivo.
        """
        end_signalled = False
        wanted = yield None  # el dispositivo envía aquí la cantidad de frames
        while wanted:
            out = array("f", bytes(wanted * self._channels * 4))
            filled = 0  # muestras rellenadas (no frames)

            if self._playing and not self._paused:
                total = wanted * self._channels
                while filled < total:
                    if self._pending_block is None:
                        try:
                            item = self._buffer.get_nowait()
                        except queue.Empty:
                            self._underruns += 1
                            break  # underrun: el resto se completa con silencio
                        if item is _END_OF_SONG:
                            end_signalled = True
                            break
                        self._pending_block = item
                    block = self._pending_block
                    take = min(len(block), total - filled)
                    out[filled : filled + take] = block[:take]
                    self._pending_block = block[take:] if take < len(block) else None
                    filled += take

                if filled:
                    if self._volume != 1.0:
                        out = array("f", [sample * self._volume for sample in out])
                    with self._lock:
                        self._current_frame += filled // self._channels

            if end_signalled:
                self._finish()

            wanted = yield out

    # ── hilo productor ────────────────────────────────────────────────
    def _reset_buffer(self):
        self._buffer = queue.Queue(maxsize=BUFFER_BLOCKS)
        self._pending_block = None

    def _prefill(self, timeout: float = 0.5):
        """Espera datos antes de arrancar el dispositivo.

        Sin esto el primer callback del dispositivo encuentra la cola vacía y
        se oye un silencio inicial (más largo cuanto más lento es el disco).
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._buffer.qsize() >= 2:
                return
            if self._song_ended.is_set():
                return
            if self._producer is not None and not self._producer.is_alive():
                return
            time.sleep(0.005)

    def _start_producer(self, start_frame: int):
        self._producer_stop = threading.Event()
        self._producer = threading.Thread(
            target=self._producer_loop,
            args=(start_frame, self._producer_stop),
            name="flac-producer",
            daemon=True,
        )
        self._producer.start()

    def _stop_producer(self):
        if self._producer_stop is not None:
            self._producer_stop.set()
        self._drain_buffer()
        if self._producer is not None:
            self._producer.join(timeout=1.0)
            self._producer = None

    def _drain_buffer(self):
        while True:
            try:
                self._buffer.get_nowait()
            except queue.Empty:
                break

    def _producer_loop(self, start_frame: int, stop_event: threading.Event):
        decoder = None
        try:
            decoder = miniaudio.stream_file(
                self._file_path,
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=self._channels,
                sample_rate=self._samplerate,
                frames_to_read=BLOCK_FRAMES,
                seek_frame=start_frame,
            )
            while not stop_event.is_set():
                try:
                    chunk = decoder.send(BLOCK_FRAMES)
                except StopIteration:
                    break
                frames_read = len(chunk) // self._channels
                if frames_read == 0:
                    break
                self._put(chunk, stop_event)
                if frames_read < BLOCK_FRAMES:
                    break  # último bloque parcial
            if not stop_event.is_set():
                self._put(_END_OF_SONG, stop_event)  # centinela de fin de pista
        except Exception:
            log.warning("Error en el hilo de decodificación", exc_info=True)
            self._put(_END_OF_SONG, stop_event)
        finally:
            if decoder is not None:
                decoder.close()

    def _put(self, item, stop_event: threading.Event):
        """Inserta en el buffer sin bloquear indefinidamente."""
        while not stop_event.is_set():
            try:
                self._buffer.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    # ── consultas ─────────────────────────────────────────────────────
    def _finish(self):
        self._playing = False
        self._song_ended.set()

    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def get_state(self) -> int:
        if not self._playing:
            return self.STATE_STOPPED
        if self._paused:
            return self.STATE_PAUSED
        return self.STATE_PLAYING

    def song_ended(self) -> bool:
        return self._song_ended.is_set()

    def acknowledge_end(self):
        self._song_ended.clear()

    def get_position(self) -> float:
        with self._lock:
            return self._current_frame / self._samplerate if self._samplerate > 0 else 0.0

    def get_duration(self) -> float:
        return self._total_frames / self._samplerate if self._samplerate > 0 else 0.0

    def seek(self, seconds: float):
        if self._file_path is None:
            return
        frame = int(max(0.0, float(seconds)) * self._samplerate)
        if self._total_frames > 0:
            frame = min(frame, self._total_frames - 1)
        frame = max(0, frame)

        with self._lock:
            self._current_frame = frame

        if self._playing:
            self._stop_producer()
            self._reset_buffer()
            self._start_producer(frame)
            self._prefill()

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))

    def get_volume(self) -> float:
        return self._volume

    def take_underruns(self) -> int:
        """Devuelve los cortes por buffer vacío acumulados y reinicia el contador."""
        count = self._underruns
        self._underruns = 0
        return count
