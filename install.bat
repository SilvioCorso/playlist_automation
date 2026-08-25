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
    echo Python 3.11 o superiore e richiesto.
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
echo [1/3] Creazione ambiente virtuale...
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
echo [2/3] Attivazione ambiente virtuale...
call venv\Scripts\activate.bat
echo [OK] Ambiente virtuale attivato.
echo.

:: Install dependencies
echo [3/3] Installazione dipendenze...
python -m pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo [ERRORE] Si e verificato un errore durante l'installazione.
    echo Prova a eseguire manualmente:
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Install Playwright Chromium (needed for Amazon Music URL import)
echo [4/4] Download del browser headless per Amazon Music...
playwright install chromium
if errorlevel 1 (
    echo [AVVISO] Installazione di Playwright Chromium non riuscita.
    echo L'import da YouTube e Spotify continuera a funzionare.
    echo Per abilitare Amazon Music, esegui manualmente:
    echo   venv\Scripts\activate
    echo   playwright install chromium
    echo.
) else (
    echo [OK] Browser headless installato.
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
