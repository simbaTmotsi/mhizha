"""RUNTIME (offline). Locale loading with recorded fallback.

No user-facing string is hardcoded in code. Everything comes through `t()`.

When a key is untranslated (value `TODO_TRANSLATE`) the English value is served and the
fallback is recorded on the response object. Silent fallback would hide how much of the
product a Shona-speaking farmer is actually getting in English, which is exactly the
number we need to see.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

TODO = "TODO_TRANSLATE"
DEFAULT_LANG = "en"


@lru_cache(maxsize=8)
def _load(locales_dir: str, lang: str) -> dict[str, Any]:
    path = Path(locales_dir) / f"{lang}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _lookup(data: dict[str, Any], key: str) -> str | None:
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


class Translator:
    """Resolves keys for one language, tracking every fallback to English."""

    def __init__(self, locales_dir: Path, lang: str, default_lang: str = DEFAULT_LANG):
        self.locales_dir = str(locales_dir)
        self.lang = lang
        self.default_lang = default_lang
        self.fallbacks: list[str] = []

    def t(self, key: str, **fmt: Any) -> str:
        value = _lookup(_load(self.locales_dir, self.lang), key)
        if value is None or value == TODO:
            fallback = _lookup(_load(self.locales_dir, self.default_lang), key)
            if self.lang != self.default_lang:
                self.fallbacks.append(key)
            value = fallback if fallback is not None else f"<missing:{key}>"
        return value.format(**fmt) if fmt else value

    @property
    def fell_back(self) -> bool:
        return bool(self.fallbacks)


def check_locales(locales_dir: Path, languages: list[str],
                  default_lang: str = DEFAULT_LANG) -> dict[str, dict[str, list[str]]]:
    """Report missing, untranslated, and orphaned keys per language."""
    reference = _flatten(_load(str(locales_dir), default_lang))
    report: dict[str, dict[str, list[str]]] = {}
    for lang in languages:
        if lang == default_lang:
            continue
        current = _flatten(_load(str(locales_dir), lang))
        report[lang] = {
            "missing": sorted(set(reference) - set(current)),
            "untranslated": sorted(k for k, v in current.items() if v == TODO),
            "orphaned": sorted(set(current) - set(reference)),
        }
    return report


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, f"{full}."))
        elif isinstance(value, str):
            out[full] = value
    return out
