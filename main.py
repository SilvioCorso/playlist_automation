# Serato Playlist Automation
# Entry point module - v4.5

import sys
import os

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def check_dependencies():
    """Return a list of missing required dependencies (empty = all OK)."""
    missing = []
    for module_name in ("PySide6", "rapidfuzz", "mutagen", "send2trash"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    return missing


def main():
    print("=" * 55)
    print("  Serato Playlist Automation v4.5")
    print("  Automazione playlist per Serato DJ")
    print("=" * 55)
    print()

    missing = check_dependencies()
    if missing:
        print("DIPENDENZE MANCANTI:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("Per installare tutto automaticamente:")
        print("  - Doppio click su launch_silently.pyw  (avvio silenzioso)")
        print("  - Oppure: start.bat  (con finestra console)")
        print()
        print("Oppure installa manualmente con:")
        print(f"  pip install -r requirements.txt")
        print("  python -m playwright install chromium")
        print()
        try:
            input("Premi Invio per uscire...")
        except EOFError:
            pass
        sys.exit(1)

    from serato_automation.ui_main import run_app
    run_app()


if __name__ == "__main__":
    main()
