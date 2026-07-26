#!/usr/bin/env python3
"""Check translation parity across all supported languages."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from serato_automation.doc_paths import resolve_localized_doc
from serato_automation.i18n import SUPPORTED_LANGS, TRANSLATIONS, set_language

DOC_STEMS = ("quick_guide", "algorithm")


def main() -> int:
    en_keys = set(TRANSLATIONS["en"])
    errors = 0

    for lang in sorted(SUPPORTED_LANGS):
        set_language(lang)
        pack = TRANSLATIONS[lang]
        missing = sorted(en_keys - set(pack))
        same_as_en = sorted(
            k for k in en_keys
            if pack.get(k) == TRANSLATIONS["en"].get(k)
            and lang not in ("en",)
            and not k.startswith(("col_", "acc_", "lbl_log"))
            and k not in ("window_title", "serato_ok", "col_bpm", "col_genre", "col_player", "col_hotcue")
        )
        if missing:
            print(f"[{lang}] MISSING {len(missing)} keys: {missing[:8]}...")
            errors += len(missing)
        if same_as_en and lang != "en":
            print(f"[{lang}] Still English ({len(same_as_en)} keys) — sample: {same_as_en[:5]}")

    for stem in DOC_STEMS:
        for lang in sorted(SUPPORTED_LANGS):
            set_language(lang)
            path = resolve_localized_doc(stem)
            if not os.path.isfile(path):
                print(f"[doc:{stem}/{lang}] MISSING: {path}")
                errors += 1

    if errors:
        print(f"\nTotal issues: {errors}")
        return 1
    print("All i18n checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
