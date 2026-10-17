from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path


@dataclass
class Song:
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: timedelta = field(default_factory=timedelta)
    bitrate: int = 0  # bits por segundo; 0 = desconocido
    cover_path: str | None = None

    @property
    def display_title(self) -> str:
        return self.title or Path(self.path).stem

    @property
    def display_artist(self) -> str:
        return self.artist or "Artista desconocido"

    @property
    def display_album(self) -> str:
        return self.album or "Álbum desconocido"

    @property
    def duration_seconds(self) -> float:
        return self.duration.total_seconds()

    @property
    def duration_str(self) -> str:
        if self.duration_seconds <= 0:
            return "--:--"
        total = int(self.duration_seconds)
        return f"{total // 60}:{total % 60:02d}"

    @property
    def bitrate_str(self) -> str:
        if self.bitrate <= 0:
            return "-- kbps"
        return f"{round(self.bitrate / 1000)} kbps"

    @property
    def display_text(self) -> str:
        return f"{self.display_artist} - {self.display_title}"
