# Serato Playlist Automation - Silent Launcher (.pyw)
# Avvia il software senza finestra CMD
# Doppio click su questo file per avviare il programma
#
# NOTA: Su Windows, i file .pyw vengono eseguiti da pythonw.exe
# che non apre la finestra della console.
#
# Se non funziona con doppio click:
# 1. Assicurati che Python sia installato
# 2. Assicurati che l'associazione .pyw -> pythonw.exe sia attiva
# 3. In alternativa, usa launch_silently.vbs

import sys
import os

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Check dependencies
try:
    import PySide6
except ImportError:
    # If launched via .pyw, show a messagebox instead of console print
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0,
            "PySide6 non e' installato!\n\n"
            "Esegui install.bat prima di usare questo launcher.",
            "Errore - Serato Playlist Automation",
            0x10)
    except Exception:
        pass
    sys.exit(1)

from serato_automation.ui_main import run_app
run_app()
