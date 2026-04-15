"""Carga y acceso al registro de tooltips en espanol."""

import json
from pathlib import Path

_TOOLTIPS_PATH = Path(__file__).parent.parent / "data" / "tooltips_es.json"
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        with open(_TOOLTIPS_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_tooltip(key: str) -> str:
    """Retorna el texto de ayuda para un campo, o cadena vacia si no existe."""
    return _load().get(key, "")


def has_tooltip(key: str) -> bool:
    return key in _load()
