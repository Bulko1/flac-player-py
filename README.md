# FlacPlayer (Python)

Reproductor de audio FLAC de escritorio con **Tkinter**, **sounddevice** y **soundfile**.

Sin dependencias externas pesadas — usa libsndfile y PortAudio (empaquetados en los wheels de pip).

## Requisitos

- **Python 3.10+**
- **pip** (para instalar dependencias)

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
python main.py
```

## Dependencias

| Paquete | Propósito |
|---------|-----------|
| `sounddevice` | Reproducción de audio (PortAudio) |
| `soundfile` | Lectura/decodificación FLAC (libsndfile) |
| `mutagen` | Metadatos y carátulas |
| `Pillow` | Visualización de carátulas en Tkinter |

## Estructura

```
flac-player-py/
├── main.py                  # UI Tkinter + entry point
├── player.py                # Motor de audio (sounddevice + soundfile)
├── playlist.py              # Lista con shuffle/repeat
├── song.py                  # Dataclass Song
├── metadata_service.py      # Lectura de tags (mutagen)
├── requirements.txt
└── README.md
```

## Funcionalidades

- Reproducción FLAC nativa (sin VLC, sin ffmpeg)
- Play / Pause / Stop / Siguiente / Anterior
- Barra de progreso con seek
- Control de volumen
- Lista de reproducción (archivos y carpetas)
- Menú contextual en la lista (reproducir, eliminar)
- Shuffle y Repeat (None / All / One)
- Metadatos: título, artista, álbum, duración
- Extracción y visualización de carátulas (cover art)
- Tema oscuro
- Auto-siguiente al terminar canción
