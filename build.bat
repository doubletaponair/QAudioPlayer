@echo off
REM ---------------------------------------------------------------
REM Build QAudioPlayer.exe using PyInstaller.
REM
REM If nvdaControllerClient64.dll is present in this folder, it is
REM bundled inside the .exe automatically - you end up with a truly
REM standalone single-file .exe that still speaks through NVDA.
REM
REM Prerequisites:
REM   - Python 3.10+ (64-bit) on PATH
REM   - VLC 64-bit installed (used at runtime, not bundled)
REM   - pip install -r requirements.txt
REM   - pip install pyinstaller
REM ---------------------------------------------------------------

echo.
echo ========================================
echo Building QAudioPlayer.exe
echo ========================================
echo.

if exist "nvdaControllerClient64.dll" (
    echo Found nvdaControllerClient64.dll - bundling it into the .exe.
    echo.
    pyinstaller ^
      --noconfirm ^
      --onefile ^
      --windowed ^
      --name "QAudioPlayer" ^
      --clean ^
      --add-binary "nvdaControllerClient64.dll;." ^
      main.py
) else (
    echo WARNING: nvdaControllerClient64.dll was not found in this folder.
    echo The .exe will be built without it. NVDA announcements ^(R, T, V^)
    echo will not speak until the DLL is copied next to QAudioPlayer.exe.
    echo.
    pyinstaller ^
      --noconfirm ^
      --onefile ^
      --windowed ^
      --name "QAudioPlayer" ^
      --clean ^
      main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Build FAILED.
    echo ========================================
    echo.
    echo If you saw an error about pyinstaller not being recognised,
    echo run:  pip install pyinstaller
    echo.
    exit /b 1
)

echo.
echo ========================================
echo Build complete.
echo ========================================
echo.
echo Your .exe is at:  dist\QAudioPlayer.exe
echo.
echo Double-click it to launch, or associate it with media files
echo via Windows Settings ^> Apps ^> Default apps.
echo.
