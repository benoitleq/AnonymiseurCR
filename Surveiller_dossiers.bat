@echo off
REM Surveille les dossiers definis dans config.json et anonymise les PDF deposes.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Premier lancement : installation en cours, merci de patienter...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo.
echo === Surveillance des dossiers (voir config.json) ===
echo Depose un PDF dans un dossier surveille : une version ANOM_*.pdf est creee a cote.
echo Fermez cette fenetre (ou Ctrl+C) pour arreter.
echo.
.venv\Scripts\python.exe watcher.py
pause
