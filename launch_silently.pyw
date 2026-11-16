# Serato Playlist Automation - Silent Launcher (.pyw)
# Avvia il software senza finestra CMD.
#
# Doppio click su questo file per avviare il programma.
#
# AL PRIMO AVVIO (o dopo aver eliminato la cartella `venv`):
#   - Verifica che Python 3.10+ sia installato
#   - Crea automaticamente un virtualenv in `venv/`
#   - Installa tutte le dipendenze da `requirements.txt`
#     (PySide6, rapidfuzz, mutagen, Send2Trash, playwright)
#   - Esegue `playwright install chromium` per Amazon Music
#   - Mostra il progresso in una finestra di dialogo (niente console)
#
# SUGLI AVVI SUCCESSIVI:
#   - Usa direttamente il Python del virtualenv (avvio immediato)
#
# NOTA: Su Windows i file .pyw vengono eseguiti da pythonw.exe senza console.
# Se il doppio click non funziona, usa `start.bat` o `run.bat`.

import sys
import os
import subprocess
import shutil
import json
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_VENV_DIR = os.path.join(_PROJECT_ROOT, "venv")
_VENV_PY = os.path.join(_VENV_DIR, "Scripts", "python.exe")
_VENV_PIP = os.path.join(_VENV_DIR, "Scripts", "pip.exe")
_REQUIREMENTS = os.path.join(_PROJECT_ROOT, "requirements.txt")

# Marker file written once the bootstrap completes successfully.
# Its presence lets us skip the (slow) dependency check on subsequent launches.
_BOOTSTRAP_MARKER = os.path.join(_VENV_DIR, ".bootstrap_done")

MIN_PY = (3, 10)


# ---------------------------------------------------------------------------
# UI helpers (no PySide6 yet — use ctypes MessageBox during bootstrap)
# ---------------------------------------------------------------------------

