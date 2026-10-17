"""Lista de reproducción con modos aleatorio y repetición."""

import random
from enum import Enum, auto

from song import Song


class RepeatMode(Enum):
    NONE = auto()
    ONE = auto()
    ALL = auto()


class Playlist:
    def __init__(self, rng: random.Random | None = None):
        self._songs: list[Song] = []
        self._current_index: int = -1
        self.shuffle: bool = False
        self.repeat: RepeatMode = RepeatMode.NONE
        self._random = rng or random.Random()
        # Índices ya reproducidos (para "anterior").
        self._history: list[int] = []
        # Índices pendientes del ciclo aleatorio actual.
        self._bag: list[int] = []

    # ── propiedades ───────────────────────────────────────────────────
    @property
    def songs(self) -> list[Song]:
        return self._songs

    @property
    def current_index(self) -> int:
        return self._current_index

    @current_index.setter
    def current_index(self, value: int):
        self._current_index = value

    @property
    def current_song(self) -> Song | None:
        if 0 <= self._current_index < len(self._songs):
            return self._songs[self._current_index]
        return None

    @property
    def count(self) -> int:
        return len(self._songs)

    # ── mutaciones ────────────────────────────────────────────────────
    def add_song(self, song: Song):
        self.add_songs([song])

    def add_songs(self, songs: list[Song]):
        self._songs.extend(songs)

    def insert_song(self, index: int, song: Song):
        index = max(0, min(index, len(self._songs)))
        self._songs.insert(index, song)

        def fix(i: int) -> int:
            return i + 1 if i >= index else i

        self._history = [fix(i) for i in self._history]
        self._bag = [fix(i) for i in self._bag]
        if index <= self._current_index:
            self._current_index += 1

    def remove_song(self, index: int) -> bool:
        if not (0 <= index < len(self._songs)):
            return False

        del self._songs[index]

        def fix(i: int) -> int:
            return i - 1 if i > index else i

        self._history = [fix(i) for i in self._history if i != index]
        self._bag = [fix(i) for i in self._bag if i != index]

        if index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index:
            self._current_index = min(self._current_index, len(self._songs) - 1)
        return True

    def remove_song_by_obj(self, song: Song) -> bool:
        try:
            return self.remove_song(self._songs.index(song))
        except ValueError:
            return False

    def clear(self):
        self._songs.clear()
        self._current_index = -1
        self._history.clear()
        self._bag.clear()

    # ── reproducción ──────────────────────────────────────────────────
    def play_song(self, index: int) -> Song | None:
        if not (0 <= index < len(self._songs)):
            return None
        self._current_index = index
        self._history.clear()
        self._bag.clear()
        return self._songs[index]

    def set_shuffle(self, enabled: bool):
        self.shuffle = enabled
        self._history.clear()
        self._bag.clear()

    def set_repeat(self, mode: RepeatMode):
        self.repeat = mode

    def get_next(self) -> Song | None:
        if not self._songs:
            return None

        if self.shuffle:
            return self._next_shuffled()

        nxt = self._current_index + 1
        if nxt >= len(self._songs):
            if self.repeat == RepeatMode.ALL:
                nxt = 0
            else:
                return None
        self._push_history()
        self._current_index = nxt
        return self._songs[nxt]

    def get_previous(self) -> Song | None:
        if not self._songs:
            return None

        if self._history:
            previous = self._history.pop()
            if self.shuffle and 0 <= self._current_index < len(self._songs):
                # Permitir volver hacia delante con "siguiente".
                self._bag.insert(0, self._current_index)
            self._current_index = previous
            return self._songs[previous]

        if self.shuffle:
            return self.current_song

        prev = self._current_index - 1
        if prev < 0:
            if self.repeat == RepeatMode.ALL:
                prev = len(self._songs) - 1
            else:
                return None
        self._current_index = prev
        return self._songs[prev]

    # ── internos ──────────────────────────────────────────────────────
    def _push_history(self):
        if 0 <= self._current_index < len(self._songs):
            self._history.append(self._current_index)

    def _next_shuffled(self) -> Song:
        if not self._bag:
            candidates = [i for i in range(len(self._songs)) if i != self._current_index]
            self._random.shuffle(candidates)
            if not candidates:  # lista con una sola canción
                candidates = [self._current_index]
            self._bag = candidates

        self._push_history()
        self._current_index = self._bag.pop(0)
        return self._songs[self._current_index]
