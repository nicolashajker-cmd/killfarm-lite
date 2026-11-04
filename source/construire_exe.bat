@echo off
chcp 65001 >nul
title Construire KillFarm Lite.exe
cd /d "%~dp0"
where py >nul 2>nul && (py -3 construire_exe.py & goto :fin)
python construire_exe.py
:fin
pause
