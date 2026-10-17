import os
from pathlib import Path

import pytest

import metadata_service
from flac_meta import PICTURE_TYPE_FRONT_COVER, FlacError, Picture, read_flac_metadata
from metadata_service import export_cover, find_flac_files, iter_songs, read_song

# Tags Vorbis del fixture ``tests/assets/tagged.flac``.
FIXTURE_TITLE = "Canción de prueba"
FIXTURE_ARTIST = "Artista de prueba"
FIXTURE_ALBUM = "Álbum de prueba"


def _synchsafe(value: int) -> bytes:
    return bytes((value >> shift) & 0x7F for shift in (21, 14, 7, 0))


def _prepend_id3v2(flac_path, flags: int = 0x00, payload: bytes = b"\x00" * 32) -> str:
    """Copia el FLAC con una etiqueta ID3v2 delante (como algunos etiquetadores)."""
    data = Path(flac_path).read_bytes()
    tag = b"ID3\x04\x00" + bytes([flags]) + _synchsafe(len(payload)) + payload
    if flags & 0x10:  # pie de etiqueta opcional (ID3v2.4)
        tag += b"\x00" * 10
    destination = Path(flac_path).with_name("with_id3.flac")
    destination.write_bytes(tag + data)
    return str(destination)


def _picture(mime="image/png", data=b"\x89PNG fake") -> Picture:
    return Picture(mime=mime, data=data)


def _append_metadata_block(path, block_type: int, body: bytes) -> None:
    """Inserta un bloque de metadatos al final de la sección de metadata.

    El bloque insertado pasa a ser el último (el flag se mueve desde el que lo
    era), igual que haría un etiquetador real.
    """
    with open(path, "rb") as fh:
        raw = bytearray(fh.read())
    assert raw[:4] == b"fLaC"
    pos = 4
    while True:
        header = raw[pos]
        size = int.from_bytes(raw[pos + 1 : pos + 4], "big")
        raw[pos] &= 0x7F
        pos += 4 + size
        if header & 0x80:
            break
    raw[pos:pos] = bytes([0x80 | block_type]) + len(body).to_bytes(3, "big") + body
    with open(path, "wb") as fh:
        fh.write(raw)


def _picture_body(
    mime: bytes,
    data: bytes,
    pic_type: int = PICTURE_TYPE_FRONT_COVER,
    declared_size: int | None = None,
) -> bytes:
    """Cuerpo de un bloque PICTURE (big-endian) con datos de imagen."""
    body = pic_type.to_bytes(4, "big")
    body += len(mime).to_bytes(4, "big") + mime
    body += (0).to_bytes(4, "big")  # descripción vacía
    body += b"\x00" * 16  # ancho, alto, profundidad y colores
    size = len(data) if declared_size is None else declared_size
    body += size.to_bytes(4, "big") + data
    return body


def _insert_picture(path, mime: bytes, data: bytes, pic_type: int = PICTURE_TYPE_FRONT_COVER) -> None:
    _append_metadata_block(path, 6, _picture_body(mime, data, pic_type))


