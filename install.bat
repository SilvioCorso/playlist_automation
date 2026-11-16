@echo off
title Serato Playlist Automation - Installazione
echo ======================================
echo   Serato Playlist Automation - Installazione
echo ======================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato!
    echo.
    echo Python 3.10 o superiore e richiesto.
    echo Scaricalo da: https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Durante l'installazione, spunta
    echo "Add Python to PATH" alla fine dell'installer.
    echo.
    pause
    exit /b 1
)

echo [OK] Python trovato:
python --version
echo.

:: Create virtual environment
echo [1/4] Creazione ambiente virtuale...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERRORE] Impossibile creare l'ambiente virtuale.
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtuale creato.
) else (
    echo [OK] Ambiente virtuale gia esistente.
)
echo.

:: Activate virtual environment
echo [2/4] Attivazione ambiente virtuale...
call venv\Scripts\activate.bat
echo [OK] Ambiente virtuale attivato.
echo.

:: Install core dependencies
echo [3/4] Installazione dipendenze core...
python -m pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRORE] Si e verificato un errore durante l'installazione.
    echo Prova a eseguire manualmente:
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo.

:: Optional: Amazon Music import (Playwright + Chromium, ~400 MB)
echo [4/4] Import da Amazon Music (opzionale, richiede ~400 MB)?
set /p WANT_AMAZON="Vuoi abilitare l'import da Amazon Music? [s/N]: "
if /i "%WANT_AMAZON%"=="s" (
    echo Installazione Playwright + Chromium...
    pip install -r requirements-amazon.txt
    python -m playwright install chromium
    if errorlevel 1 (
        echo [AVVISO] Installazione di Playwright Chromium non riuscita.
        echo L'import da YouTube e Spotify continuera a funzionare.
        echo Per riprovare: venv\Scripts\activate ^&^& playwright install chromium
    ) else (
        echo [OK] Import da Amazon Music abilitato.
    )
) else (
    echo [OK] Salto Amazon Music. YouTube e Spotify rimangono disponibili.
)
echo.

echo ======================================
echo   Installazione completata!
echo ======================================
echo.
echo Per avviare l'applicazione:
echo   1. Doppio click su "run.bat"
echo   Oppure:
echo   2. venv\Scripts\activate.bat
echo      python main.py
echo.
pause
