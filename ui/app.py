"""Controlador principal de la aplicación (une modelo y vistas)."""

import logging
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import storage
from metadata_service import find_flac_files, iter_songs
from player import Player
from playlist import Playlist, RepeatMode
from song import Song
from ui import theme
from ui.playlist_panel import PlaylistPanel
from ui.track_panel import TrackPanel
from ui.transport_panel import TransportPanel

log = logging.getLogger(__name__)

SEEK_STEP = 5.0


class FlacPlayerUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FlacPlayer")
        self.root.geometry("560x740")
        self.root.configure(bg=theme.BG_DARK)

        self.player = Player()
        self.playlist = Playlist()

        self._current_song: Song | None = None
        self._result_queue: queue.Queue = queue.Queue()

        theme.setup_styles()

        self._container = ttk.Frame(self.root, padding=10)

        self.transport_panel = TransportPanel(self._container, {
            "play_pause": self._cmd_play_pause,
            "stop": self._cmd_stop,
            "next": self._cmd_next,
            "previous": self._cmd_previous,
            "seek": self._on_seek,
            "volume": self._on_volume,
        })
        self.track_panel = TrackPanel(self._container)
        self.playlist_panel = PlaylistPanel(self._container, {
            "activate": self._cmd_play_index,
            "delete": self._cmd_delete_index,
            "play_next": self._cmd_play_next,
            "add_files": self._cmd_add_files,
            "add_folder": self._cmd_add_folder,
            "toggle_shuffle": self._cmd_toggle_shuffle,
            "toggle_repeat": self._cmd_toggle_repeat,
            "toggle_theme": self._cmd_toggle_theme,
            "clear": self._cmd_clear,
        })

        self._build_layout()
        self._bind_events()
        self._apply_sizing()

        self._restore_state()
        self._tick()

    # ── layout ────────────────────────────────────────────────────────
    def _build_layout(self):
        self._container.pack(fill="both", expand=True)

        # Orden vertical: lista arriba, controles al medio, detalle abajo.
        self.playlist_panel.pack(fill="both", expand=True, pady=(0, 8))
        self.transport_panel.pack(fill="x", pady=(0, 8))
        self.track_panel.pack(fill="x")

        status_frame = ttk.Frame(self._container, style="Status.TFrame")
        status_frame.pack(fill="x", pady=(8, 0))
        self._status_label = ttk.Label(status_frame, text="Listo", style="Status.TLabel")
        self._status_label.pack(fill="x")

    def _apply_sizing(self):
        """Impide que la ventana encoja por debajo del contenido (anti-recorte)."""
        self.root.update_idletasks()
        width = max(460, min(self.root.winfo_reqwidth(), 680))
        height = max(580, min(self.root.winfo_reqheight(), 820))
        self.root.minsize(width, height)

    # ── eventos ───────────────────────────────────────────────────────
    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<space>", self._key_play_pause)
        self.root.bind("<Left>", lambda e: self._key_seek(-SEEK_STEP))
        self.root.bind("<Right>", lambda e: self._key_seek(SEEK_STEP))
        self.root.bind("<Control-Left>", lambda e: self._key_cmd(self._cmd_previous))
        self.root.bind("<Control-Right>", lambda e: self._key_cmd(self._cmd_next))
        self.root.bind("<Control-o>", lambda e: self._key_cmd(self._cmd_add_files))
        self.root.bind("<Control-f>", lambda e: self._key_cmd(self.playlist_panel.focus_filter))
        self.root.bind("<Control-s>", lambda e: self._key_cmd(self._cmd_toggle_shuffle))
        self.root.bind("<Control-t>", lambda e: self._key_cmd(self._cmd_toggle_theme))

    def _filter_focused(self) -> bool:
        return self.root.focus_get() is self.playlist_panel._filter_entry

    def _key_cmd(self, func):
        func()
        return "break"

    def _key_play_pause(self, _event=None):
        if self._filter_focused():
            return None
        self._cmd_play_pause()
        return "break"

    def _key_seek(self, delta: float):
        if self._filter_focused() or self._current_song is None:
            return None
        new_pos = max(0.0, self.transport_panel.position() + delta)
        self._on_seek(new_pos)
        return "break"

    # ── comandos de transporte ────────────────────────────────────────
    def _cmd_play_pause(self):
        if self._current_song is None:
            if self.playlist.count > 0:
                song = self.playlist.play_song(0)
                if song:
                    self._load_and_play(song)
            return

        if self.player.get_state() == Player.STATE_PLAYING:
            self.player.pause()
            self.transport_panel.set_playing(False)
            self._set_status(f"Pausado: {self._current_song.display_title}")
        else:
            self.player.play()
            self.transport_panel.set_playing(True)
            self._set_status(f"Reproduciendo: {self._current_song.display_title}")

    def _cmd_stop(self):
        self.player.stop()
        self.transport_panel.set_playing(False)
        self.transport_panel.set_position(0.0, self.player.get_duration())
        self._set_status("Detenido")

    def _cmd_next(self):
        if self.playlist.repeat == RepeatMode.ONE and self._current_song:
            self.player.seek(0)
            self.transport_panel.set_position(0.0)
            return
        song = self.playlist.get_next()
        if song:
            self._load_and_play(song)
        else:
            self._cmd_stop()

    def _cmd_previous(self):
        if self.transport_panel.position() > 3.0:
            self.player.seek(0)
            self.transport_panel.set_position(0.0)
            return
        song = self.playlist.get_previous()
        if song:
            self._load_and_play(song)
        else:
            self.player.seek(0)
            self.transport_panel.set_position(0.0)

    def _cmd_play_index(self, index: int):
        song = self.playlist.play_song(index)
        if song:
            self._load_and_play(song)

    def _cmd_play_next(self, index: int):
        if not (0 <= index < self.playlist.count):
            return
        song = self.playlist.songs[index]
        insert_at = self.playlist.current_index + 1
        if index < insert_at:
            insert_at -= 1
        self.playlist.insert_song(insert_at, Song(**vars(song)))
        self.playlist_panel.set_songs(self.playlist.songs)
        self._set_status(f"A continuación: {song.display_title}")

    def _cmd_delete_index(self, index: int):
        song = self.playlist.songs[index] if index < self.playlist.count else None
        was_current = song is not None and song is self._current_song
        self.playlist.remove_song(index)
        self.playlist_panel.set_songs(self.playlist.songs)

        if was_current:
            if self.playlist.current_song:
                self._load_and_play(self.playlist.current_song)
            else:
                self._cmd_stop()
                self._current_song = None
                self.track_panel.clear_song()
                self.transport_panel.reset()
        self._set_status("Canción eliminada")

    def _cmd_clear(self):
        self._cmd_stop()
        self.playlist.clear()
        self._current_song = None
        self.track_panel.clear_song()
        self.transport_panel.reset()
        self.playlist_panel.set_songs(self.playlist.songs)
        self._set_status("Lista vaciada")

    def _cmd_toggle_shuffle(self):
        self.playlist.set_shuffle(not self.playlist.shuffle)
        self.playlist_panel.set_shuffle(self.playlist.shuffle)
        state = "activado" if self.playlist.shuffle else "desactivado"
        self._set_status(f"Modo aleatorio {state}")

    def _cmd_toggle_repeat(self):
        modes = [RepeatMode.NONE, RepeatMode.ALL, RepeatMode.ONE]
        current = modes.index(self.playlist.repeat)
        self.playlist.set_repeat(modes[(current + 1) % len(modes)])
        self.playlist_panel.set_repeat(self.playlist.repeat)
        labels = {RepeatMode.NONE: "Sin repetición",
                  RepeatMode.ALL: "Repetir lista",
                  RepeatMode.ONE: "Repetir una canción"}
        self._set_status(labels[self.playlist.repeat])

    def _cmd_toggle_theme(self):
        name = theme.toggle()
        self._apply_theme(name)
        self._set_status("Tema claro" if name == "light" else "Tema oscuro")

    def _apply_theme(self, name: str):
        theme.set_palette(name)
        theme.setup_styles()
        self.root.configure(bg=theme.BG_DARK)
        self.playlist_panel.apply_theme()
        self.playlist_panel.set_theme_icon(theme.current_palette())
        self.track_panel.apply_theme()

    # ── añadir pistas ─────────────────────────────────────────────────
    def _cmd_add_files(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar archivos FLAC",
            filetypes=[("Archivos FLAC", "*.flac"), ("Todos", "*.*")],
        )
        if paths:
            self._scan(list(paths), f"{len(paths)} archivo(s)")

    def _cmd_add_folder(self):
        directory = filedialog.askdirectory(title="Seleccionar carpeta con FLAC")
        if not directory:
            return
        self.playlist_panel.set_busy(True)
        self._set_status(f"Buscando archivos FLAC en {directory}...")
        self._start_scan(directory, lambda: find_flac_files(directory))

    def _scan(self, paths: list[str], label: str):
        """Escanea rutas ya conocidas (archivos sueltos o estado guardado)."""
        if not paths:
            return
        self.playlist_panel.set_busy(True)
        self._set_status(f"Leyendo {len(paths)} archivo(s)...")
        self._start_scan(label, lambda: paths)

    def _start_scan(self, label: str, resolve_paths):
        """Busca y lee metadatos en segundo plano, enviando lotes a la UI."""

        def worker():
            try:
                paths = resolve_paths()
                if not paths:
                    self._result_queue.put(("empty", [], label))
                    return
                total = len(paths)
                loaded = 0
                for batch in iter_songs(paths):
                    loaded += len(batch)
                    self._result_queue.put(("songs", batch, (label, loaded, total)))
            except Exception:
                log.warning("Fallo al escanear %s", label, exc_info=True)
            finally:
                self._result_queue.put(("done", [], label))

        threading.Thread(target=worker, name="flac-scanner", daemon=True).start()

    # ── reproducción ──────────────────────────────────────────────────
    def _load_and_play(self, song: Song):
        if not self.player.load(song.path):
            self._set_status(f"No se pudo cargar: {song.display_title}")
            return
        self._current_song = song
        self.track_panel.set_song(song)
        self.player.set_volume(self.transport_panel.volume() / 100.0)
        if not self.player.play():
            self.transport_panel.set_playing(False)
            self._set_status(f"No se pudo reproducir: {song.display_title}")
            return
        self.transport_panel.set_playing(True)
        self.transport_panel.set_duration(self.player.get_duration())
        self.transport_panel.set_position(0.0, self.player.get_duration())
        self.playlist_panel.highlight(self.playlist.current_index)
        self._set_status(f"Reproduciendo: {song.display_title}")

    def _on_seek(self, seconds: float):
        self.player.seek(seconds)
        self.transport_panel.set_position(seconds, self.player.get_duration())

    def _on_volume(self, value: float):
        self.player.set_volume(value / 100.0)

    def _handle_song_end(self):
        if self.playlist.repeat == RepeatMode.ONE and self._current_song:
            self.player.seek(0)
            self.player.play()
            self.transport_panel.set_position(0.0, self.player.get_duration())
            return
        self._cmd_next()

    # ── bucle principal ───────────────────────────────────────────────
    def _tick(self):
        self._drain_results()

        underruns = self.player.take_underruns()
        if underruns:
            log.warning("Cortes de audio por buffer vacío: %d", underruns)

        if self.player.song_ended():
            self.player.acknowledge_end()
            self._handle_song_end()

        state = self.player.get_state()
        if state == Player.STATE_PLAYING:
            self.transport_panel.set_position(self.player.get_position(),
                                           self.player.get_duration())
            interval = 100
        else:
            interval = 300

        self.root.after(interval, self._tick)

    def _drain_results(self):
        songs: list[Song] = []
        progress = None
        finished = False
        empty = False
        while True:
            try:
                kind, payload, info = self._result_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "songs":
                songs.extend(payload)
                progress = info
            elif kind == "empty":
                empty = True
            elif kind == "done":
                finished = True

        # Un solo repintado por tick aunque lleguen varios lotes seguidos.
        if songs:
            self.playlist.add_songs(songs)
            self.playlist_panel.set_songs(self.playlist.songs)

        if progress is not None:
            label, loaded, total = progress
            if loaded < total:
                self._set_status(f"Leyendo {loaded}/{total}... ({label})")
            else:
                self._set_status(f"{total} canción(es) añadida(s) ({label})")

        if empty:
            self._set_status("Sin archivos FLAC")
            messagebox.showinfo("FlacPlayer", "No se encontraron archivos FLAC")

        if finished or empty:
            self.playlist_panel.set_busy(False)

    # ── persistencia ──────────────────────────────────────────────────
    def _restore_state(self):
        state = storage.load_state()
        self._apply_theme(state.get("theme") or theme.DEFAULT_PALETTE)
        if not state:
            return

        self.transport_panel.set_volume(float(state.get("volume", 80.0)))
        if state.get("shuffle"):
            self.playlist.set_shuffle(True)
            self.playlist_panel.set_shuffle(True)

        try:
            self.playlist.set_repeat(RepeatMode[state.get("repeat", "NONE")])
        except KeyError:
            pass
        self.playlist_panel.set_repeat(self.playlist.repeat)

        paths = [p for p in state.get("paths", []) if p]
        if paths:
            self._scan(paths, "estado anterior")

    def _save_state(self):
        storage.save_state({
            "paths": [s.path for s in self.playlist.songs],
            "current_index": self.playlist.current_index,
            "shuffle": self.playlist.shuffle,
            "repeat": self.playlist.repeat.name,
            "theme": theme.current_palette(),
            "volume": self.transport_panel.volume(),
        })

    # ── cierre ────────────────────────────────────────────────────────
    def _on_close(self):
        self._save_state()
        self.player.release()
        self.root.destroy()

    def _set_status(self, text: str):
        self._status_label.configure(text=text)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        log.debug("No se pudo establecer el icono de la ventana")
    FlacPlayerUI(root)
    root.mainloop()
