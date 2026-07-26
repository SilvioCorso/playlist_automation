# Theme palette and styling helpers — shared by MainWindow and dialogs.

from typing import Dict

# Updated by MainWindow._apply_theme() so dialogs opened later read the active theme.
_DARK_ACTIVE: bool = False


def set_dark_active(dark: bool) -> None:
    global _DARK_ACTIVE
    _DARK_ACTIVE = dark


def is_dark() -> bool:
    return _DARK_ACTIVE


def palette(dark: bool | None = None) -> Dict[str, str]:
    """Return named colours for the active (or requested) theme."""
    if dark is None:
        dark = _DARK_ACTIVE
    if dark:
        return {
            "bg": "#1a1d23",
            "panel": "#22262e",
            "panel_alt": "#2a2d38",
            "border": "#3d4255",
            "text": "#e0e4ef",
            "text_muted": "#a0a8c0",
            "text_faint": "#888ea8",
            "accent": "#9b7de0",
            "accent_dark": "#7c5cbf",
            "success": "#27ae60",
            "danger": "#e74c3c",
            "header_sub": "rgba(255,255,255,0.92)",
            "footer_text": "#b0b8d0",
            "step_inactive": "#666",
            "step_active": "#9b7de0",
            "step_done": "#27ae60",
            "dots_bg": "#2a2540",
            "footer_bar": "#22262e",
        }
    return {
        "bg": "#f0f2f5",
        "panel": "#ffffff",
        "panel_alt": "#f8f9fb",
        "border": "#d0c8e8",
        "text": "#2c3e50",
        "text_muted": "#7f8c8d",
        "text_faint": "#95a5a6",
        "accent": "#4927af",
        "accent_dark": "#3d208f",
        "success": "#1e8449",
        "danger": "#c0392b",
        "header_sub": "rgba(255,255,255,0.95)",
        "footer_text": "#5a6a7a",
        "step_inactive": "#aaa",
        "step_active": "#4927af",
        "step_done": "#27ae60",
        "dots_bg": "#f0ecfa",
        "footer_bar": "#ffffff",
    }


def apply_themed_dialog(dialog, dark: bool | None = None) -> None:
    """Ensure a QDialog inherits readable colours (no hard-coded white panels)."""
    p = palette(dark)
    dialog.setStyleSheet(
        f"QDialog {{ background-color: {p['bg']}; }}"
        f"QLabel {{ color: {p['text']}; background: transparent; }}"
        f"QLineEdit, QTextEdit, QComboBox, QSpinBox {{"
        f"  background: {p['panel_alt']}; color: {p['text']};"
        f"  border: 1px solid {p['border']}; border-radius: 5px; }}"
    )


def panel_box_style(dark: bool | None = None) -> str:
    p = palette(dark)
    return (
        f"background: {p['panel_alt']}; border: 1px solid {p['border']};"
        f" border-radius: 6px; padding: 12px; color: {p['text']};"
    )


def muted_label_style(dark: bool | None = None, size: int = 11) -> str:
    p = palette(dark)
    return f"color: {p['text_muted']}; font-size: {size}px; background: transparent;"


def title_label_style(dark: bool | None = None, size: int = 13) -> str:
    p = palette(dark)
    return (
        f"color: {p['text']}; font-size: {size}px; font-weight: bold;"
        f" background: transparent;"
    )


def accent_label_style(dark: bool | None = None, size: int = 12) -> str:
    p = palette(dark)
    return f"color: {p['accent']}; font-weight: bold; font-size: {size}px; background: transparent;"
