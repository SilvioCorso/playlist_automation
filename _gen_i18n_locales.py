import json
import pathlib
import re
import runpy

from deep_translator import GoogleTranslator

base = pathlib.Path(r"c:\Users\fulvi\Desktop\mainDJ\Serato_Playlist_Automation_v4.1")
m = runpy.run_path(str(base / "serato_automation" / "i18n.py"))
en = dict(m["TRANSLATIONS"]["en"])

new_en = {
    "ph_playlist_input": "Paste the playlist here...\n\nExample:\nDavid Guetta - Titanium\nCalvin Harris - Summer\nAvicii - Wake Me Up",
    "guide_body_detailed": "<b>RECOMMENDED FORMAT:</b>  <code>Artist - Title</code>  (one track per line)<br><br>The separator MUST be <b>space-dash-space</b> (<code> - </code>).<br>The artist should come <b>BEFORE</b> the title for better matching accuracy.<br><br><b>Correct examples:</b><br>&nbsp;&nbsp;&nbsp;David Guetta - Titanium<br>&nbsp;&nbsp;&nbsp;Calvin Harris - Summer<br>&nbsp;&nbsp;&nbsp;Martin Garrix - Animals<br>&nbsp;&nbsp;&nbsp;Avicii - Wake Me Up<br><br><b>Examples to AVOID:</b><br>&nbsp;&nbsp;&nbsp;Titanium - David Guetta  &nbsp;← artist after title<br>&nbsp;&nbsp;&nbsp;1. David Guetta - Titanium  &nbsp;← numbering is not needed<br>&nbsp;&nbsp;&nbsp;David Guetta ft. Sia - Titanium (Radio Edit)  &nbsp;← too many details",
    "player_play_pause": "Play/Pause",
    "player_no_file": "No file",
    "player_play_track": "Play track: {name}",
    "lock_tooltip_locked": "Row locked (always selected)",
    "lock_tooltip_unlock": "Unlock row",
    "score_locked_tooltip": "Locked row: score forced to 100%",
    "found_versions_tooltip": "Found versions: {count} of {total}",
    "title_library_loaded": "Library Loaded",
    "msg_library_loaded": "Tracks: {tracks}\nWith BPM: {bpm}\nWith Key: {key}\nWith Comment: {comment}",
    "wizard_event_ph": "e.g. Rossi Wedding - 21 June 2026",
    "wizard_playlist_ph": "Paste the event playlist here...",
    "wizard_header_playlist": "1) Playlist",
    "wizard_header_matching": "2) Matching",
    "wizard_header_review": "3) Review",
    "wizard_header_export": "4) Export",
    "grp_wizard_crate": "Tracks for crate",
    "grp_wizard_missing": "Missing / To buy",
    "serato_not_detected_short": "Serato not detected",
    "wizard_lib_status_html": "<b>Library:</b> {count} tracks<br><b>Folder:</b> {folder}",
    "wizard_not_set_folder": "(not set)",
    "dlg_wizard_playlist": "Open Event Playlist",
    "import_url_ph": "https://www.youtube.com/playlist?list=...  or  https://open.spotify.com/playlist/...",
    "copy_yes": "YES",
}

source = {**en, **new_en}
keys = list(source.keys())

PH = re.compile(r"\{[^{}]+\}")
TG = re.compile(r"</?[^>]+?>")


def protect(text: str):
    ph, tg = [], []

    def repl_ph(m):
        ph.append(m.group(0))
        return f"__PH{len(ph)-1}__"

    def repl_tg(m):
        tg.append(m.group(0))
        return f"__TG{len(tg)-1}__"

    t = PH.sub(repl_ph, text)
    t = TG.sub(repl_tg, t)
    return t, ph, tg


def unprotect(text: str, ph, tg):
    text = re.sub(r"__PH(\d+)__", lambda m: ph[int(m.group(1))], text)
    text = re.sub(r"__TG(\d+)__", lambda m: tg[int(m.group(1))], text)
    return text


def translate_locale(target_code: str):
    translator = GoogleTranslator(source="en", target=target_code)
    out = {}
    failed = []
    for k in keys:
        t0, ph, tg = protect(source[k])
        try:
            t1 = translator.translate(t0)
            if not isinstance(t1, str) or not t1.strip():
                raise ValueError("empty")
        except Exception:
            t1 = t0
            failed.append(k)
        out[k] = unprotect(t1, ph, tg)
    return out, failed

locales = {}
failed_map = {}
for short, code in [("de", "de"), ("es", "es"), ("fr", "fr"), ("ru", "ru"), ("zh", "zh-CN")]:
    loc, failed = translate_locale(code)
    locales[short] = loc
    failed_map[short] = failed

locales["es"]["copy_yes"] = "SI"
locales["de"]["copy_yes"] = "JA"
locales["fr"]["copy_yes"] = "OUI"
locales["ru"]["copy_yes"] = "ДА"
locales["zh"]["copy_yes"] = "是"

header = '''"""Additional locale dictionaries for i18n."""

from __future__ import annotations

NEW_KEYS = [
    "ph_playlist_input",
    "guide_body_detailed",
    "player_play_pause",
    "player_no_file",
    "player_play_track",
    "lock_tooltip_locked",
    "lock_tooltip_unlock",
    "score_locked_tooltip",
    "found_versions_tooltip",
    "title_library_loaded",
    "msg_library_loaded",
    "wizard_event_ph",
    "wizard_playlist_ph",
    "wizard_header_playlist",
    "wizard_header_matching",
    "wizard_header_review",
    "wizard_header_export",
    "grp_wizard_crate",
    "grp_wizard_missing",
    "serato_not_detected_short",
    "wizard_lib_status_html",
    "wizard_not_set_folder",
    "dlg_wizard_playlist",
    "import_url_ph",
    "copy_yes",
]

'''

output = base / "serato_automation" / "i18n_locales.py"
text = (
    header
    + "LOCALE_DE = " + json.dumps(locales["de"], ensure_ascii=False, indent=4, sort_keys=True) + "\n\n"
    + "LOCALE_ES = " + json.dumps(locales["es"], ensure_ascii=False, indent=4, sort_keys=True) + "\n\n"
    + "LOCALE_FR = " + json.dumps(locales["fr"], ensure_ascii=False, indent=4, sort_keys=True) + "\n\n"
    + "LOCALE_RU = " + json.dumps(locales["ru"], ensure_ascii=False, indent=4, sort_keys=True) + "\n\n"
    + "LOCALE_ZH = " + json.dumps(locales["zh"], ensure_ascii=False, indent=4, sort_keys=True) + "\n"
)
output.write_text(text, encoding="utf-8")

print("written", output)
print("key_count", len(keys))
print("locale_counts", {k: len(v) for k, v in locales.items()})
print("failed", {k: len(v) for k, v in failed_map.items()})
print("failed_keys_de", failed_map["de"])
