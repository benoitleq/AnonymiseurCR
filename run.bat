@echo off
REM Lance l'Anonymiseur de CR en local (http://127.0.0.1:8000)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] Creation de l'environnement Python...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo Demarrage du serveur sur http://127.0.0.1:8000
echo (Ctrl+C pour arreter)
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
