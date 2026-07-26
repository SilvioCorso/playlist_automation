@echo off
title Serato Playlist Automation
echo ======================================
echo   Serato Playlist Automation v3.4
echo ======================================
echo.

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Ambiente virtuale attivato.
) else (
    echo [AVVISO] Ambiente virtuale non trovato.
    echo Esegui prima "install.bat" per installare.
    echo.
    echo Tentativo di avvio con Python globale...
)

echo.
echo Avvio applicazione...
echo.

:: Run the application and capture exit code
python main.py

:: If Python crashes, show the error and pause
if errorlevel 1 (
    echo.
    echo ======================================
    echo   ERRORE! L'applicazione si e chiusa in modo imprevisto.
    echo ======================================
    echo.
    echo Controlla sopra per i messaggi di errore.
    echo Se il problema persiste, prova a reinstallare:
    echo   1. Esegui "install.bat"
    echo   2. Poi "run.bat"
    echo.
)

pause
