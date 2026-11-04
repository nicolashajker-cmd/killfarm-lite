"""KillFarm Lite : dossiers et réglages (config.json, modifiable à la main)."""
import copy
import json
import sys
from pathlib import Path

APP_NAME = "KillFarm Lite"
VERSION = "2.1.1"
SIGNATURE = "by MrØza."
TIKTOK_NAME = "@mr.ozattv"
TIKTOK_URL = "https://www.tiktok.com/@mr.ozattv"
DISCORD_URL = "https://discord.gg/vmB7kEreuW"

# Version .exe (PyInstaller) : le dossier de l'appli = celui du .exe
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
# Version .exe « un seul fichier » : data et Image sont rangés DANS le .exe (dossier temporaire _MEIPASS)
RES_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
DATA_DIR = RES_DIR / "data"
IMG_DIR = RES_DIR / "Image"
LOGO_PNG, LOGO_ICO = IMG_DIR / "logo.png", IMG_DIR / "logo.ico"


def _documents():
    try:
        import save_locator
        return save_locator.documents_dir()
    except Exception:
        return Path.home() / "Documents"


# Données du joueur HORS du dossier de l'appli (une mise à jour ne fait rien perdre).
# Un fichier « portable.txt » à côté de l'appli = tout garder dans le dossier de l'appli.
USER_DIR = APP_DIR if (APP_DIR / "portable.txt").exists() else _documents() / "KillFarm_Lite"
CONFIG_PATH = USER_DIR / "config.json"

DEFAULTS = {
    "saves_dir": "auto",            # dossier Saves\<SteamID> du jeu ; « auto » = trouvé tout seul
    "poll_seconds": 1.0,
    "settle_seconds": 1.5,
    "trophy_wait_seconds": 20,
    "mode": "fenetre",              # fenetre | tiktok | stream
    "big": "since",                 # grand chiffre : since (depuis le dernier Great One) | total
    "bar_side": "bas",              # barre Stream : haut | haut_hud | bas
    "bar_opacity": 1.0,
    "bar_live": False,
    "live_window": False,           # fenêtre « KillFarm Lite – Live » (vraie fenêtre, pour TikTok LIVE Studio)
    "live_geo": None,
    "screen": 0,                    # écran de la barre, de la carte et du mini menu (0 = principal)
    "mini": "reduit",               # mini menu au bord de l'écran : ouvert | reduit (logo seul) | off
    "bubble_side": "droite",        # droite | gauche
    "bubble_y": 0.42,               # hauteur (fraction de l'écran)              # barre Stream OPAQUE, visible dans TikTok LIVE Studio / OBS (capture de fenêtre)             # couleur de la barre Stream : 1 = pleine, 0.6 = on voit le jeu à travers
    "tiktok_pos": None,             # [x, y] de la carte TikTok
    "tiktok_size": "M",             # S | M | L
    "hotkeys": {"mode": "F7", "hide": "F8", "lock": "²"},
    "click_through": True,          # carte TikTok et barre Stream : la souris passe à travers (touche ² pour changer)
    "theme": "automne",             # couleur : automne | foret | glace | sang
    "tuto_vu": False,               # tutoriel déjà vu (sinon il s'ouvre au lancement)
    "lang": "auto",                 # langue : auto (celle de Windows) | fr | en
}


def data_path(name):
    return DATA_DIR / name


def load():
    cfg = copy.deepcopy(DEFAULTS)
    try:
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    for k, v in DEFAULTS.items():
        if isinstance(v, dict):
            cfg[k] = {**v, **(cfg.get(k) or {})}
    if cfg.get("card_v") != 2:                              # 1.9 : nouvelle barre (tableau) -> en bas, au centre
        cfg["bar_side"], cfg["card_v"] = "bas", 2
    if cfg.get("card_v", 0) < 3:                            # 2.1 : barre pleine par défaut (textes bien nets)
        cfg["bar_opacity"], cfg["card_v"] = 1.0, 3
    return cfg


def save(cfg):
    USER_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_name("config.json.tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(CONFIG_PATH)
