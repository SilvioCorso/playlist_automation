@echo off
title Serato Playlist Automation - Build Distribuzione
echo ======================================
echo   Serato Playlist Automation - Build
echo   Creazione .exe distribuzione
echo ======================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato!
    pause
    exit /b 1
)

:: Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Ambiente virtuale attivato.
) else (
    echo [AVVISO] Ambiente virtuale non trovato. Uso Python globale.
)

:: Install PyInstaller if needed
pip install pyinstaller --quiet 2>nul
echo [OK] PyInstaller pronto.

:: Build the executable
echo.
echo [1/2] Compilazione in corso...
pyinstaller --noconfirm ^
    --name "Serato Playlist Automation" ^
    --windowed ^
    --onefile ^
    --icon "NONE" ^
    --add-data "serato_automation;serato_automation" ^
    --hidden-import "serato_automation" ^
    --hidden-import "serato_automation.ui_main" ^
    --hidden-import "serato_automation.track_matcher" ^
    --hidden-import "serato_automation.library_reader" ^
    --hidden-import "serato_automation.crate_writer" ^
    --hidden-import "serato_automation.config" ^
    --hidden-import "serato_automation.playlist_parser" ^
    --hidden-import "serato_automation.playlist_importer" ^
    --hidden-import "serato_automation.log_handler" ^
    --hidden-import "serato_automation.report_generator" ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERRORE] Compilazione fallita!
    echo Controlla gli errori sopra.
    pause
    exit /b 1
)

echo.
echo [2/2] Copia file nella cartella dist...
if not exist "dist\config.json" (
    copy nul "dist\config.json" 2>nul
)

echo.
echo ======================================
echo   BUILD COMPLETATO!
echo ======================================
echo.
echo L'eseguibile si trova in:
echo   dist\Serato Playlist Automation.exe
echo.
echo Per distribuire il software:
echo   1. Copia il file .exe in una cartella
echo   2. Il programma creera' config.json e
echo      la cache automaticamente al primo avvio
echo   3. Nessuna installazione Python necessaria
echo      per l'utente finale!
echo.
echo Per creare un installer completo:
echo   - Usa Inno Setup (gratis) per creare un .exe installer
echo   - Oppure usa NSIS per un installer professionale
echo.
pause
