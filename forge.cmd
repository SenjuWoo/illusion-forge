@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
"%ROOT%.venv\Scripts\python.exe" -m illusionforge %*
