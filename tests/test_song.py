from datetime import timedelta

from song import Song


def test_display_fallbacks():
    song = Song(path="/music/track.flac")
    assert song.display_title == "track"
    assert song.display_artist == "Artista desconocido"
    assert song.display_album == "Álbum desconocido"
    assert song.display_text == "Artista desconocido - track"


def test_display_uses_metadata():
    song = Song(path="/music/a.flac", title="T", artist="A", album="Al")
    assert song.display_title == "T"
    assert song.display_artist == "A"
    assert song.display_album == "Al"


def test_duration_str():
    assert Song(path="x", duration=timedelta(seconds=0)).duration_str == "--:--"
    assert Song(path="x", duration=timedelta(seconds=75)).duration_str == "1:15"
    assert Song(path="x", duration=timedelta(seconds=600)).duration_str == "10:00"


def test_bitrate_str():
    assert Song(path="x").bitrate_str == "-- kbps"
    assert Song(path="x", bitrate=18_000).bitrate_str == "18 kbps"
    assert Song(path="x", bitrate=923_400).bitrate_str == "923 kbps"
    assert Song(path="x", bitrate=1_411_200).bitrate_str == "1411 kbps"
