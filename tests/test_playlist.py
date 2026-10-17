import random

from playlist import Playlist, RepeatMode
from song import Song


def make_songs(n: int) -> list[Song]:
    return [Song(path=f"/m/{i}.flac", title=f"T{i}") for i in range(n)]


def test_next_sequential_stops_at_end():
    pl = Playlist()
    pl.add_songs(make_songs(3))
    pl.play_song(0)
    assert pl.get_next().title == "T1"
    assert pl.get_next().title == "T2"
    assert pl.get_next() is None


def test_repeat_all_wraps():
    pl = Playlist()
    pl.add_songs(make_songs(2))
    pl.set_repeat(RepeatMode.ALL)
    pl.play_song(0)
    assert pl.get_next().title == "T1"
    assert pl.get_next().title == "T0"


def test_previous_returns_last_played():
    pl = Playlist()
    pl.add_songs(make_songs(3))
    pl.play_song(0)
    pl.get_next()  # -> T1
    pl.get_next()  # -> T2
    assert pl.get_previous().title == "T1"
    assert pl.get_previous().title == "T0"


def test_shuffle_never_repeats_immediately():
    pl = Playlist(random.Random(42))
    pl.add_songs(make_songs(6))
    pl.set_shuffle(True)
    pl.play_song(0)
    previous = pl.current_index
    for _ in range(60):
        song = pl.get_next()
        assert song is not None
        assert pl.current_index != previous
        previous = pl.current_index


def test_shuffle_previous_walks_history():
    pl = Playlist(random.Random(7))
    pl.add_songs(make_songs(5))
    pl.set_shuffle(True)
    pl.play_song(0)
    first = pl.get_next()
    pl.get_next()
    assert pl.get_previous() is first
    assert pl.get_previous().title == "T0"


def test_remove_adjusts_current_index():
    pl = Playlist()
    pl.add_songs(make_songs(4))
    pl.play_song(2)
    pl.remove_song(0)
    assert pl.current_index == 1
    assert pl.current_song.title == "T2"


def test_remove_current_clamps():
    pl = Playlist()
    pl.add_songs(make_songs(2))
    pl.play_song(1)
    pl.remove_song(1)
    assert pl.count == 1
    assert pl.current_index == 0


def test_insert_song():
    pl = Playlist()
    pl.add_songs(make_songs(2))
    pl.play_song(0)
    pl.insert_song(1, Song(path="/m/x.flac", title="X"))
    assert [s.title for s in pl.songs] == ["T0", "X", "T1"]
    assert pl.current_index == 0
