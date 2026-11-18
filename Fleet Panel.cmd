@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Set up the Python environment described in README.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m runtime.recording.panel --open
if errorlevel 1 pause
