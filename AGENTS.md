# AGENTS.md

Reproductor FLAC de escritorio (Windows-first, Tkinter). Python ≥3.10: `ruff` apunta a
`py310` y el CI prueba 3.10/3.12/3.13 — no uses sintaxis posterior a 3.10. Todo el repo
(docs, comentarios, textos de UI) está en español: mantén ese idioma.

## Comandos

```bash
.venv\Scripts\python.exe -m pytest    # suite completa (no necesita dispositivo de audio)
.venv\Scripts\python.exe -m pytest tests/test_player.py::test_play_reaches_end  # un test
.venv\Scripts\python.exe -m ruff check .
python main.py                        # ejecutar la app
```

CI (`.github/workflows/ci.yml`, windows-latest): instala `requirements-dev.txt`, luego
`ruff check .` y después `pytest`. Si el venv no existe: `python -m venv .venv` +
`.venv\Scripts\pip install -r requirements-dev.txt`.

## Regla de dependencias (crítica)

El proyecto mantiene un árbol **MIT puro**: nunca añadas dependencias copyleft
(GPL/LGPL), ni en runtime ni en dev.

- `mutagen` (GPL-2.0), `soundfile`/libsndfile (LGPL-2.1) y `sounddevice` fueron
  eliminados a propósito — no los reintroduzcas ni propongas alternativas GPL
  (p. ej. `pytaglib`).
- Metadatos FLAC: parser propio en `flac_meta.py` (RFC 9639), incluida la carátula
  (bloque PICTURE). No añadas librerías de tags. Salta una etiqueta ID3v2 inicial (algunos
  archivos la llevan delante de `fLaC`) y admite `skip_pictures=True`, que usa
  `metadata_service` cuando la carátula ya está exportada (evita leer cientos de MB al
  escanear; el índice de carátulas vive en `metadata_service.CoverCache`).
- Los tests usan FLAC versionados en `tests/assets/`; **nunca** añadas un codificador
  FLAC como dependencia de test (ver `tests/assets/README.md`).
- Runtime permitido hoy: `miniaudio` + `Pillow` (transitivas: `cffi`, `pycparser`).

## Arquitectura (trampas no obvias)

- `player.py`: hilo productor → `miniaudio.stream_file` (el generador vuelve ya
  iniciado; se maneja con `send(n)`) → cola → generador de salida que alimenta
  `miniaudio.PlaybackDevice`.
  - El generador de salida debe tener **un solo `yield` por iteración** (patrón de
    pyminiaudio) y devolver exactamente los `n` frames pedidos; con dos `yield`, el
    siguiente `send()` devuelve `None`.
  - En el generador de salida `filled` cuenta **muestras** (`wanted * channels`), no
    frames: compararlo con `wanted` deja la mitad de la trama en silencio (bug real ya
    corregido, regresión cubierta por `test_stereo_callback_fills_whole_buffer`).
    `_current_frame` se actualiza en frames (`filled // channels`).
  - `play()` y `seek()` prellenan la cola (`_prefill`) antes de arrancar el dispositivo
    para no emitir silencio inicial; `take_underruns()` expone los cortes por cola vacía.
  - El callback RT no hace E/S; el volumen se escala con una list-comp sobre
    `array('f')` (≈36 µs por callback típico). No reintroduzcas numpy.
  - Tras el fin de pista el generador sigue emitiendo silencio hasta cerrar el
    dispositivo: es intencional (evita basura del buffer al dejar de producirse frames).
- `miniaudio` 1.71 **no tiene** `set_master_volume`/`get_master_volume` (aparecen en la
  doc del repo, que es de master; no existen en la versión instalada).
- Datos del usuario en `%LOCALAPPDATA%\FlacPlayer\`: `state.json` (storage.py) y
  `covers/` con nombre = sha1 del path absoluto del FLAC.
- UI en `ui/` (`ui/app.py` es el controlador); los módulos raíz se importan en absoluto
  (`from song import Song`), sin layout `src/`. El escaneo de metadatos corre en un hilo
  (`flac-scanner`) y sus resultados se drenan en el bucle `after()` de Tk.
- Al crear un módulo raíz nuevo, agrégalo a `[tool.setuptools] py-modules` en
  `pyproject.toml` para que se empaquete.

## Tests

- No requieren hardware de audio: `tests/test_player.py` usa un `FakeDevice` y simula el
  callback enviando frames al generador (`send(n)`).
- Los FLAC de `tests/assets/` son **mono**: el fixture `stereo_wav` (conftest) genera un
  WAV estéreo con la stdlib para cubrir rutas de dos canales (el bug de `filled` solo se
  manifestaba con estéreo).
- Los tests de UI crean `tk.Tk()`: se saltan solos si no hay entorno gráfico, y
  monkeypatchean `storage` para no leer/escribir el estado real del usuario.
- `pythonpath = ["."]` y `testpaths = ["tests"]` ya están configurados en
  `pyproject.toml`: ejecuta `pytest` desde la raíz.
