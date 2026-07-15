import random
from enum import Enum, auto
from song import Song


class RepeatMode(Enum):
    NONE = auto()
    ONE = auto()
    ALL = auto()


class Playlist:
    def __init__(self):
        self._songs: list[Song] = []
        self._current_index: int = -1
        self.shuffle: bool = False
        self.repeat: RepeatMode = RepeatMode.NONE
        self._random = random.Random()

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

    def add_song(self, song: Song):
        self._songs.append(song)

    def add_songs(self, songs: list[Song]):
        self._songs.extend(songs)

    def remove_song(self, index: int) -> bool:
        if index < 0 or index >= len(self._songs):
            return False
        del self._songs[index]
        if self._current_index >= len(self._songs):
            self._current_index = len(self._songs) - 1
        elif index < self._current_index:
            self._current_index -= 1
        return True

    def remove_song_by_obj(self, song: Song) -> bool:
        try:
            idx = self._songs.index(song)
            return self.remove_song(idx)
        except ValueError:
            return False

    def clear(self):
        self._songs.clear()
        self._current_index = -1

    def play_song(self, index: int) -> Song | None:
        if index < 0 or index >= len(self._songs):
            return None
        self._current_index = index
        return self._songs[index]

    def get_next(self) -> Song | None:
        if not self._songs:
            return None
        if self.shuffle:
            self._current_index = self._random.randint(0, len(self._songs) - 1)
        else:
            nxt = self._current_index + 1
            if nxt >= len(self._songs):
                if self.repeat == RepeatMode.ALL:
                    nxt = 0
                else:
                    return None
            self._current_index = nxt
        return self._songs[self._current_index]

    def get_previous(self) -> Song | None:
        if not self._songs:
            return None
        if self.shuffle:
            self._current_index = self._random.randint(0, len(self._songs) - 1)
        else:
            prev = self._current_index - 1
            if prev < 0:
                if self.repeat == RepeatMode.ALL:
                    prev = len(self._songs) - 1
                else:
                    return None
            self._current_index = prev
        return self._songs[self._current_index]
