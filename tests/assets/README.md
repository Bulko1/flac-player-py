# Fixtures FLAC

FLACs de prueba versionados. La suite **no necesita ninguna librería de
codificación** para correr: los tests copian estos archivos a `tmp_path` y los
modifican con Python puro (bloques PICTURE insertados a mano).

| Archivo | Contenido |
|---|---|
| `tone.flac` | 1 s, mono, 8 kHz, seno de 440 Hz a amplitud 0.1, sin tags |
| `tagged.flac` | 2 s, mono, 8 kHz, tags Vorbis: `title="Canción de prueba"`, `artist="Artista de prueba"`, `album="Álbum de prueba"` |

Si alguna vez necesitas regenerarlos, usa cualquier herramienta de
codificación/etiquetado FLAC (PCM 16 bits, mono, 8 kHz) respetando estos
parámetros.
