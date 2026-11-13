@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
echo Illusion Forge. Cards are written only where you point --dest.
echo The maker plugin is not copied into a game by this script.
echo.
"%ROOT%.venv\Scripts\python.exe" -m illusionforge doctor
echo.
echo Next: forge compile "honey select 2 female with blue eyes and a wide face"
echo        forge apply --source card.png --dest out\card.png --spec spec.json
echo        forge build-bridge
echo Debug log: set ILLUSIONFORGE_DEBUG=1
