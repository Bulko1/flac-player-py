"""Lectura de metadatos y extracción de carátulas de archivos FLAC.

Usa el parser propio de ``flac_meta`` (sin dependencias de terceros).
"""

import hashlib
import logging
import os
from collections.abc import Iterator
from datetime import timedelta

from flac_meta import Picture, read_flac_metadata
from song import Song

log = logging.getLogger(__name__)

#: Tamaño de lote al escanear muchas pistas (para ir mostrando progreso).
BATCH_SIZE = 200

_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
}

#: Extensiones posibles de una carátula exportada, en orden de búsqueda.
_COVER_EXTS = tuple(dict.fromkeys([*_MIME_EXT.values(), ".img"]))


def cover_dir() -> str:
    """Directorio de carátulas extraídas, en datos locales del usuario."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "FlacPlayer", "covers")
    os.makedirs(path, exist_ok=True)
    return path


def export_cover(picture: Picture, file_path: str) -> str | None:
    """Escribe la carátula en disco (una vez) y devuelve su ruta.

    El nombre se deriva del hash del path completo para evitar colisiones entre
    archivos con el mismo nombre en carpetas distintas, y conserva la
    extensión real del tipo MIME.
    """
    try:
        ext = _MIME_EXT.get((picture.mime or "").lower(), ".img")
        cover_path = os.path.join(cover_dir(), _cover_digest(file_path) + ext)
        if not os.path.exists(cover_path):
            with open(cover_path, "wb") as fh:
                fh.write(picture.data)
        return cover_path
    except Exception:
        log.warning("No se pudo extraer la carátula de %s", file_path, exc_info=True)
        return None


def _cover_digest(file_path: str) -> str:
    """Nombre (sin extensión) de la carátula exportada para ``file_path``."""
    return hashlib.sha1(os.fsencode(os.path.abspath(file_path))).hexdigest()


def find_cover(file_path: str) -> str | None:
    """Ruta de la carátula ya exportada para ``file_path``, si existe."""
    directory = cover_dir()
    digest = _cover_digest(file_path)
    for ext in _COVER_EXTS:
        path = os.path.join(directory, digest + ext)
        if os.path.exists(path):
            return path
    return None


class CoverCache:
    """Índice en memoria de las carátulas exportadas.

    Evita varios ``os.path.exists`` por archivo durante el escaneo: los nombres
    se listan una sola vez y las carátulas nuevas se añaden al índice.
    """

    def __init__(self) -> None:
        self._dir = cover_dir()
        self._names: set[str] = set()
        try:
            with os.scandir(self._dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        self._names.add(entry.name)
        except OSError:
            log.debug("No se pudo indexar el directorio de carátulas", exc_info=True)

    def find(self, file_path: str) -> str | None:
        digest = _cover_digest(file_path)
        for ext in _COVER_EXTS:
            name = digest + ext
            if name in self._names:
                return os.path.join(self._dir, name)
        return None

    def add(self, cover_path: str) -> None:
        self._names.add(os.path.basename(cover_path))


def read_song(file_path: str, cover_cache: CoverCache | None = None) -> Song:
    song = Song(path=file_path)
    cached_cover = cover_cache.find(file_path) if cover_cache else find_cover(file_path)
    song.cover_path = cached_cover
    try:
        # Si la carátula ya está exportada no hace falta leer el bloque PICTURE
        # (puede ocupar cientos de KB por archivo).
        meta = read_flac_metadata(file_path, skip_pictures=cached_cover is not None)
        song.title = meta.first("title")
        song.artist = meta.first("artist")
        song.album = meta.first("album")

        if meta.duration is not None and meta.duration > 0:
            song.duration = timedelta(seconds=meta.duration)

        if meta.bitrate:
            song.bitrate = round(meta.bitrate)

        if cached_cover is None:
            cover = meta.cover
            if cover is not None:
                song.cover_path = export_cover(cover, file_path)
                if cover_cache is not None and song.cover_path:
                    cover_cache.add(song.cover_path)
    except Exception:
        log.warning("No se pudieron leer los metadatos de %s", file_path, exc_info=True)
    return song


def iter_songs(file_paths: list[str], batch_size: int = BATCH_SIZE) -> Iterator[list[Song]]:
    """Itera ``Song`` en lotes, reutilizando el índice de carátulas."""
    cache = CoverCache()
    batch: list[Song] = []
    for path in file_paths:
        batch.append(read_song(path, cover_cache=cache))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def read_songs(file_paths: list[str]) -> list[Song]:
    return [song for batch in iter_songs(file_paths) for song in batch]


def find_flac_files(directory: str) -> list[str]:
    result: list[str] = []
    try:
        for root, _, files in os.walk(directory):
            for name in files:
                if name.lower().endswith(".flac"):
                    result.append(os.path.join(root, name))
    except Exception:
        log.warning("Error al recorrer el directorio %s", directory, exc_info=True)
    return sorted(result)
