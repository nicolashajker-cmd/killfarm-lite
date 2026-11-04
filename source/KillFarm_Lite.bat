@echo off
title KillFarm Lite
cd /d "%~dp0"
rem Version partagee : l'appli est dans le dossier fichiers
if exist "fichiers\killfarm_lite.py" cd /d "%~dp0fichiers"
rem Version .exe : rien a installer
if exist "KillFarm Lite.exe" (
  start "" "KillFarm Lite.exe"
  exit /b
)
set "PY="
set "PYW="
where py >nul 2>nul && set "PY=py -3" && set "PYW=pyw -3"
if not defined PY (
  python -c "import tkinter" >nul 2>nul && set "PY=python" && set "PYW=pythonw"
)
if not defined PY goto :nopython
%PY% -c "import PIL" >nul 2>nul || (
  echo Installation de Pillow pour les images, une seule fois...
  %PY% -m pip install --user pillow
)
start "" %PYW% killfarm_lite.py
exit /b
:nopython
echo.
echo  Python n'est pas installe sur ce PC : il faut Python pour lancer KillFarm Lite.
echo  Installation automatique de Python (officiel, gratuit)...
echo.
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo  Termine : ferme cette fenetre et relance KillFarm Lite.bat
echo  Si rien ne s'est installe : https://www.python.org/downloads/  (coche "Add python.exe to PATH")
pause
