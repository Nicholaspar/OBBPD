@echo off
cls
echo ================================
echo 🔧 OBBPD Build Troubleshooter
echo ================================

REM === Step 1: Confirm Python is Installed
echo.
echo [1] Checking Python installation...
where python >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Python not found. Please install Python and make sure it's added to PATH.
    goto end
) ELSE (
    echo ✅ Python found.
)

REM === Step 2: Confirm PyInstaller is Installed
echo.
echo [2] Checking PyInstaller installation...
pyinstaller --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ PyInstaller not found.
    echo 👉 Run: pip install pyinstaller
    goto end
) ELSE (
    echo ✅ PyInstaller is installed.
)

REM === Step 3: Check for required files
echo.
echo [3] Checking required files...

IF NOT EXIST OBBPD.py (
    echo ❌ Missing: OBBPD.py
    goto end
)
IF NOT EXIST obbpd_config.ini (
    echo ❌ Missing: obbpd_config.ini
    goto end
)
IF NOT EXIST version.txt (
    echo ❌ Missing: version.txt
    goto end
)
IF NOT EXIST OBBPD_oblivion_themed_transparent.ico (
    echo ❌ Missing: OBBPD_oblivion_themed_transparent.ico
    goto end
)
echo ✅ All required files found.

REM === Step 4: Start Build Process
echo.
echo [4] Running PyInstaller...

pyinstaller --onefile --name "OBBPD" ^
--icon "OBBPD_oblivion_themed_transparent.ico" ^
--version-file "version.txt" ^
--add-data "obbpd_config.ini;." ^
OBBPD.py

IF EXIST dist\OBBPD.exe (
    echo.
    echo ✅ Build successful! EXE created at: dist\OBBPD.exe
) ELSE (
    echo.
    echo ❌ Build failed. Please review the error messages above.
)

:end
echo.
echo ===================================
echo 🧪 Build process complete.
echo (This window will stay open.)
echo ===================================
pause