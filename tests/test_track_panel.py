"""Pruebas del panel de detalle de la pista (carátula y metadatos)."""

import tkinter as tk

import pytest

from song import Song


@pytest.fixture
def panel():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Sin entorno gráfico disponible")

    from ui.track_panel import TrackPanel

    widget = TrackPanel(root)
    yield widget
    try:
        root.destroy()
    except tk.TclError:
        pass


def test_set_song_shows_bitrate(panel):
    panel.set_song(Song(path="x", title="T", bitrate=923_400))
    assert panel._details_label.cget("text") == "FLAC · 923 kbps"


def test_set_song_without_bitrate(panel):
    panel.set_song(Song(path="x"))
    assert panel._details_label.cget("text") == "FLAC · -- kbps"


def test_clear_song_hides_bitrate(panel):
    panel.set_song(Song(path="x", bitrate=923_400))
    panel.clear_song()
    assert panel._details_label.cget("text") == ""
