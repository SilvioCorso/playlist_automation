"""Validate i18n completeness."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serato_automation.i18n import TRANSLATIONS, SUPPORTED_LANGS, tr, set_language


def test_all_locales_have_keys():
    base_keys = set(TRANSLATIONS["en"].keys())
    for lang in SUPPORTED_LANGS:
        keys = set(TRANSLATIONS[lang].keys())
        missing = base_keys - keys
        assert not missing, f"{lang} missing keys: {missing}"


def test_no_english_leaks_in_it():
    set_language("it")
    assert tr("btn_browse") == "Sfoglia..."
    assert tr("btn_match") == "Confronta con Libreria"
    assert tr("btn_select_all") == "Spunta Tutti"


def test_no_english_leaks_in_de():
    set_language("de")
    assert tr("btn_browse") == "Durchsuchen..."
    assert tr("btn_match") == "Mit Bibliothek abgleichen"
    assert tr("btn_select_all") == "Alle auswählen"


if __name__ == "__main__":
    test_all_locales_have_keys()
    test_no_english_leaks_in_it()
    test_no_english_leaks_in_de()
    print("All i18n tests passed.")