def _msg_box(message, title="Serato Playlist Automation", kind="info"):
    """Show a native Windows message box without any third-party dep."""
    try:
        import ctypes
        flags = {
            "info":    0x40,        # MB_ICONINFORMATION
            "warn":    0x30,        # MB_ICONWARNING
            "error":   0x10,        # MB_ICONERROR
            "question": 0x20,       # MB_ICONQUESTION
        }.get(kind, 0x40)
        # MB_SETFOREGROUND | MB_TOPMOST | MB_OK
        flags |= 0x10000 | 0x40000 | 0x00000000
        ctypes.windll.user32.MessageBoxW(0, str(message), str(title), flags)
    except Exception:
        # Non-Windows or ctypes unavailable — print to stderr (ignored by pythonw).
        print(f"[{title}] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def _find_system_python():
    """Find a usable system Python (>= MIN_PY) on PATH or via py launcher."""
    candidates = []

    # 1) py launcher (recommended way on Windows)
    py_exe = shutil.which("py")
    if py_exe:
        candidates.append((py_exe, ["-3"]))

    # 2) plain `python` on PATH
    for name in ("python", "python3"):
        exe = shutil.which(name)
        if exe:
            candidates.append((exe, []))

    # 3) well-known install locations
    for env_var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = os.environ.get(env_var)
        if not base:
            continue
        for ver in ("3.13", "3.12", "3.11", "3.10"):
            exe = os.path.join(base, "Python" + ver, "python.exe")
            if os.path.exists(exe):
                candidates.append((exe, []))

    for exe, extra_args in candidates:
        try:
            proc = subprocess.run(
                [exe, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                continue
            # Output: "Python 3.12.1"
            ver_str = (proc.stdout or proc.stderr).strip().lower()
            if not ver_str.startswith("python "):
                continue
            ver = ver_str.split()[1].split(".")
            major, minor = int(ver[0]), int(ver[1])
            if (major, minor) >= MIN_PY:
                return exe, extra_args
        except Exception:
            continue

    return None, []


def _run_streamed(cmd, cwd=None):
    """Run a subprocess and stream its output to stdout/stderr.

    With pythonw.exe there is no console, so this is effectively silent,
    but if a console is attached (e.g. when launched from `python launch_silently.pyw`)
    the user sees the install progress.
    """
    # subprocess.DEVNULL would hide everything; we keep stdout/stderr attached
    # so debugging is possible from a terminal. pythonw.exe silently discards them.
    return subprocess.run(cmd, cwd=cwd)


def _ensure_pip(python_exe):
    """Make sure pip is available in the given Python."""
    try:
        proc = subprocess.run(
            [python_exe, "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            return True
    except Exception:
        pass
    # Try ensurepip
    try:
        subprocess.run(
            [python_exe, "-m", "ensurepip", "--upgrade"],
            timeout=60,
        )
        return True
    except Exception:
        return False


def _bootstrap():
    """Create the virtualenv and install all dependencies.

    Returns the path of the venv python.exe to use for running the app,
    or None on failure (in which case an error message has already been shown).
    """
    # 1) Find a suitable system Python
    sys_py, extra_args = _find_system_python()
    if not sys_py:
        _msg_box(
            "Python non trovato oppure versione troppo vecchia.\n\n"
            f"E' richiesto Python {MIN_PY[0]}.{MIN_PY[1]} o superiore.\n\n"
            "Scaricalo da: https://www.python.org/downloads/\n\n"
            "IMPORTANTE: durante l'installazione spunta\n"
            "    [x] Add Python to PATH",
            title="Errore - Python mancante",
            kind="error",
        )
        return None

    # 2) Create the virtualenv (idempotent)
    if not os.path.exists(_VENV_PY):
        _msg_box(
            "Primo avvio rilevato.\n\n"
            "Verra' creato un ambiente virtuale Python e installate\n"
            "tutte le dipendenze (PySide6, Playwright, ecc.).\n\n"
            "Questa operazione richiede 2-5 minuti ed avviene una\n"
            "sola volta. Al termine l'applicazione si avviera'\n"
            "automaticamente.\n\n"
            "Non chiudere questa finestra.",
            title="Installazione in corso",
            kind="info",
        )

        try:
            subprocess.run(
                [sys_py] + extra_args + ["-m", "venv", _VENV_DIR],
                timeout=120,
                check=True,
            )
        except Exception as e:
            _msg_box(
                "Impossibile creare l'ambiente virtuale.\n\n"
                f"Dettagli: {e}",
                title="Errore installazione",
                kind="error",
            )
            return None

    # 3) Ensure pip is up to date inside the venv
    if not _ensure_pip(_VENV_PY):
        _msg_box(
            "pip non disponibile nel virtualenv.\n"
            "Riprova ad eseguire launch_silently.pyw.",
            title="Errore installazione",
            kind="error",
        )
        return None

    try:
        subprocess.run(
            [_VENV_PY, "-m", "pip", "install", "--upgrade", "pip"],
            timeout=120,
        )
    except Exception:
        pass  # non-fatal

    # 4) Install requirements.txt — capture pip output so we can show WHY it
    #    failed (network / proxy / conflict / partial install). The previous
    #    version used _run_streamed without checking the return code, so a pip
    #    failure was silent: the marker got written and main.py then crashed
    #    with "DIPENDENZE MANCANTI" — invisible under pythonw.exe.
    if not os.path.exists(_REQUIREMENTS):
        _msg_box(
            "File requirements.txt non trovato.\n"
            "Reinstalla il software.",
            title="Errore installazione",
            kind="error",
        )
        return None

    pip_log = os.path.join(_PROJECT_ROOT, "pip_install.log")
    try:
        proc = subprocess.run(
            [_VENV_PY, "-m", "pip", "install", "--upgrade", "-r", _REQUIREMENTS],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        _msg_box(
            "Installazione delle dipendenze troppo lenta (timeout 10 min).\n"
            "Verifica la connessione internet e riprova lanciando di nuovo\n"
            "launch_silently.pyw.",
            title="Errore installazione", kind="error",
        )
        return None
    except Exception as e:
        _msg_box(
            "Errore durante l'installazione delle dipendenze Python.\n\n"
            f"Dettagli: {e}\n\n"
            "Verifica la connessione internet e riprova.",
            title="Errore installazione", kind="error",
        )
        return None

    # Persist the full pip log for support, then surface the tail on failure.
    try:
        with open(pip_log, "w", encoding="utf-8") as f:
            f.write(f"returncode={proc.returncode}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n")
    except Exception:
        pass

    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-20:])
        _msg_box(
            "Installazione delle dipendenze Python fallita (errore di pip).\n\n"
            f"{tail or '(nessun output)'}\n\n"
            "Log completo salvato in:\n"
            f"{pip_log}\n\n"
            "Verifica la connessione internet e riprova lanciando di nuovo\n"
            "launch_silently.pyw.",
            title="Errore installazione", kind="error",
        )
        return None

    # 4b) Verify the core deps are actually importable. A 'successful' pip run
    #     can still leave the venv half-populated (e.g. a build failure on one
    #     wheel); this guard refuses to write the marker until everything works.
    try:
        verify = subprocess.run(
            [_VENV_PY, "-c",
             "import PySide6, rapidfuzz, mutagen, certifi, send2trash"],
            capture_output=True, timeout=30,
        )
    except Exception:
        verify = None
    if verify is None or verify.returncode != 0:
        vmsg = ""
        if verify is not None:
            vmsg = (verify.stderr or b"").decode("utf-8", "replace")
        _msg_box(
            "Le dipendenze risultano ancora mancanti dopo l'installazione.\n\n"
            f"{vmsg[-400:]}\n\n"
            "Prova a eliminare la cartella 'venv' e rilanciare\n"
            "launch_silently.pyw.",
            title="Errore installazione", kind="error",
        )
        return None

    # 5) Install Playwright Chromium browser (for Amazon Music import).
    #    This is a ~150 MB download; we treat failures as non-fatal so that
    #    YouTube/Spotify imports still work without it.
    try:
        subprocess.run(
            [_VENV_PY, "-m", "playwright", "install", "chromium"],
            timeout=600,  # up to 10 minutes
        )
    except Exception:
        # Non-fatal — the user can still use YouTube/Spotify.
        pass

    # 6) Write marker so we skip bootstrap next time
    try:
        with open(_BOOTSTRAP_MARKER, "w", encoding="utf-8") as f:
            json.dump({
                "python": sys.version,
                "created_at": time.time(),
            }, f)
    except Exception:
        pass

    return _VENV_PY


# ---------------------------------------------------------------------------
# App launch (subprocess-based so a startup crash is diagnosable)
# ---------------------------------------------------------------------------

def _launch_app(venv_py):
    """Run main.py with the venv Python.

    On Windows os.execv does NOT replace the process — it spawns a child and
    exits the parent immediately, so if main.py crashed at startup the error
    vanished silently (pythonw.exe has no console). We instead run main.py as
    a short-lived watched subprocess: if it exits within a few seconds we treat
    that as a startup crash, read the captured traceback from launch_error.log
    and show it to the user. If it survives >3 s the GUI is up and we exit the
    launcher cleanly (no lingering pythonw.exe for the whole session).
    """
    main_py = os.path.join(_PROJECT_ROOT, "main.py")
    err_log = os.path.join(_PROJECT_ROOT, "launch_error.log")
    try:
        log_fh = open(err_log, "w", encoding="utf-8")
    except Exception:
        log_fh = subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            [venv_py, main_py],
            cwd=_PROJECT_ROOT,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as e:
        _msg_box(
            "Impossibile avviare l'applicazione.\n\n"
            f"Dettagli: {e}",
            title="Errore di avvio", kind="error",
        )
        return
    # Watch briefly: a startup crash happens fast; if still alive after 3 s,
    # the GUI launched successfully — exit the launcher cleanly.
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        sys.exit(0)  # app is running — launcher done.
    # Process exited within 3 s → almost certainly a startup crash.
    rc = proc.returncode
    if rc == 0:
        sys.exit(0)  # clean immediate exit (rare but valid).
    # Read back whatever the child wrote (traceback + INFO logs).
    detail = ""
    try:
        with open(err_log, "r", encoding="utf-8", errors="replace") as f:
            detail = f.read()
    except Exception:
        pass
    # Keep only the tail (the traceback) — INFO logs above are noise here.
    tail = detail.strip().splitlines()
    tail_text = "\n".join(tail[-25:]) if tail else "(nessun output)"
    _msg_box(
        "L'applicazione si è chiusa in modo imprevisto all'avvio.\n\n"
        f"Exit code: {rc}\n\n"
        f"{tail_text}\n\n"
        f"Log completo salvato in:\n{err_log}",
        title="Errore di avvio", kind="error",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Fast path: virtualenv already exists and bootstrap completed.
    if os.path.exists(_BOOTSTRAP_MARKER) and os.path.exists(_VENV_PY):
        # Sanity-check that the venv actually has the core deps (marker could
        # be stale if the user deleted site-packages, or pulled a version that
        # added a new core dep like certifi/send2trash).
        try:
            check = subprocess.run(
                [_VENV_PY, "-c", "import PySide6, rapidfuzz, mutagen, certifi, send2trash"],
                capture_output=True, timeout=15,
            )
            venv_ready = (check.returncode == 0)
        except Exception:
            venv_ready = False

        if venv_ready:
            _launch_app(_VENV_PY)
            return
        # else: marker is stale, fall through to full bootstrap

    venv_py = _bootstrap()
    if not venv_py:
        sys.exit(1)

    _launch_app(venv_py)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # Last-resort error dialog
        import traceback
        tb = traceback.format_exc()
        _msg_box(
            "Errore imprevisto durante l'avvio.\n\n"
            f"{e}\n\n"
            f"Traceback:\n{tb[:1500]}",
            title="Errore critico",
            kind="error",
        )
        sys.exit(1)
