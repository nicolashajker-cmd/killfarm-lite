# KillFarm Lite 2.1.1 — code source

Code source complet de **KillFarm Lite** (Python 3 + tkinter + Pillow), publié pour que tout le monde puisse vérifier ce que fait l'appli.
Full source code of **KillFarm Lite** (Python 3 + tkinter + Pillow), published so anyone can check what the app does.

## Ce que fait l'appli / What the app does
- **Lit seulement** la sauvegarde du jeu (`Documents\Avalanche Studios\COTW\Saves\<SteamID>`) : `hunting_log_adf` (bêtes ramassées) et `trophy_lodges_adf` (dernière bête). Voir `kill_detector.py`, `hunting_log.py`, `last_harvest.py`, `adf.py`.
  **Only reads** the game save. It never writes to the game or its files.
- Écrit seulement dans `Documents\KillFarm_Lite` (farms.json, config.json, diag_kills.log). Voir `config.py`, `farms.py`, `storage.py`.
  Only writes to `Documents\KillFarm_Lite`.
- Touches F7 / F8 / ² : `RegisterHotKey` de Windows (`hotkey.py`), pas de keylogger.
  F7 / F8 hotkeys use the Windows `RegisterHotKey` API (`hotkey.py`), no keyboard hook.
- Barre du live : petit serveur web **local uniquement** sur `127.0.0.1:8777` (`webbar.py`). Rien n'est envoyé sur Internet.
  Live overlay: a **local-only** web server on `127.0.0.1:8777` (`webbar.py`). Nothing is sent over the Internet.
- Fenêtres toujours devant le jeu, coins arrondis, barre de titre sombre : appels Windows `SetWindowPos`, `SetWindowRgn`, `DwmSetWindowAttribute` (`killfarm_lite.py`).

## Le .exe
Le fichier `KillFarm Lite.exe` des releases est ce code empaqueté avec **PyInstaller** (un seul fichier, Python 3.14).
Certains antivirus « par intelligence artificielle » signalent parfois les .exe PyInstaller non signés : c'est une fausse alerte connue.
The release `KillFarm Lite.exe` is this code packed with **PyInstaller** (one file, Python 3.14). Some AI/heuristic antivirus engines flag unsigned PyInstaller executables: a known false positive.

Lancer depuis le code / Run from source : `python killfarm_lite.py` (Python 3.12+, `pip install pillow`).

Images (logos des bêtes, des réserves, badges) : dans le .exe et le zip de la release.

by MrØza. · https://nicolashajker-cmd.github.io/killfarm-lite/ · Discord https://discord.gg/vmB7kEreuW
