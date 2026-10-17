"""Panel de controles: progreso/seek, transporte y volumen (parte central)."""

import tkinter as tk
from tkinter import ttk

from ui.widgets import attach_tooltip, format_time


class TransportPanel(ttk.Frame):
    """Controles de reproducción: seek, transporte y volumen."""

    def __init__(self, master, callbacks: dict):
        super().__init__(master)
        self._cb = callbacks

        self._position_var = tk.DoubleVar(value=0.0)
        self._volume_var = tk.DoubleVar(value=80.0)

        self._seeking = False
        self._playing = False
        self._muted = False
        self._last_volume = 80.0

        self._build()

    # ── construcción ──────────────────────────────────────────────────
    def _build(self):
        # Barra de progreso con marca de tiempo.
        progress = ttk.Frame(self)
        progress.pack(fill="x")

        self._time_label = ttk.Label(progress, text="0:00 / --:--", style="Time.TLabel")
        self._time_label.pack(side="right")

        self._progress_slider = ttk.Scale(progress, from_=0, to=100,
                                          variable=self._position_var,
                                          style="Progress.Horizontal.TScale",
                                          state="disabled")
        self._progress_slider.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._progress_slider.bind("<ButtonPress-1>", self._on_seek_start)
        self._progress_slider.bind("<ButtonRelease-1>", self._on_seek_end)

        # Fila de transporte: botones a la izquierda, volumen a la derecha.
        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(8, 0))

        buttons = [
            ("⏮", "prev", "Icon.TButton", self._cb["previous"], "Anterior"),
            ("▶", "play", "Play.TButton", self._cb["play_pause"], "Reproducir / Pausar"),
            ("⏹", "stop", "Icon.TButton", self._cb["stop"], "Detener"),
            ("⏭", "next", "Icon.TButton", self._cb["next"], "Siguiente"),
        ]
        self._play_btn: ttk.Button | None = None
        for text, key, style, cmd, tip in buttons:
            btn = ttk.Button(controls, text=text, style=style, command=cmd)
            btn.pack(side="left", padx=(0, 2))
            attach_tooltip(btn, tip)
            if key == "play":
                self._play_btn = btn

        vol_frame = ttk.Frame(controls)
        vol_frame.pack(side="right")

        self._vol_icon = ttk.Button(vol_frame, text="🔊", style="Icon.TButton",
                                    command=self._toggle_mute)
        self._vol_icon.pack(side="left", padx=(0, 4))

        vol_slider = ttk.Scale(vol_frame, from_=0, to=100,
                               variable=self._volume_var,
                               style="Volume.Horizontal.TScale", length=90,
                               command=self._on_volume_changed)
        vol_slider.pack(side="left")

    # ── API pública ───────────────────────────────────────────────────
    def set_playing(self, playing: bool):
        self._playing = playing
        if self._play_btn is not None:
            self._play_btn.configure(text="⏸" if playing else "▶")

    def set_duration(self, seconds: float):
        self._progress_slider.configure(to=max(seconds, 0.001), state="normal")
        self._update_time_label(self._position_var.get(), seconds)

    def set_position(self, seconds: float, duration: float | None = None):
        if self._seeking:
            return
        self._position_var.set(seconds)
        self._update_time_label(seconds, duration)

    def reset(self):
        self.set_playing(False)
        self._progress_slider.configure(state="disabled")
        self._position_var.set(0.0)
        self._update_time_label(0.0, 0.0)

    def position(self) -> float:
        return self._position_var.get()

    def volume(self) -> float:
        return self._volume_var.get()

    def set_volume(self, value: float):
        self._volume_var.set(value)
        self._last_volume = value if value > 0 else self._last_volume
        self._on_volume_changed(value)

    def is_seeking(self) -> bool:
        return self._seeking

    # ── internos ──────────────────────────────────────────────────────
    def _on_seek_start(self, _event=None):
        self._seeking = True

    def _on_seek_end(self, _event=None):
        self._seeking = False
        self._cb["seek"](self._position_var.get())

    def _on_volume_changed(self, value=None):
        if value is None:
            value = self._volume_var.get()
        self._cb["volume"](float(value))

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._last_volume = self._volume_var.get() or self._last_volume
            self._vol_icon.configure(text="🔇")
            self._volume_var.set(0)
            self._cb["volume"](0.0)
        else:
            self._vol_icon.configure(text="🔊")
            self._volume_var.set(self._last_volume)
            self._cb["volume"](self._last_volume)

    def _update_time_label(self, position: float, duration: float | None):
        duration = self._progress_slider.cget("to") if duration is None else duration
        pos_str = format_time(position)
        dur_str = format_time(duration) if duration and duration > 0 else "--:--"
        self._time_label.configure(text=f"{pos_str} / {dur_str}")
