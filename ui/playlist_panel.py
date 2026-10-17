"""Panel inferior: lista de reproducción con filtro y controles."""

import tkinter as tk
from tkinter import ttk

from playlist import RepeatMode
from song import Song
from ui import theme
from ui.widgets import attach_tooltip


class PlaylistPanel(ttk.Frame):
    """Vista de la lista de reproducción.

    Mantiene el mapeo entre las filas visibles (posiblemente filtradas) y los
    índices reales dentro de la lista.
    """

    def __init__(self, master, callbacks: dict):
        super().__init__(master)
        self._cb = callbacks
        self._songs: list[Song] = []
        self._visible: list[int] = []  # fila -> índice real
        self._filter_var = tk.StringVar()
        self._busy = False

        self._build()
        self._filter_var.trace_add("write", lambda *_: self._render())

    # ── construcción ──────────────────────────────────────────────────
    def _build(self):
        # Cabecera: título a la izquierda, botones compactos a la derecha.
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 4))

        ttk.Label(header, text="Lista de Reproducción",
                  style="Header.TLabel").pack(side="left")

        self._theme_btn = ttk.Button(header, text="🌙", style="Icon.TButton",
                                     command=self._cb["toggle_theme"])
        self._theme_btn.pack(side="right", padx=1)
        attach_tooltip(self._theme_btn, "Cambiar tema (oscuro/claro)")

        header_buttons = [
            ("shuffle", "🔀", self._cb["toggle_shuffle"], "Aleatorio"),
            ("repeat", "🔁", self._cb["toggle_repeat"], "Repetir"),
            ("add_files", "📂", self._cb["add_files"], "Añadir archivos (Ctrl+O)"),
            ("add_folder", "📁", self._cb["add_folder"], "Añadir carpeta"),
        ]
        self._toggle_buttons: dict[str, ttk.Button] = {}
        for key, text, cmd, tip in reversed(header_buttons):
            btn = ttk.Button(header, text=text, style="Icon.TButton", command=cmd)
            btn.pack(side="right", padx=1)
            attach_tooltip(btn, tip)
            self._toggle_buttons[key] = btn

        # Filtro de búsqueda.
        search = ttk.Frame(self)
        search.pack(fill="x", pady=(0, 4))

        ttk.Label(search, text="🔎").pack(side="left", padx=(2, 4))
        self._filter_entry = ttk.Entry(search, textvariable=self._filter_var,
                                       font=(theme.FONT_FAMILY, 10))
        self._filter_entry.pack(side="left", fill="x", expand=True)

        # Lista con barra de desplazamiento.
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(list_frame,
                                   bg=theme.CTRL_BG, fg=theme.TEXT_PRIMARY,
                                   selectbackground=theme.BG_LIGHT,
                                   selectforeground=theme.TEXT_PRIMARY,
                                   borderwidth=0, highlightthickness=0,
                                   font=(theme.FONT_FAMILY, 10),
                                   activestyle="none", exportselection=False)
        self._listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self._listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._listbox.configure(yscrollcommand=scrollbar.set)

        self._listbox.bind("<Double-Button-1>", self._on_activate)
        self._listbox.bind("<Return>", self._on_activate)
        self._listbox.bind("<Delete>", self._on_delete)
        self._listbox.bind("<Button-3>", self._on_right_click)

        self._empty_label = tk.Label(list_frame,
                                     text="Añade archivos o carpetas\ncon música FLAC",
                                     font=(theme.FONT_FAMILY, 11),
                                     bg=theme.CTRL_BG, fg=theme.TEXT_SECONDARY,
                                     justify="center")
        self._empty_label.place(relx=0.5, rely=0.5, anchor="center")

    # ── API pública ───────────────────────────────────────────────────
    def set_songs(self, songs: list[Song]):
        self._songs = songs
        self._render()

    def set_shuffle(self, enabled: bool):
        self._toggle_buttons["shuffle"].configure(
            style="Active.TButton" if enabled else "Icon.TButton")

    def set_repeat(self, mode: RepeatMode):
        active = mode != RepeatMode.NONE
        self._toggle_buttons["repeat"].configure(
            style="Active.TButton" if active else "Icon.TButton")
        self._toggle_buttons["repeat"].configure(
            text="🔂" if mode == RepeatMode.ONE else "🔁")

    def set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        for key in ("add_files", "add_folder"):
            self._toggle_buttons[key].configure(state=state)

    def set_theme_icon(self, name: str):
        self._theme_btn.configure(text="🌙" if name == "dark" else "☀️")

    def apply_theme(self):
        self._listbox.configure(bg=theme.CTRL_BG, fg=theme.TEXT_PRIMARY,
                                selectbackground=theme.BG_LIGHT,
                                selectforeground=theme.TEXT_PRIMARY)
        self._empty_label.configure(bg=theme.CTRL_BG, fg=theme.TEXT_SECONDARY)

    def selected_real_index(self) -> int | None:
        selection = self._listbox.curselection()
        if not selection:
            return None
        row = selection[0]
        return self._visible[row] if 0 <= row < len(self._visible) else None

    def highlight(self, real_index: int):
        if real_index in self._visible:
            row = self._visible.index(real_index)
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(row)
            self._listbox.see(row)

    # ── render ────────────────────────────────────────────────────────
    def _matches(self, song: Song, needle: str) -> bool:
        haystack = f"{song.display_artist} {song.display_title} {song.album}".lower()
        return needle in haystack

    def _render(self):
        needle = self._filter_var.get().strip().lower()
        self._listbox.delete(0, tk.END)
        self._visible = []

        for real_index, song in enumerate(self._songs):
            if needle and not self._matches(song, needle):
                continue
            self._listbox.insert(tk.END, f"  {song.display_text}   {song.duration_str}")
            self._visible.append(real_index)

        if not self._songs:
            self._empty_label.configure(
                text="Añade archivos o carpetas\ncon música FLAC")
            self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
        elif not self._visible:
            self._empty_label.configure(text="Sin resultados")
            self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._empty_label.place_forget()

    # ── eventos ───────────────────────────────────────────────────────
    def _on_activate(self, _event=None) -> str:
        index = self.selected_real_index()
        if index is not None:
            self._cb["activate"](index)
        return "break"

    def _on_delete(self, _event=None) -> str:
        index = self.selected_real_index()
        if index is not None:
            self._cb["delete"](index)
        return "break"

    def _on_right_click(self, event):
        row = self._listbox.nearest(event.y)
        if not (0 <= row < len(self._visible)):
            return
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(row)

        menu = tk.Menu(self, tearoff=0, bg=theme.CTRL_BG, fg=theme.TEXT_PRIMARY,
                       activebackground=theme.BG_LIGHT, activeforeground=theme.TEXT_PRIMARY)
        menu.add_command(label="Reproducir", command=self._on_activate)
        menu.add_command(label="Reproducir a continuación",
                         command=lambda: self._cb["play_next"](self._visible[row]))
        menu.add_command(label="Eliminar", command=self._on_delete)
        menu.add_separator()
        menu.add_command(label="Añadir archivos...", command=self._cb["add_files"])
        menu.add_command(label="Añadir carpeta...", command=self._cb["add_folder"])
        menu.add_separator()
        menu.add_command(label="Vaciar lista", command=self._cb["clear"])
        menu.tk_popup(event.x_root, event.y_root)

    def focus_filter(self):
        self._filter_entry.focus_set()
