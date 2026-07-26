"""Merge v4.4+ locale supplements into i18n."""
from __future__ import annotations

from .locale_supplement_de import DE
from .locale_supplement_es import ES
from .locale_supplement_fr import FR
from .locale_supplement_ru import RU
from .locale_supplement_zh import ZH

LOCALE_SUPPLEMENT = {
    "de": DE,
    "es": ES,
    "fr": FR,
    "ru": RU,
    "zh": ZH,
}
