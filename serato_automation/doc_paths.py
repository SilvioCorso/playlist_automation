# Localized markdown documents — one file per language under docs/<stem>/<lang>.md
#
# When adding a new user-facing document:
#   1. Create docs/<stem>/en.md (source of truth)
#   2. Add docs/<stem>/<lang>.md for each entry in i18n.SUPPORTED_LANGS
#   3. Add UI keys guide_* / algo_* titles in i18n.py (en + it) and locale_supplement.py
#   4. Run: python tools/verify_i18n.py

from __future__ import annotations

import os

from .config import get_config_dir
from .i18n import SUPPORTED_LANGS, get_language

_LEGACY_FILES = {
    ("quick_guide", "it"): ("docs", "guida_rapida.md"),
    ("algorithm", "it"): ("docs", "algoritmo_percentuali.md"),
}


def resolve_localized_doc(stem: str) -> str:
    """Return absolute path to the best matching markdown for the current language."""
    lang = get_language()
    root = get_config_dir()
    tried: list[str] = []

    subdir = os.path.join(root, "docs", stem)
    for code in (lang, "en", "it"):
        if code not in SUPPORTED_LANGS and code != "en":
            continue
        path = os.path.join(subdir, f"{code}.md")
        tried.append(path)
        if os.path.isfile(path):
            return path

    legacy = _LEGACY_FILES.get((stem, lang))
    if legacy:
        path = os.path.join(root, *legacy)
        tried.append(path)
        if os.path.isfile(path):
            return path

    return tried[0] if tried else os.path.join(subdir, f"{lang}.md")
