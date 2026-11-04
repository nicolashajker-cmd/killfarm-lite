@echo off
title Partager KillFarm Lite
cd /d "%~dp0"
where py >nul 2>nul && (py -3 partager.py) || (python partager.py)
pause
