"""Trouve la sauvegarde Steam de COTW."""
import os
import re
from pathlib import Path

WATCHED_PREFIXES = ("animal_population_", "hunting_log_adf", "statistics_adf", "found_icons_")
BACKUP_MARKERS = (" - copie", " - copy")
BACKUP_SUFFIXES = (".bak", ".old", ".tmp")


def documents_dir():
    """Dossier « Documents » de Windows, même déplacé (OneDrive, autre disque) : on demande à Windows."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
            guid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            ptr = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ptr)) == 0 and ptr.value:
                path = Path(ptr.value)
                ctypes.windll.ole32.CoTaskMemFree(ptr)
                return path
        except Exception:
            pass
        try:                                                    # ancienne méthode
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


def save_roots():
    """Tous les endroits plausibles du dossier Saves (Documents normal, déplacé, OneDrive FR/EN)."""
    tail = Path("Avalanche Studios") / "COTW" / "Saves"
    home = Path.home()
    bases = [documents_dir(), home / "Documents"]
    for od in home.glob("OneDrive*"):
        bases += [od / "Documents", od / "Mes documents"]
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial", "USERPROFILE"):   # variables Windows de CE PC
        v = os.environ.get(var)
        if v:
            bases += [Path(v) / "Documents", Path(v) / "Mes documents"]
    out, seen = [], set()
    for b in bases:
        p = b / tail
        if str(p).lower() not in seen:
            seen.add(str(p).lower())
            out.append(p)
    return out


def looks_like_saves_dir(p):
    """Vrai si le dossier contient une sauvegarde COTW (hunting_log_adf)."""
    try:
        p = Path(p)
        return p.is_dir() and any((p / n).exists() for n in ("hunting_log_adf", "thp_player_profile_adf", "statistics_adf"))
    except OSError:
        return False


def desktop_candidates():
    home = Path.home()
    cands = [home / "Desktop", home / "Bureau"]
    for onedrive in home.glob("OneDrive*"):
        cands += [onedrive / "Desktop", onedrive / "Bureau"]
    return cands


def is_backup(name):
    low = name.lower()
    return any(m in low for m in BACKUP_MARKERS) or low.endswith(BACKUP_SUFFIXES)


def find_saves_dir(cfg):
    """Dossier Saves\\<SteamID> à lire : celui forcé dans config.json, sinon le plus récemment modifié
    (plusieurs comptes Steam sur le même PC -> on prend celui avec lequel tu viens de jouer)."""
    forced = cfg.get("saves_dir", "auto")
    if forced and forced != "auto":
        p = Path(forced)
        return p if p.is_dir() else None
    best, best_time = None, -1
    for root in save_roots():
        if not root.is_dir():
            continue
        for sub in root.iterdir():
            if sub.is_dir() and sub.name.isdigit():       # dossier = SteamID64
                try:
                    t = max([f.stat().st_mtime for f in sub.iterdir()] or [0])
                except OSError:
                    t = 0
                if looks_like_saves_dir(sub):
                    t += 1e10                              # un vrai dossier de sauvegarde passe avant un dossier vide
                if t > best_time:
                    best, best_time = sub, t
    return best


def snapshot(saves_dir):
    """{nom_fichier: (mtime_ns, taille)} pour les fichiers utiles (hors copies de secours)."""
    out = {}
    try:
        for f in Path(saves_dir).iterdir():
            if f.is_file() and f.name.startswith(WATCHED_PREFIXES) and not is_backup(f.name):
                st = f.stat()
                out[f.name] = (st.st_mtime_ns, st.st_size)
    except OSError:
        pass
    return out


def map_id_from_name(name):
    m = re.search(r"(?:animal_population|found_icons)_(\d+)$", name)
    return int(m.group(1)) if m else None


def latest_map_id(saves_dir):
    snap = snapshot(saves_dir)
    pops = [(v[0], n) for n, v in snap.items() if n.startswith("animal_population_")]
    return map_id_from_name(max(pops)[1]) if pops else None
