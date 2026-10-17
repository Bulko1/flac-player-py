"""Panel de detalle de la pista: carátula y metadatos (parte inferior)."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from song import Song
from ui import theme
from ui.widgets import shorten

COVER_SIZE = 100
_TITLE_LIMIT = 42
_SUBTITLE_LIMIT = 46


class TrackPanel(ttk.Frame):
    """Muestra la carátula y los metadatos de la pista actual."""

    def __init__(self, master):
        super().__init__(master)
        self._cover_cache: dict[str, ImageTk.PhotoImage] = {}
        self._build()

    def _build(self):
        cover_frame = ttk.Frame(self, width=110, height=110, style="Cover.TFrame")
        cover_frame.pack(side="left", padx=(0, 12))
        cover_frame.pack_propagate(False)

        self._cover_label = tk.Label(cover_frame, text="♫",
                                     font=(theme.FONT_FAMILY, 40),
                                     bg=theme.CTRL_BG, fg=theme.TEXT_SECONDARY)
        self._cover_label.place(relx=0.5, rely=0.5, anchor="center")

        info = ttk.Frame(self)
        info.pack(side="left", fill="x", expand=True)

        self._title_label = ttk.Label(info, text="Sin canción",
                                      style="Title.TLabel", anchor="w")
        self._title_label.pack(fill="x")

        self._artist_label = ttk.Label(info, text="", style="Subtitle.TLabel",
                                       anchor="w")
        self._artist_label.pack(fill="x", pady=(2, 0))

        self._album_label = ttk.Label(info, text="", style="Subtitle.TLabel",
                                      anchor="w")
        self._album_label.pack(fill="x")

        self._details_label = ttk.Label(info, text="", style="Subtitle.TLabel",
                                        anchor="w")
        self._details_label.pack(fill="x")

    def set_song(self, song: Song):
        self._title_label.configure(text=shorten(song.display_title, _TITLE_LIMIT))
        self._artist_label.configure(text=shorten(song.display_artist, _SUBTITLE_LIMIT))
        self._album_label.configure(text=shorten(song.display_album, _SUBTITLE_LIMIT))
        self._details_label.configure(text=f"FLAC · {song.bitrate_str}")

        photo = self._load_cover(song.cover_path) if song.cover_path else None
        if photo is not None:
            self._cover_label.configure(image=photo, text="")
            self._cover_label.image = photo
        else:
            self._show_placeholder()

    def clear_song(self):
        self._title_label.configure(text="Sin canción")
        self._artist_label.configure(text="")
        self._album_label.configure(text="")
        self._details_label.configure(text="")
        self._show_placeholder()

    def apply_theme(self):
        self._cover_label.configure(bg=theme.CTRL_BG, fg=theme.TEXT_SECONDARY)

    def _load_cover(self, path: str):
        if path in self._cover_cache:
            return self._cover_cache[path]
        try:
            img = Image.open(path)
            # Los JPEG grandes se decodifican ya reducidos: menos CPU y, sobre
            # todo, menos tiempo con el GIL tomado (el hilo de audio lo necesita).
            img.draft("RGB", (COVER_SIZE * 2, COVER_SIZE * 2))
            img = img.resize((COVER_SIZE, COVER_SIZE), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._cover_cache[path] = photo
            return photo
        except Exception:
            return None

    def _show_placeholder(self):
        self._cover_label.configure(image="", text="♫",
                                    font=(theme.FONT_FAMILY, 40))
