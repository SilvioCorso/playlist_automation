# Serato Playlist Automation
# Entry point module - v4.4

import sys
import os

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def check_dependencies():
    missing = []
    try:
        import PySide6
    except ImportError:
        missing.append("PySide6")
    return missing


def main():
    print("=" * 55)
    print("  Serato Playlist Automation v4.4")
    print("  Automazione playlist per Serato DJ")
    print("=" * 55)
    print()

    missing = check_dependencies()
    if missing:
        print("DIPENDENZE MANCANTI:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("Installa con: pip install " + " ".join(missing))
        input("Premi Invio per uscire...")
        sys.exit(1)

    from serato_automation.ui_main import run_app
    run_app()


if __name__ == "__main__":
    main()
