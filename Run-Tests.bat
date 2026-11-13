@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "%ROOT%"
"%ROOT%.venv\Scripts\python.exe" -m unittest discover -s tests -v
exit /b %ERRORLEVEL%
