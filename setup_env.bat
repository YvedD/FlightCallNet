@echo off
REM =========================================================
REM FlightCallNet – volledige omgevingssetup (Windows)
REM =========================================================

echo.
echo === FlightCallNet environment setup ===
echo.

REM -------- PROJECT PAD --------
set "PROJECT_ROOT=C:\RPiProjects\FlightCallNet"
set "VENV_SCRIPTS=%PROJECT_ROOT%\.venv\Scripts"
set "FFMPEG_BIN=C:\FFmpeg\bin"

REM -------- NAAR PROJECT --------
cd /d "%PROJECT_ROOT%" || (
    echo [ERROR] Project map niet gevonden!
    pause
    exit /b 1
)

REM -------- PYTHON VENV --------
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment ontbreekt, wordt aangemaakt...
    python -m venv .venv || (
        echo [ERROR] venv kon niet worden aangemaakt
        pause
        exit /b 1
    )
)

REM -------- VENV ACTIVEREN --------
call ".venv\Scripts\activate.bat" || (
    echo [ERROR] Kon venv niet activeren
    pause
    exit /b 1
)

echo [OK] Virtual environment actief

REM -------- PERMANENTE PATH SET --------
echo.
echo [INFO] PATH permanent bijwerken (user-level)

setx PATH "%VENV_SCRIPTS%;%FFMPEG_BIN%;%PATH%" >nul

echo [OK] PATH aangepast
echo.

REM -------- CONTROLES --------
echo === Controle ===
echo Python:
python --version

echo.
echo Pip:
pip --version

echo.
echo FFmpeg:
ffmpeg -version >nul 2>&1 && echo FFmpeg OK || echo FFmpeg NIET gevonden

echo.
echo === Klaar ===
echo Nieuwe terminals gebruiken nu automatisch deze setup
echo.
pause
