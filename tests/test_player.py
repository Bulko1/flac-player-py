import time

import miniaudio
import pytest

from player import BLOCK_FRAMES, Player


class FakeDevice:
    """Simula un PlaybackDevice de miniaudio, guardando el generador de audio."""

    def __init__(self, **kwargs):
        self.settings = kwargs
        self.callback_generator = None
        self.started = False
        self.closed = False

    def start(self, callback_generator):
        self.callback_generator = callback_generator
        self.started = True

    def stop(self):
        self.started = False
        self.callback_generator = None

    def close(self):
        self.closed = True
        self.callback_generator = None


@pytest.fixture
def fake_audio(monkeypatch):
    devices = []

    def factory(**kwargs):
        device = FakeDevice(**kwargs)
        devices.append(device)
        return device

    monkeypatch.setattr(miniaudio, "PlaybackDevice", factory)
    return devices


def _wait_for_audio(player, timeout=3.0):
    """Espera a que el hilo productor tenga datos listos en la cola."""
    deadline = time.time() + timeout
    while time.time() < deadline and player._buffer.empty():
        time.sleep(0.01)


def _pull(device, frames=BLOCK_FRAMES):
    """Simula un periodo del dispositivo: pide ``frames`` al generador."""
    return device.callback_generator.send(frames)


def _consume(device, player, limit=2000):
    """Simula el dispositivo pidiendo bloques hasta el fin de pista."""
    for _ in range(limit):
        out = _pull(device)
        assert len(out) == BLOCK_FRAMES * device.settings["nchannels"]
        if player.song_ended():
            return True
        time.sleep(0.002)
    return False


def test_load_and_duration(flac_file):
    p = Player()
    assert p.load(flac_file) is True
    assert 0.9 < p.get_duration() < 1.1


def test_load_invalid_path():
    p = Player()
    assert p.load("/does/not/exist.flac") is False
    assert p.get_duration() == 0


def test_play_reaches_end(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    assert p.play() is True
    _wait_for_audio(p)

    device = fake_audio[0]
    assert device.started is True
    assert _consume(device, p) is True
    assert p.get_state() == Player.STATE_STOPPED


def test_pause_freezes_position(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    p.play()
    _wait_for_audio(p)

    device = fake_audio[0]
    _pull(device)  # consume algo de audio
    p.pause()

    out = _pull(device)
    assert not any(out)  # silencio en pausa
    assert p.get_state() == Player.STATE_PAUSED


def test_pause_then_resume(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    p.play()
    _wait_for_audio(p)

    device = fake_audio[0]
    p.pause()
    assert p.play() is True
    assert p.get_state() == Player.STATE_PLAYING
    assert any(_pull(device))  # vuelve a oírse audio


def test_stop_resets(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    p.play()
    _wait_for_audio(p)

    device = fake_audio[0]
    p.stop()
    assert p.get_state() == Player.STATE_STOPPED
    assert p.get_position() == 0.0
    assert device.closed is True


def test_seek_is_clamped(flac_file):
    p = Player()
    p.load(flac_file)
    p.seek(-10)
    assert p.get_position() == 0.0
    p.seek(10_000)
    assert 0.0 < p.get_position() < p.get_duration()


def test_seek_mid_playback(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    p.play()
    _wait_for_audio(p)

    device = fake_audio[0]
    _pull(device)
    p.seek(0.5)
    assert 0.49 < p.get_position() < 0.51
    assert len(_pull(device)) == BLOCK_FRAMES


def test_volume_zero_produces_silence(flac_file, fake_audio):
    p = Player()
    p.load(flac_file)
    p.set_volume(0.0)
    p.play()
    _wait_for_audio(p)

    assert not any(_pull(fake_audio[0]))


def test_set_volume_clamps():
    p = Player()
    p.set_volume(5.0)
    assert p.get_volume() == 1.0
    p.set_volume(-5.0)
    assert p.get_volume() == 0.0


def test_play_without_file_returns_false():
    assert Player().play() is False


def test_stereo_callback_fills_whole_buffer(stereo_wav, fake_audio):
    """Regresión: ``filled`` debe contar muestras, no frames.

    Con estéreo, el bug original rellenaba solo la mitad del buffer y dejaba
    la otra mitad en silencio (música a mitad de velocidad con cortes).
    """
    p = Player()
    p.set_volume(1.0)
    assert p.load(stereo_wav) is True
    assert p.play() is True
    _wait_for_audio(p)

    device = fake_audio[0]
    frames = 4410  # periodo de 100 ms a 44.1 kHz
    out = _pull(device, frames)

    assert len(out) == frames * 2
    non_silent = sum(1 for sample in out if sample != 0.0)
    assert non_silent > len(out) * 0.9, "la segunda mitad del buffer va en silencio"
    assert any(sample != 0.0 for sample in out[frames:])

    before = p.get_position()
    _pull(device, frames)
    assert p.get_position() - before == pytest.approx(frames / 44100)


def test_play_prefills_before_start(stereo_wav, fake_audio):
    """El primer callback ya debe traer audio (sin silencio inicial)."""
    p = Player()
    p.set_volume(0.5)
    assert p.load(stereo_wav) is True
    assert p.play() is True

    out = _pull(fake_audio[0], 4410)
    assert any(out)


def test_underrun_is_counted(stereo_wav, fake_audio):
    p = Player()
    assert p.load(stereo_wav) is True
    assert p.play() is True
    _wait_for_audio(p)

    p._stop_producer()  # sin productor no habrá más bloques
    p._reset_buffer()  # cola vacía garantizada
    out = _pull(fake_audio[0], 800)

    assert not any(out)
    assert p.take_underruns() >= 1
    assert p.take_underruns() == 0  # se reinicia al consultarlo
    p.stop()
