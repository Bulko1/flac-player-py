import os
import tempfile
from datetime import timedelta
from pathlib import Path

import mutagen
from mutagen.flac import FLAC, Picture

from song import Song


def read_song(file_path: str) -> Song:
    song = Song(path=file_path)
    try:
        audio = FLAC(file_path)
        song.title = str(audio.get("title", [""])[0]) if audio.get("title") else ""
        song.artist = str(audio.get("artist", [""])[0]) if audio.get("artist") else ""
        song.album = str(audio.get("album", [""])[0]) if audio.get("album") else ""

        if audio.info and audio.info.length > 0:
            song.duration = timedelta(seconds=audio.info.length)

        cover = extract_cover(audio, file_path)
        if cover:
            song.cover_path = cover
    except Exception:
        pass
    return song


def read_songs(file_paths: list[str]) -> list[Song]:
    return [read_song(p) for p in file_paths]


def find_flac_files(directory: str) -> list[str]:
    result = []
    try:
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".flac"):
                    result.append(os.path.join(root, f))
    except Exception:
        pass
    return result


def extract_cover(audio: FLAC, file_path: str) -> str | None:
    try:
        pictures: list[Picture] = audio.get("metadata_block_picture", [])
        if not pictures:
            return None

        cover_dir = os.path.join(tempfile.gettempdir(), "FlacPlayerPy", "covers")
        os.makedirs(cover_dir, exist_ok=True)

        stem = Path(file_path).stem
        cover_path = os.path.join(cover_dir, f"{stem}.jpg")

        if not os.path.exists(cover_path):
            with open(cover_path, "wb") as f:
                f.write(pictures[0].data)

        return cover_path
    except Exception:
        return None
