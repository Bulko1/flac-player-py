"""Fixtures compartidas por los tests.

Los FLAC de prueba están versionados en ``tests/assets/`` y se copian a
``tmp_path``, de modo que cada test puede modificarlos (p. ej. insertar
bloques PICTURE) sin depender de librerías de codificación.
"""

import array
import math
import shutil
import wave
from pathlib import Path

import pytest

ASSETS = Path(__file__).parent / "assets"


def _copy_asset(name: str, destination: Path) -> str:
    shutil.copyfile(ASSETS / name, destination)
    return str(destination)


@pytest.fixture
def flac_file(tmp_path):
    """FLAC de prueba: 1 s, mono, 8 kHz, seno 440 Hz, sin tags."""
    return _copy_asset("tone.flac", tmp_path / "tone.flac")


@pytest.fixture
def tagged_flac(tmp_path):
    """FLAC de prueba: 2 s, mono, 8 kHz, con tags Vorbis (title/artist/album)."""
    return _copy_asset("tagged.flac", tmp_path / "tagged.flac")


@pytest.fixture
def stereo_wav(tmp_path):
    """WAV estéreo de 1 s, 44.1 kHz y seno 440 Hz.

    Se genera con la biblioteca estándar (sin codificadores externos) para
    cubrir las rutas de dos canales, que los FLAC de prueba (mono) no cubren.
    """
    rate = 44100
    frames = rate
    samples = array.array("h")
    for i in range(frames):
        value = int(0.25 * 32767 * math.sin(2 * math.pi * 440 * i / rate))
        samples.append(value)
        samples.append(value)
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(2)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(samples.tobytes())
    return str(path)

