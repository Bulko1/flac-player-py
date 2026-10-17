# FlacPlayer (Python)

![CI](https://github.com/Bulko1/flac-player-py/actions/workflows/ci.yml/badge.svg)

Reproductor de audio FLAC de escritorio con **Tkinter** y **miniaudio**.

Sin dependencias externas pesadas — usa miniaudio (empaquetado en el wheel de pip), con backend nativo del sistema (WASAPI en Windows). Todas las dependencias son permisivas (MIT/BSD).

## Requisitos

- **Python 3.10+** (CI en Windows: 3.10, 3.12 y 3.13)
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
| `miniaudio` | Reproducción y decodificación FLAC (dr_flac, backends nativos) |
| `Pillow` | Visualización de carátulas en Tkinter |

Los metadatos y carátulas se leen con un parser FLAC propio (`flac_meta.py`, RFC 9639), sin dependencias adicionales.

## Estructura

```
flac-player-py/
├── main.py                  # Entry point
├── player.py                # Motor de audio (hilo productor + callback RT)
├── playlist.py              # Lista con shuffle (bolsa) / repeat
├── song.py                  # Dataclass Song
├── metadata_service.py      # Lectura de tags y carátulas (caché en disco)
├── flac_meta.py             # Parser de bloques FLAC: tags, duración, carátulas
├── storage.py               # Persistencia del estado (JSON)
├── ui/                      # Interfaz Tkinter
│   ├── app.py               #   Controlador principal
│   ├── playlist_panel.py    #   Lista, filtro y menú contextual (arriba)
│   ├── transport_panel.py   #   Progreso, transporte y volumen (centro)
│   ├── track_panel.py       #   Carátula y metadatos (abajo)
│   ├── theme.py             #   Paleta y estilos ttk
│   └── widgets.py           #   Tooltips, formato y truncado
├── tests/                   # Suite de pruebas (pytest) + assets FLAC versionados
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Funcionalidades

- Reproducción FLAC nativa (sin VLC, sin ffmpeg)
- Interfaz en tres bloques: **lista arriba**, **controles al medio**, **detalle de la pista abajo**
- Play / Pause / Stop / Siguiente / Anterior
- Barra de progreso con seek
- Control de volumen con mute
- Lista de reproducción (archivos y carpetas) con **filtro de búsqueda**
- Menú contextual en la lista (reproducir, reproducir a continuación, eliminar, vaciar)
- Shuffle (sin repetición inmediata) y Repeat (None / All / One), con indicadores
- Metadatos: título, artista, álbum, duración
- Extracción y caché de carátulas (cover art)
- Tema oscuro (por defecto) y **tema claro** conmutables (botón 🌙/☀️)
- Auto-siguiente al terminar canción
- Escaneo de metadatos en segundo plano (no bloquea la interfaz)
- Persistencia de la lista, modo y volumen entre sesiones

## Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Espacio` | Reproducir / Pausar |
| `←` / `→` | Retroceder / avanzar 5 s |
| `Ctrl+←` / `Ctrl+→` | Canción anterior / siguiente |
| `Ctrl+O` | Añadir archivos |
| `Ctrl+F` | Buscar en la lista |
| `Ctrl+S` | Activar/desactivar aleatorio |
| `Ctrl+T` | Cambiar tema (oscuro / claro) |
| `Supr` | Eliminar canción seleccionada |

## Desarrollo

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt

ruff check .                  # Lint
pytest                        # Tests
```

Los tests usan FLAC de prueba versionados en `tests/assets/` (copiados a un temporal), sin dependencias de codificación. El CI (GitHub Actions, `windows-latest`) instala `requirements-dev.txt` y ejecuta `ruff` + `pytest` en Python 3.10, 3.12 y 3.13.

## Licencia

MIT (ver `LICENSE`). Todas las dependencias son permisivas: `miniaudio` (MIT) y `Pillow` (MIT-CMU) en runtime, `pytest` y `ruff` (MIT) en desarrollo.

El proyecto no admite dependencias copyleft (GPL/LGPL): por eso los metadatos FLAC y las carátulas se leen con un parser propio (`flac_meta.py`) y los tests usan FLAC versionados en `tests/assets/`.
