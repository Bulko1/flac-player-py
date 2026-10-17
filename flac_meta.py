"""Lectura de la sección de metadatos de archivos FLAC (RFC 9639).

Implementación propia, sin dependencias externas: recorre los bloques de
metadatos y extrae comentarios Vorbis, duración y tamaño del audio (STREAMINFO)
y carátulas (PICTURE), sin decodificar el audio.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import BinaryIO

log = logging.getLogger(__name__)

#: Tipos de bloque de metadatos que se interpretan (RFC 9639, sección 8.1).
_BLOCK_STREAMINFO = 0
_BLOCK_VORBIS_COMMENT = 4
_BLOCK_PICTURE = 6

#: Tipo de imagen "carátula frontal" (mismo valor que APIC de ID3v2).
PICTURE_TYPE_FRONT_COVER = 3

#: Límites de lectura defensivos para bloques anómalos (bytes).
_MAX_VORBIS_COMMENT_BYTES = 8 * 1024 * 1024
_MAX_PICTURE_BYTES = 16 * 1024 * 1024

#: Longitud fija del bloque STREAMINFO según la especificación.
_STREAMINFO_BYTES = 34

#: Longitud de la cabecera de una etiqueta ID3v2 (RFC 6262 / especificación ID3).
_ID3_HEADER_BYTES = 10


class FlacError(ValueError):
    """El archivo no es FLAC o su sección de metadatos está dañada."""


@dataclass
class Picture:
    """Imagen embebida en un bloque PICTURE."""

    mime: str
    data: bytes
    type: int = PICTURE_TYPE_FRONT_COVER


@dataclass
class FlacMetadata:
    """Metadatos relevantes extraídos de un archivo FLAC."""

    tags: dict[str, list[str]] = field(default_factory=dict)
    duration: float | None = None
    #: Bitrate medio real en bits/s (datos de audio ÷ duración); excluye
    #: cabecera ID3, tags y carátulas. ``None`` si no se puede calcular.
    bitrate: float | None = None
    pictures: list[Picture] = field(default_factory=list)

    def first(self, key: str) -> str:
        """Primer valor del tag ``key`` (Vorbis no distingue mayúsculas)."""
        values = self.tags.get(key.upper())
        return values[0] if values else ""

    @property
    def cover(self) -> Picture | None:
        """Carátula preferida: la frontal (tipo 3) o, si no, la primera."""
        for picture in self.pictures:
            if picture.type == PICTURE_TYPE_FRONT_COVER:
                return picture
        return self.pictures[0] if self.pictures else None


def read_flac_metadata(path: str, skip_pictures: bool = False) -> FlacMetadata:
    """Lee los metadatos de ``path``.

    Lanza ``FlacError`` si el archivo no es FLAC o si la sección de metadata
    está truncada. Los bloques PICTURE dañados se ignoran con un aviso.

    ``skip_pictures`` omite el contenido de los bloques PICTURE sin leerlo, útil
    cuando la carátula ya fue exportada a disco y solo interesan los tags.
    """
    with open(path, "rb") as fh:
        _skip_id3v2(fh)
        if fh.read(4) != b"fLaC":
            raise FlacError(f"No es un archivo FLAC: {path}")
        meta = FlacMetadata()
        while True:
            header = fh.read(4)
            if len(header) < 4:
                raise FlacError(f"Metadatos FLAC truncados: {path}")
            block_type = header[0] & 0x7F
            size = int.from_bytes(header[1:4], "big")

            if block_type == _BLOCK_STREAMINFO:
                body = _read_block(fh, size, _STREAMINFO_BYTES)
                if body is not None:
                    meta.duration = _parse_streaminfo(body)
            elif block_type == _BLOCK_VORBIS_COMMENT:
                body = _read_block(fh, size, _MAX_VORBIS_COMMENT_BYTES)
                if body is not None:
                    _parse_vorbis_comment(body, meta.tags)
            elif block_type == _BLOCK_PICTURE:
                if skip_pictures:
                    fh.seek(size, os.SEEK_CUR)
                else:
                    body = _read_block(fh, size, _MAX_PICTURE_BYTES)
                    picture = _parse_picture(body) if body is not None else None
                    if picture is not None:
                        meta.pictures.append(picture)
            else:
                fh.seek(size, os.SEEK_CUR)

            if header[0] & 0x80:  # flag de último bloque
                break

        # ``fh.tell()`` es el inicio de los datos de audio, así que el bitrate
        # medio excluye ID3, tags y carátula: una carátula grande no lo infla.
        audio_bytes = os.fstat(fh.fileno()).st_size - fh.tell()
        if meta.duration and audio_bytes > 0:
            meta.bitrate = audio_bytes * 8 / meta.duration
        return meta


def _skip_id3v2(fh: BinaryIO) -> None:
    """Salta una etiqueta ID3v2 inicial, si la hay.

    Algunos etiquetadores escriben un ID3v2 delante del stream FLAC; dr_flac lo
    tolera al reproducir, así que el parser también debe hacerlo.
    """
    start = fh.tell()
    header = fh.read(_ID3_HEADER_BYTES)
    if len(header) < _ID3_HEADER_BYTES or header[:3] != b"ID3":
        fh.seek(start)
        return

    # Tamaño "synchsafe" (7 bits por byte) y posible pie de etiqueta (ID3v2.4).
    size = (
        ((header[6] & 0x7F) << 21)
        | ((header[7] & 0x7F) << 14)
        | ((header[8] & 0x7F) << 7)
        | (header[9] & 0x7F)
    )
    footer = _ID3_HEADER_BYTES if header[5] & 0x10 else 0
    fh.seek(start + _ID3_HEADER_BYTES + size + footer)


def _read_block(fh: BinaryIO, size: int, max_bytes: int) -> bytes | None:
    """Lee el bloque completo o, si excede ``max_bytes``, lo omite."""
    if size > max_bytes:
        fh.seek(size, os.SEEK_CUR)
        return None
    return fh.read(size)


def _parse_streaminfo(body: bytes) -> float | None:
    """Duración en segundos a partir de sample rate y total de samples."""
    if len(body) < _STREAMINFO_BYTES:
        return None
    packed = int.from_bytes(body[10:18], "big")
    samplerate = packed >> 44
    total_samples = packed & 0xFFFFFFFFF  # 36 bits
    if samplerate <= 0 or total_samples <= 0:
        return None
    return total_samples / samplerate


def _parse_vorbis_comment(body: bytes, tags: dict[str, list[str]]) -> None:
    """Extrae los comentarios ``CLAVE=valor`` (enteros little-endian)."""
    pos = 0
    try:
        vendor_len = int.from_bytes(body[pos : pos + 4], "little")
        pos += 4 + vendor_len  # el vendor string no se usa
        count = int.from_bytes(body[pos : pos + 4], "little")
        pos += 4
        for _ in range(count):
            length = int.from_bytes(body[pos : pos + 4], "little")
            pos += 4
            comment = body[pos : pos + length].decode("utf-8", "replace")
            pos += length
            key, sep, value = comment.partition("=")
            if sep:
                tags.setdefault(key.strip().upper(), []).append(value)
    except Exception:
        log.warning("Sección VORBIS_COMMENT dañada; se ignora", exc_info=True)


def _parse_picture(body: bytes) -> Picture | None:
    """Extrae tipo, MIME y datos de un bloque PICTURE (big-endian)."""
    try:
        pic_type = int.from_bytes(body[0:4], "big")
        mime_len = int.from_bytes(body[4:8], "big")
        pos = 8
        mime = body[pos : pos + mime_len].decode("ascii", "replace").lower()
        pos += mime_len
        desc_len = int.from_bytes(body[pos : pos + 4], "big")
        pos += 4 + desc_len
        pos += 16  # ancho, alto, profundidad y colores no se usan
        data_len = int.from_bytes(body[pos : pos + 4], "big")
        pos += 4
        data = body[pos : pos + data_len]
        if not data or len(data) != data_len:
            raise ValueError("datos de la carátula truncados")
        return Picture(mime=mime, data=bytes(data), type=pic_type)
    except Exception:
        log.warning("Bloque PICTURE dañado; se ignora", exc_info=True)
        return None
