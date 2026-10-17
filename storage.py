"""Persistencia ligera del estado del reproductor (JSON en datos locales)."""

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def _data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "FlacPlayer")
    os.makedirs(path, exist_ok=True)
    return path


def state_path() -> str:
    return os.path.join(_data_dir(), "state.json")


def save_state(data: dict[str, Any]) -> None:
    try:
        with open(state_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        log.warning("No se pudo guardar el estado", exc_info=True)


def load_state() -> dict[str, Any]:
    try:
        with open(state_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        log.warning("No se pudo cargar el estado", exc_info=True)
        return {}
