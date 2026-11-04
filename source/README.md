# KillFarm Lite — source code (2.1.1)

Full Python source of **KillFarm Lite.exe** (theHunter: Call of the Wild farm counter), published so anyone — players, antivirus vendors, Nexus Mods moderators — can check exactly what the app does.
*(Code source complet de KillFarm Lite.exe, publié pour que tout le monde puisse vérifier ce que fait l'appli.)*

## What the app does / doesn't do
- ✅ **Reads** the game save (`Documents\Avalanche Studios\COTW\Saves\<SteamID>`): `hunting_log_adf`, `trophy_lodges_adf`, `thp_player_profile_adf` — see `kill_detector.py`, `hunting_log.py`, `last_harvest.py`, `adf.py`. **It never writes to the game or its save.**
- ✅ Writes only its own data in `Documents\KillFarm_Lite` (`farms.json`, `config.json`, `diag_kills.log`) — `config.py`, `farms.py`, `storage.py`.
- ✅ Global hotkeys F7 / F8 / key under Esc with the Windows `RegisterHotKey` API — `hotkey.py`.
- ✅ Overlay windows (always on top, see-through, click-through) with `SetWindowLong` / `SetWindowPos` — `killfarm_lite.py`.
- ✅ A tiny web page for the live overlay, served **only on 127.0.0.1** (this PC), port 8777 — `webbar.py`. Nothing is sent over the Internet.
- ❌ No network access to the Internet, no telemetry, no code injection, no memory reading of the game, no admin rights.

## Why some antivirus engines flag the .exe
The .exe is a **PyInstaller one-file** bundle (Python 3.14 + tkinter + Pillow). It is **not code-signed** and it unpacks itself to a temp folder at start. A few machine-learning engines flag every unsigned PyInstaller one-file exe by default (e.g. "Wacatac.B!ml"). These are false positives: the code is all here.

## Run from source
Python 3.12+ with Pillow: `pip install pillow` then `python killfarm_lite.py` (or `KillFarm_Lite.bat`).
Build the .exe: `construire_exe.bat` (PyInstaller).
Images (`Image/`) are not included here to keep the repo small; they are inside the release.

Made by MrØza. — https://nicolashajker-cmd.github.io/killfarm-lite/ — Discord https://discord.gg/vmB7kEreuW
Fan project, not affiliated with Expansive Worlds / Avalanche Studios.