# ── export_cover ──────────────────────────────────────────────────────
def test_export_cover_uses_hash_and_real_extension(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = str(tmp_path / "song.flac")
    cover = export_cover(_picture("image/png"), path)

    assert cover is not None
    assert cover.endswith(".png")
    assert os.path.exists(cover)
    # El nombre del archivo no depende del stem original.
    assert os.path.basename(cover) != "song.png"


def test_export_cover_no_collision_same_stem(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    a = export_cover(_picture("image/jpeg", b"aaa"), str(tmp_path / "d1" / "x.flac"))
    b = export_cover(_picture("image/jpeg", b"bbb"), str(tmp_path / "d2" / "x.flac"))
    assert a != b


def test_export_cover_reuses_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = str(tmp_path / "song.flac")
    first = export_cover(_picture("image/jpeg", b"data"), path)
    mtime = os.path.getmtime(first)
    second = export_cover(_picture("image/jpeg", b"other"), path)
    assert first == second
    assert os.path.getmtime(second) == mtime


# ── read_song ─────────────────────────────────────────────────────────
def test_read_song_reads_tags(tagged_flac):
    song = read_song(tagged_flac)
    assert (song.title, song.artist, song.album) == (FIXTURE_TITLE, FIXTURE_ARTIST, FIXTURE_ALBUM)


def test_read_song_reads_duration(flac_file):
    song = read_song(flac_file)
    assert song.path == flac_file
    assert 0.9 < song.duration.total_seconds() < 1.1
    assert song.cover_path is None


def test_read_song_reads_bitrate(tagged_flac):
    song = read_song(tagged_flac)
    assert song.bitrate > 0
    assert song.bitrate_str.endswith(" kbps")


def test_read_song_extracts_cover(tagged_flac, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    png = b"\x89PNG\r\n\x1a\n" + b"datos de imagen"
    _insert_picture(tagged_flac, b"image/png", png)

    song = read_song(tagged_flac)
    assert song.title == FIXTURE_TITLE
    assert song.cover_path is not None
    assert song.cover_path.endswith(".png")
    with open(song.cover_path, "rb") as fh:
        assert fh.read() == png


def test_read_song_prefers_front_cover(tagged_flac, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _insert_picture(tagged_flac, b"image/jpeg", b"contraportada", pic_type=0)
    _insert_picture(tagged_flac, b"image/png", b"portada", pic_type=3)

    song = read_song(tagged_flac)
    assert song.cover_path.endswith(".png")
    with open(song.cover_path, "rb") as fh:
        assert fh.read() == b"portada"


def test_read_song_missing_file_returns_song():
    song = read_song("/does/not/exist.flac")
    assert song.title == ""
    assert song.duration.total_seconds() == 0


def test_read_song_invalid_file_returns_defaults(tmp_path):
    path = tmp_path / "broken.flac"
    path.write_bytes(b"\x00" * 32)

    song = read_song(str(path))
    assert song.title == ""
    assert song.artist == ""
    assert song.duration.total_seconds() == 0
    assert song.bitrate == 0
    assert song.cover_path is None


def test_read_song_reuses_exported_cover_without_reading_picture(
    tagged_flac, tmp_path, monkeypatch
):
    """Con la carátula ya exportada no se debe leer el bloque PICTURE."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _insert_picture(tagged_flac, b"image/png", b"portada")

    first = read_song(tagged_flac)
    assert first.cover_path is not None

    def fail_parse(_body):
        raise AssertionError("no debería leer el bloque PICTURE")

    monkeypatch.setattr("flac_meta._parse_picture", fail_parse)

    second = read_song(tagged_flac)
    assert second.title == FIXTURE_TITLE
    assert second.cover_path == first.cover_path


def test_iter_songs_batches(tagged_flac, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    batches = list(iter_songs([tagged_flac] * 5, batch_size=2))
    assert [len(batch) for batch in batches] == [2, 2, 1]


# ── parser (flac_meta) ────────────────────────────────────────────────
def test_read_flac_metadata_parses_tags_and_pictures(tagged_flac):
    _insert_picture(tagged_flac, b"image/gif", b"gif-data", pic_type=1)

    meta = read_flac_metadata(tagged_flac)
    assert (meta.first("title"), meta.first("artist"), meta.first("album")) == (
        FIXTURE_TITLE,
        FIXTURE_ARTIST,
        FIXTURE_ALBUM,
    )
    assert meta.first("genre") == ""
    assert meta.duration is not None
    assert 1.9 < meta.duration < 2.1
    assert len(meta.pictures) == 1
    assert meta.pictures[0].mime == "image/gif"
    assert meta.pictures[0].data == b"gif-data"
    assert meta.cover is meta.pictures[0]


def test_read_flac_metadata_computes_average_bitrate(tagged_flac):
    meta = read_flac_metadata(tagged_flac)
    assert meta.duration is not None
    assert meta.bitrate is not None
    # Positivo y por debajo del nominal sin comprimir (mono 16 bits a 8 kHz).
    assert 0 < meta.bitrate < 8000 * 16


def test_read_flac_metadata_bitrate_ignores_pictures(tagged_flac):
    before = read_flac_metadata(tagged_flac).bitrate
    _insert_picture(tagged_flac, b"image/png", b"x" * 50_000)
    after = read_flac_metadata(tagged_flac).bitrate
    assert before is not None
    assert after == pytest.approx(before)


def test_read_flac_metadata_rejects_non_flac(tmp_path):
    path = tmp_path / "fake.flac"
    path.write_bytes(b"RIFF esto no es flac")

    with pytest.raises(FlacError):
        read_flac_metadata(str(path))


@pytest.mark.parametrize("flags", [0x00, 0x10])
def test_read_flac_metadata_skips_id3v2_prefix(tagged_flac, flags):
    path = _prepend_id3v2(tagged_flac, flags=flags)

    meta = read_flac_metadata(path)
    assert meta.first("title") == FIXTURE_TITLE
    assert meta.duration is not None
    assert 1.9 < meta.duration < 2.1


def test_read_flac_metadata_can_skip_pictures(tagged_flac):
    _insert_picture(tagged_flac, b"image/png", b"portada")

    meta = read_flac_metadata(tagged_flac, skip_pictures=True)
    assert meta.pictures == []
    assert meta.first("title") == FIXTURE_TITLE
    assert meta.duration is not None


def test_read_flac_metadata_ignores_truncated_picture(tagged_flac):
    _append_metadata_block(tagged_flac, 6, _picture_body(b"image/png", b"corta", declared_size=100))

    meta = read_flac_metadata(tagged_flac)
    assert meta.pictures == []
    assert meta.first("title") == FIXTURE_TITLE


# ── utilidades del servicio ───────────────────────────────────────────
def test_find_flac_files_recurses_and_sorts(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.flac").write_bytes(b"")
    (tmp_path / "sub" / "b.flac").write_bytes(b"")
    (tmp_path / "c.mp3").write_bytes(b"")

    found = find_flac_files(str(tmp_path))
    assert found == sorted(found)
    assert len(found) == 2
    assert all(p.lower().endswith(".flac") for p in found)


def test_cover_dir_uses_localappdata(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert metadata_service.cover_dir().startswith(str(tmp_path))
