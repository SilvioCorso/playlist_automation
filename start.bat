@echo off
title Serato Playlist Automation
echo ======================================
echo   Serato Playlist Automation v3.4
echo   Installazione + Avvio automatico (v3.4)
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

:: Install/upgrade dependencies
echo [3/3] Installazione dipendenze...
python -m pip install --upgrade pip --quiet 2>nul
pip install -r requirements.txt --quiet 2>nul
echo [OK] Dipendenze installate.
echo.

echo ======================================
echo   Avvio applicazione...
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
