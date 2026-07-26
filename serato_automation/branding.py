# Serato Playlist Automation — branding, URLs, and external-link helpers.
#
# Centralises product identity and outbound links so UI code stays readable
# and marketing URLs can be updated in one place.

import sys
import webbrowser
from typing import Optional

APP_VERSION = "4.4"
APP_NAME = "Serato Playlist Automation"
APP_VENDOR = "SirvioDJ"
APP_TAGLINE_KEY = "app_tagline"  # i18n key

# Outbound links (open in the user's default browser)
URL_WEBSITE = "https://sirviodj.it"
URL_FEEDBACK = (
    "https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContatto"
)
URL_PRO_UPGRADE = "https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContatto"
URL_BLOG = "https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo"


def open_url(url: str) -> bool:
    """Open *url* in the system default browser. Returns True on success."""
    if not url:
        return False
    try:
        webbrowser.open(url, new=2)  # new tab when possible
        return True
    except Exception:
        return False


def window_title() -> str:
    return f"{APP_NAME} v{APP_VERSION}"


def log_startup_message() -> str:
    return f"Avvio applicazione v{APP_VERSION}"


def is_pro_license(config: Optional[dict] = None) -> bool:
    """Return True when a valid Pro license is stored in config.

    Placeholder until the licensing backend is wired — always False for now.
    """
    if not config:
        return False
    return bool(config.get("license_pro", False))
