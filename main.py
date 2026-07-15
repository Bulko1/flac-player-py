import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from metadata_service import find_flac_files, read_songs
from player import Player
from playlist import Playlist, RepeatMode
from song import Song


# ── Colour palette ──────────────────────────────────────────────────
BG_DARK      = "#1A1A2E"
BG_MEDIUM    = "#16213E"
BG_LIGHT     = "#0F3460"
ACCENT       = "#E94560"
TEXT_PRIMARY  = "#EAEAEA"
TEXT_SECONDARY = "#A0A0B0"
CTRL_BG      = "#25253D"
CTRL_BORDER  = "#3A3A5C"


class FlacPlayerUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FlacPlayer")
        self.root.geometry("480x650")
        self.root.minsize(400, 500)
        self.root.configure(bg=BG_DARK)

        self.player = Player()
        self.playlist = Playlist()

        self._current_song: Song | None = None
        self._seeking = False
        self._position_var = tk.DoubleVar(value=0.0)
        self._volume_var = tk.DoubleVar(value=80.0)

        self._setup_styles()
        self._build_ui()
        self._bind_events()

        self.player.set_on_end(self._on_song_ended)

        self._update_position_loop()

    # ── styles ──────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY,
                        fieldbackground=CTRL_BG, bordercolor=CTRL_BORDER)
        style.configure("TFrame", background=BG_DARK)
        style.configure("TLabelframe", background=BG_DARK, foreground=TEXT_PRIMARY)
        style.configure("TLabelframe.Label", background=BG_DARK, foreground=TEXT_PRIMARY)

        style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY,
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=TEXT_SECONDARY)
        style.configure("Small.TLabel", font=("Segoe UI", 9), foreground=TEXT_SECONDARY)
        style.configure("Time.TLabel", font=("Segoe UI", 9), foreground=TEXT_SECONDARY)

        style.configure("TButton", background=CTRL_BG, foreground=TEXT_PRIMARY,
                        borderwidth=1, focusthickness=0, font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("active", BG_LIGHT), ("pressed", ACCENT)])

        style.configure("Icon.TButton", background=BG_DARK, borderwidth=0,
                        font=("Segoe UI", 14))
        style.map("Icon.TButton",
                  background=[("active", BG_MEDIUM)])

        style.configure("Play.TButton", background=BG_DARK, borderwidth=0,
                        font=("Segoe UI", 22))
        style.map("Play.TButton",
                  background=[("active", BG_MEDIUM)])

        style.configure("TScale", background=BG_DARK, troughcolor=CTRL_BG,
                        sliderlength=16, slidercolor=TEXT_PRIMARY)

        style.configure("Progress.Horizontal.TScale", background=BG_DARK,
                        troughcolor=CTRL_BG, sliderlength=14, slidercolor=ACCENT)

        style.configure("Volume.Horizontal.TScale", background=BG_DARK,
                        troughcolor=CTRL_BG, sliderlength=12, slidercolor=TEXT_PRIMARY)

        style.configure("Status.TLabel", background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                        font=("Segoe UI", 9), padding=(6, 2))

        style.configure("Cover.TFrame", background=CTRL_BG, relief="solid",
                        borderwidth=1)

    # ── layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        # ── top section ──────────────────────────────────────────────
        top_frame = ttk.Frame(outer)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_frame.columnconfigure(1, weight=1)

        # cover art
        cover_frame = ttk.Frame(top_frame, width=120, height=120,
                                style="Cover.TFrame")
        cover_frame.grid(row=0, column=0, rowspan=3, padx=(0, 12), sticky="n")
        cover_frame.grid_propagate(False)

        self._cover_label = tk.Label(cover_frame, text="♫",
                                     font=("Segoe UI", 44),
                                     bg=CTRL_BG, fg=TEXT_SECONDARY)
        self._cover_label.place(relx=0.5, rely=0.5, anchor="center")

        # song info
        self._title_label = ttk.Label(top_frame, text="Sin canción",
                                      style="Title.TLabel")
        self._title_label.grid(row=0, column=1, sticky="w")

        self._artist_label = ttk.Label(top_frame, text="",
                                       style="Subtitle.TLabel")
        self._artist_label.grid(row=1, column=1, sticky="w", pady=(2, 0))

        self._album_label = ttk.Label(top_frame, text="",
                                      style="Subtitle.TLabel")
        self._album_label.grid(row=2, column=1, sticky="w")

        # progress bar
        progress_frame = ttk.Frame(top_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew",
                            pady=(12, 4))
        progress_frame.columnconfigure(0, weight=1)

        self._progress_slider = ttk.Scale(progress_frame, from_=0, to=100,
                                          variable=self._position_var,
                                          style="Progress.Horizontal.TScale",
                                          state="disabled")
        self._progress_slider.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._time_label = ttk.Label(progress_frame, text="0:00 / 0:00",
                                     style="Time.TLabel")
        self._time_label.grid(row=0, column=1)

        # controls
        ctrl_frame = ttk.Frame(top_frame)
        ctrl_frame.grid(row=4, column=0, columnspan=2, sticky="ew",
                        pady=(8, 0))

        buttons = [
            ("⏮", "prev", "Icon.TButton", self._cmd_previous, "Anterior"),
            ("▶", "play", "Play.TButton", self._cmd_play_pause, "Reproducir"),
            ("⏹", "stop", "Icon.TButton", self._cmd_stop, "Detener"),
            ("⏭", "next", "Icon.TButton", self._cmd_next, "Siguiente"),
        ]

        self._play_btn = None
        for i, (txt, key, stl, cmd, tip) in enumerate(buttons):
            btn = ttk.Button(ctrl_frame, text=txt, style=stl, command=cmd)
            btn.grid(row=0, column=i, padx=(0 if i == 0 else 2, 2))
            self._bind_tooltip(btn, tip)
            if key == "play":
                self._play_btn = btn

        ctrl_frame.columnconfigure(4, weight=1)

        vol_frame = ttk.Frame(ctrl_frame)
        vol_frame.grid(row=0, column=5, padx=(8, 0), sticky="e")

        vol_icon = ttk.Label(vol_frame, text="🔊", font=("Segoe UI", 12))
        vol_icon.grid(row=0, column=0, padx=(0, 4))

        vol_slider = ttk.Scale(vol_frame, from_=0, to=100,
                               variable=self._volume_var,
                               style="Volume.Horizontal.TScale",
                               command=self._on_volume_changed)
        vol_slider.grid(row=0, column=1)

        # ── playlist section ──────────────────────────────────────────
        playlist_outer = ttk.Frame(outer)
        playlist_outer.grid(row=1, column=0, sticky="nsew")
        playlist_outer.columnconfigure(0, weight=1)
        playlist_outer.rowconfigure(1, weight=1)

        # playlist header
        header = ttk.Frame(playlist_outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        header.columnconfigure(0, weight=1)

        header_label = ttk.Label(header, text="Lista de Reproducción",
                                 font=("Segoe UI", 11, "bold"))
        header_label.grid(row=0, column=0, sticky="w")

        header_buttons = [
            ("🔀", self._cmd_toggle_shuffle, "Aleatorio"),
            ("🔁", self._cmd_toggle_repeat, "Repetir"),
            ("📂", self._cmd_add_files, "Añadir archivos"),
            ("📁", self._cmd_add_folder, "Añadir carpeta"),
        ]
        for col, (text, cmd, tip) in enumerate(header_buttons, start=1):
            btn = ttk.Button(header, text=text, style="Icon.TButton",
                             command=cmd)
            btn.grid(row=0, column=col, padx=1)

        # playlist listbox
        list_frame = ttk.Frame(playlist_outer)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._playlist_box = tk.Listbox(list_frame,
                                        bg=CTRL_BG, fg=TEXT_PRIMARY,
                                        selectbackground=BG_LIGHT,
                                        selectforeground=TEXT_PRIMARY,
                                        borderwidth=0, highlightthickness=0,
                                        font=("Segoe UI", 10),
                                        activestyle="none")
        self._playlist_box.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self._playlist_box.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._playlist_box.configure(yscrollcommand=scrollbar.set)

        # ── status bar ───────────────────────────────────────────────
        status_frame = ttk.Frame(outer, style="Status.TFrame")
        status_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self._status_label = ttk.Label(status_frame, text="Listo",
                                       style="Status.TLabel")
        self._status_label.pack(fill="x")

        # ── empty playlist message ──────────────────────────────────
        self._empty_label = tk.Label(list_frame, text="Añade archivos o carpetas\ncon música FLAC",
                                     font=("Segoe UI", 11), bg=CTRL_BG, fg=TEXT_SECONDARY,
                                     justify="center")
        self._empty_label.place(relx=0.5, rely=0.5, anchor="center")

    # ── events ──────────────────────────────────────────────────────
    def _bind_events(self):
        self._progress_slider.bind("<ButtonPress-1>", self._on_seek_start)
        self._progress_slider.bind("<ButtonRelease-1>", self._on_seek_end)
        self._playlist_box.bind("<Double-Button-1>", self._on_playlist_double_click)
        self._playlist_box.bind("<Delete>", self._on_playlist_delete)
        self._playlist_box.bind("<Button-3>", self._on_playlist_right_click)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _bind_tooltip(self, widget, text):
        tip = None
        def enter(_):
            nonlocal tip
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(tip, text=text, bg="#333", fg="white",
                           font=("Segoe UI", 9), padx=6, pady=2)
            lbl.pack()
        def leave(_):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    # ── commands ─────────────────────────────────────────────────────
    def _cmd_play_pause(self):
        if self._current_song is None:
            if self.playlist.count > 0:
                s = self.playlist.play_song(0)
                if s:
                    self._load_and_play(s)
            return

        st = self.player.get_state()
        if st == Player.STATE_PLAYING:
            self.player.pause()
            self._play_btn.configure(text="▶")
            self._set_status(f"Pausado: {self._current_song.display_title}")
        else:
            self.player.play()
            self._play_btn.configure(text="⏸")
            self._set_status(f"Reproduciendo: {self._current_song.display_title}")

    def _cmd_stop(self):
        self.player.stop()
        self._play_btn.configure(text="▶")
        self._position_var.set(0)
        self._update_time_label()
        self._set_status("Detenido")

    def _cmd_next(self):
        if self.playlist.repeat == RepeatMode.ONE:
            if self._current_song:
                self.player.seek(0)
                self._position_var.set(0)
            return

        s = self.playlist.get_next()
        if s:
            self._load_and_play(s)
        else:
            self._cmd_stop()

    def _cmd_previous(self):
        pos = self._position_var.get()
        if pos > 3.0:
            self.player.seek(0)
            self._position_var.set(0)
            return

        s = self.playlist.get_previous()
        if s:
            self._load_and_play(s)
        else:
            self.player.seek(0)
            self._position_var.set(0)

    def _cmd_add_files(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar archivos FLAC",
            filetypes=[("Archivos FLAC", "*.flac"), ("Todos", "*.*")]
        )
        if not paths:
            return

        songs = read_songs(list(paths))
        self.playlist.add_songs(songs)
        self._refresh_playlist()
        self._set_status(f"{len(songs)} canción(es) añadida(s)")

        if self._current_song is None and self.playlist.count > 0:
            s = self.playlist.play_song(0)
            if s:
                self._show_song_info(s)

    def _cmd_add_folder(self):
        directory = filedialog.askdirectory(title="Seleccionar carpeta con FLAC")
        if not directory:
            return

        files = find_flac_files(directory)
        if not files:
            messagebox.showinfo("FlacPlayer", "No se encontraron archivos FLAC")
            return

        songs = read_songs(files)
        self.playlist.add_songs(songs)
        self._refresh_playlist()
        self._set_status(f"{len(songs)} canción(es) añadida(s) de {os.path.basename(directory)}")

        if self._current_song is None and self.playlist.count > 0:
            s = self.playlist.play_song(0)
            if s:
                self._show_song_info(s)

    def _cmd_toggle_shuffle(self):
        self.playlist.shuffle = not self.playlist.shuffle
        status = "activado" if self.playlist.shuffle else "desactivado"
        self._set_status(f"Modo aleatorio {status}")

    def _cmd_toggle_repeat(self):
        modes = [RepeatMode.NONE, RepeatMode.ALL, RepeatMode.ONE]
        current = modes.index(self.playlist.repeat) if self.playlist.repeat in modes else 0
        self.playlist.repeat = modes[(current + 1) % len(modes)]
        labels = {RepeatMode.NONE: "Sin repetición",
                  RepeatMode.ALL: "Repetir lista",
                  RepeatMode.ONE: "Repetir una canción"}
        self._set_status(labels[self.playlist.repeat])

    def _on_playlist_double_click(self, _event=None):
        sel = self._playlist_box.curselection()
        if not sel:
            return
        idx = sel[0]
        s = self.playlist.play_song(idx)
        if s:
            self._load_and_play(s)

    def _on_playlist_delete(self, _event=None):
        sel = self._playlist_box.curselection()
        if not sel:
            return
        idx = sel[0]
        song = self.playlist.songs[idx] if idx < self.playlist.count else None
        was_current = song is not None and song is self._current_song

        self.playlist.remove_song(idx)
        self._refresh_playlist()

        if was_current:
            if self.playlist.current_song:
                self._load_and_play(self.playlist.current_song)
            else:
                self._cmd_stop()
                self._current_song = None
                self._show_song_info(None)

        self._set_status("Canción eliminada")

    def _on_playlist_right_click(self, event):
        idx = self._playlist_box.nearest(event.y)
        if idx < 0 or idx >= self.playlist.count:
            return
        self._playlist_box.selection_clear(0, tk.END)
        self._playlist_box.selection_set(idx)

        menu = tk.Menu(self.root, tearoff=0, bg=CTRL_BG, fg=TEXT_PRIMARY,
                       activebackground=BG_LIGHT, activeforeground=TEXT_PRIMARY)
        menu.add_command(label="Reproducir", command=lambda: self._on_playlist_double_click())
        menu.add_command(label="Eliminar", command=self._on_playlist_delete)
        menu.add_separator()
        menu.add_command(label="Añadir archivos...", command=self._cmd_add_files)
        menu.add_command(label="Añadir carpeta...", command=self._cmd_add_folder)
        menu.tk_popup(event.x_root, event.y_root)

    def _on_volume_changed(self, _value=None):
        v = max(0, min(100, self._volume_var.get()))
        self.player.set_volume(v / 100.0)

    def _on_seek_start(self, _event=None):
        self._seeking = True

    def _on_seek_end(self, _event=None):
        self._seeking = False
        seconds = self._position_var.get()
        self.player.seek(seconds)

    def _on_song_ended(self):
        self.root.after(0, self._handle_song_end)

    def _handle_song_end(self):
        if self.playlist.repeat == RepeatMode.ONE and self._current_song:
            self.player.seek(0)
            self._position_var.set(0)
            self.player.play()
            return

        self._cmd_next()

    def _on_close(self):
        self.player.release()
        self.root.destroy()

    # ── internal helpers ─────────────────────────────────────────────
    def _load_and_play(self, song: Song):
        self._current_song = song
        self._show_song_info(song)

        self.player.load(song.path)
        self.player.play()
        self._play_btn.configure(text="⏸")

        dur = self.player.get_duration()
        self._progress_slider.configure(to=dur if dur > 0 else 100, state="normal")
        self._set_status(f"Reproduciendo: {song.display_title}")

    def _show_song_info(self, song: Song | None):
        if song is None:
            self._title_label.configure(text="Sin canción")
            self._artist_label.configure(text="")
            self._album_label.configure(text="")
            self._cover_label.configure(text="♫", font=("Segoe UI", 44))
            self._progress_slider.configure(state="disabled")
            return

        self._title_label.configure(text=song.display_title)
        self._artist_label.configure(text=song.display_artist)
        self._album_label.configure(text=song.display_album)

        if song.cover_path and os.path.exists(song.cover_path):
            try:
                img = Image.open(song.cover_path)
                img = img.resize((110, 110), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._cover_label.configure(image=photo, text="")
                self._cover_label.image = photo
            except Exception:
                self._cover_label.configure(text="♫", font=("Segoe UI", 44),
                                            image="")
        else:
            self._cover_label.configure(text="♫", font=("Segoe UI", 44),
                                        image="")

    def _refresh_playlist(self):
        self._playlist_box.delete(0, tk.END)

        if self.playlist.count == 0:
            self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return

        self._empty_label.place_forget()

        for song in self.playlist.songs:
            self._playlist_box.insert(tk.END, f"  {song.display_text}   {song.duration_str}")

    def _update_time_label(self):
        pos = self._position_var.get()
        dur = self.player.get_duration() if self._current_song else 0
        p_str = f"{int(pos // 60)}:{int(pos % 60):02d}"
        d_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur > 0 else "--:--"
        self._time_label.configure(text=f"{p_str} / {d_str}")

    def _update_position_loop(self):
        if not self._seeking:
            st = self.player.get_state()
            if st == Player.STATE_PLAYING:
                pos = self.player.get_position()
                self._position_var.set(pos)
                self._update_time_label()

        self.root.after(200, self._update_position_loop)

    def _set_status(self, text: str):
        self._status_label.configure(text=text)


def main():
    root = tk.Tk()
    root.iconbitmap(default="")
    app = FlacPlayerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
