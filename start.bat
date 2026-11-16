@echo off
title Serato Playlist Automation
:: Read version dynamically from branding.py so this banner never drifts
for /f "delims=" %%v in ('python -c "from serato_automation.branding import APP_VERSION; print(APP_VERSION)" 2^>nul') do set APPVER=%%v
if "%APPVER%"=="" set APPVER=4.5
echo ======================================
echo   Serato Playlist Automation v%APPVER%
echo   Installazione + Avvio automatico
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

:: Install/upgrade dependencies
echo [3/3] Installazione dipendenze...
python -m pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt --quiet 2>nul
echo [OK] Dipendenze installate.
echo.

echo ======================================
echo   Avvio applicazione v%APPVER%...
echo ======================================
echo.

:: Run the application
python main.py

:: If Python crashes, show the error and pause
if errorlevel 1 (
    echo.
    echo ======================================
    echo   ERRORE! L'applicazione si e chiusa in modo imprevisto.
    echo ======================================
    echo.
    echo Controlla sopra per i messaggi di errore.
    echo Se il problema persiste, elimina la cartella "venv"
    echo e riavvia questo file per reinstallare tutto.
    echo.
)

pause
