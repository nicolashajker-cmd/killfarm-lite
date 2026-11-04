"""KillFarm Lite — compteur de farm simple pour theHunter: Call of the Wild.

- Compte tout seul chaque bête RAMASSÉE de ton farm (lecture de la sauvegarde du jeu, rien n'est modifié).
- Grades du farm : sans médaille, bronze, argent, or, diamant, Great One (Great One reconnu dans la sauvegarde).
- 3 affichages : Fenêtre, carte TikTok (à capturer dans OBS / à filmer), barre Stream le long de l'écran.
- « ▶ Lancer un farm » : la réserve, l'animal, c'est parti (ou « farmer la dernière bête ramassée » en 1 clic).
Raccourcis : F7 = changer d'affichage, F8 = cacher / montrer (modifiables dans config.json).
"""
import os
import queue
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import config
import farms as fm
import lang
from lang import T
import gamedata as gd
import hunting_log
import last_harvest
import referentiel
import save_locator
from hotkey import HotkeyManager
from kill_detector import KillDetector
import webbar

# ---- palette (automne : bruns, orange feuille, or) ----
BG, PANEL, CARD, BTN, EDGE = "#1c130d", "#2b1d14", "#1f150e", "#4a3222", "#5a3d29"
ACC, GOLD, LEAF, FG, DIM = "#e8791d", "#f2b84b", "#a9c35a", "#f7ecd9", "#bda78d"
# Couleurs au choix (⚙ > Couleur) : appliquées à la fenêtre, à la carte TikTok et à la barre Stream.
THEMES = {
    "automne": ("Automne (orange)", dict(BG="#1c130d", PANEL="#2b1d14", CARD="#1f150e", BTN="#4a3222", EDGE="#5a3d29",
                                         ACC="#e8791d", GOLD="#f2b84b", LEAF="#a9c35a", FG="#f7ecd9", DIM="#bda78d")),
    "foret": ("Forêt (vert)", dict(BG="#0f1a12", PANEL="#17271b", CARD="#122016", BTN="#24402b", EDGE="#2f5236",
                                   ACC="#6cc04a", GOLD="#e3c55a", LEAF="#b6e35d", FG="#eaf3e3", DIM="#9fb59a")),
    "glace": ("Glace (bleu)", dict(BG="#0d1620", PANEL="#15222f", CARD="#101b26", BTN="#1f3346", EDGE="#2a4660",
                                   ACC="#4fb3e8", GOLD="#f2d27a", LEAF="#8fe0a0", FG="#eaf4fb", DIM="#93acc0")),
    "sang": ("Sang (rouge)", dict(BG="#160b0b", PANEL="#241212", CARD="#1b0d0d", BTN="#3d1a1a", EDGE="#5a2424",
                                  ACC="#e0392b", GOLD="#f2b84b", LEAF="#b6e35d", FG="#f8e9e6", DIM="#c09a94")),
    # couleurs des plateformes (TikTok : rose #FE2C55 + cyan #25F4EE ; Twitch : violet #9146FF ; YouTube : rouge #FF0033)
    "tiktok": ("TikTok (rose et cyan)", dict(BG="#0b0b10", PANEL="#16161e", CARD="#111118", BTN="#24242f", EDGE="#34344a",
                                             ACC="#fe2c55", GOLD="#25f4ee", LEAF="#25f4ee", FG="#ffffff", DIM="#a4a4b8")),
    "twitch": ("Twitch (violet)", dict(BG="#0e0e10", PANEL="#18181b", CARD="#141417", BTN="#27272e", EDGE="#3b3b46",
                                       ACC="#9146ff", GOLD="#bf94ff", LEAF="#00f593", FG="#efeff1", DIM="#adadb8")),
    "youtube": ("YouTube (rouge)", dict(BG="#0f0f0f", PANEL="#1c1c1c", CARD="#161616", BTN="#2a2a2a", EDGE="#3f3f3f",
                                        ACC="#ff0033", GOLD="#ffb12b", LEAF="#3ea6ff", FG="#f1f1f1", DIM="#aaaaaa")),
}


def apply_theme(name):
    """Change les couleurs (variables du module) ; thème inconnu = Automne. -> clé du thème appliqué."""
    name = name if name in THEMES else "automne"
    globals().update(THEMES[name][1])
    return name


KEY = "#010203"                                              # couleur rendue transparente (coins des overlays)
GRADE_COL = {5: "#b6e35d", 4: "#8fd8ea", 3: "#f2b84b", 2: "#d6d2cc", 1: "#d08a56", 0: "#bda78d"}
UI, NUM = "Segoe UI", "Bahnschrift"                          # Bahnschrift : chiffres serrés (Windows 10+) ; sinon Segoe
BAR_SIDES = (("bas", "En bas, au centre (conseillé)"), ("haut", "En haut, au centre"),
             ("haut_hud", "En haut, sous la barre du jeu"))     # textes passés par T()
BAR_OPACITY = ((1.0, "Pleine (conseillé : textes bien nets)"), (0.8, "80 %"), (0.6, "60 %"), (0.4, "40 %"),
               (0.25, "25 % (très transparente)"))
MODES = ("fenetre", "tiktok", "stream")
MODE_NAMES = {"fenetre": "Fenêtre", "tiktok": "TikTok", "stream": "Stream"}
WIN = os.name == "nt"


def full_app_dir():
    """Lite rangé dans le dossier de l'appli complète (Cotw_KillFarm\\KillFarm_Lite) : dossier de Cotw_KillFarm, sinon None."""
    d = config.APP_DIR.parent
    if ((d / "Kill_Farm.exe").exists() or (d / "Cotw_KillFarm.exe").exists()) and (d / "data" / "especes.json").exists():
        return d                                            # appli complète en .exe
    if getattr(sys, "frozen", False):
        return None
    return d if (d / "main.py").exists() and (d / "hud.py").exists() and (d / "choix_appli.py").exists() else None


def fmt(n):
    return f"{int(n):,}".replace(",", lang.THOUSANDS)


def kills(n):
    """« 1 kill », « 2 kills », « 12 386 kills »."""
    n = int(n or 0)
    return f"{fmt(n)} kill{'s' if n > 1 else ''}"


def fname(f):
    """Nom de la bête du farm, dans la langue de l'appli (le nom FR reste enregistré dans farms.json)."""
    sp = gd.species_by_en(f.get("species_en")) if f else None
    return gd.name(sp) if sp else (f or {}).get("name", "")


def fres(f):
    """Réserve du farm, dans la langue de l'appli."""
    rid = (f or {}).get("rid")
    if rid in gd.BY_RID:
        return gd.reserve_label(rid)
    return T((f or {}).get("reserve") or "")


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, t):
    a, b = hex_rgb(c1), hex_rgb(c2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def rounded(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
           x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def fit_font(text, family, size, maxw, weight="bold", min_size=10):
    """Police la plus grande (<= size) dans laquelle le texte tient en maxw pixels."""
    f = tkfont.Font(family=family, size=size, weight=weight)
    while size > min_size and f.measure(text) > maxw:
        size -= 2
        f.configure(size=size)
    return f


def short_num(n):
    """Nombre court pour les petites cases : 12 386 -> 12,4k ; 1 234 567 -> 1,23M."""
    n = int(n)
    if n < 10000:
        return fmt(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}k".replace(".0k", "k").replace(".", lang.DECIMAL)
    return f"{n / 1_000_000:.2f}M".replace(".", lang.DECIMAL)


def fit(text, font, maxw):
    if font.measure(text) <= maxw:
        return text
    while text and font.measure(text + "…") > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def monitors():
    """Écrans du PC : [(x, y, largeur, hauteur)], l'écran principal en premier."""
    out = []
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class MI(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                            ("dwFlags", wintypes.DWORD)]
            u32 = ctypes.windll.user32
            proto = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                       wintypes.LPARAM)

            def cb(hmon, hdc, rc, lp):
                mi = MI()
                mi.cbSize = ctypes.sizeof(MI)
                if u32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    r = mi.rcMonitor
                    out.append((r.left, r.top, r.right - r.left, r.bottom - r.top, bool(mi.dwFlags & 1)))
                return 1
            u32.EnumDisplayMonitors(None, None, proto(cb), 0)
        except Exception:
            out = []
    if not out:
        return [(0, 0, None, None)]
    out.sort(key=lambda m: (not m[4], m[0]))                # principal d'abord, puis de gauche à droite
    return [m[:4] for m in out]


class RButton(tk.Canvas):
    """Bouton ARRONDI en relief (ombre dessous, reflet dessus, survol plus clair, enfoncé au clic).
    Même usage qu'un tk.Button : text, command, bg, fg, state, width (en caractères), font."""

    def __init__(self, parent, text="", command=None, bg=None, fg=None, font=None, padx=12, pady=6, width=None,
                 radius=9, **_ignored):
        try:
            pbg = parent.cget("bg")
        except tk.TclError:
            pbg = BG
        super().__init__(parent, bg=pbg, highlightthickness=0, bd=0, cursor="hand2")
        self._o = dict(text=text, command=command, bg=bg or BTN, fg=fg or FG, font=font or (UI, 9),
                       state="normal", width=width)
        self._px, self._py, self._r = padx, pady, radius
        self._hover = self._down = False
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._draw())
        self._size()

    # API « comme tk.Button »
    def configure(self, cnf=None, **kw):
        mine = {k: kw.pop(k) for k in list(kw) if k in ("text", "command", "bg", "fg", "font", "state", "width",
                                                        "activebackground", "activeforeground", "padx", "pady")}
        for k in ("activebackground", "activeforeground"):
            mine.pop(k, None)
        if "padx" in mine:
            self._px = mine.pop("padx")
        if "pady" in mine:
            self._py = mine.pop("pady")
        self._o.update(mine)
        if cnf or kw:
            super().configure(cnf, **kw)
        if mine or not (cnf or kw):
            self._size()
    config = configure

    def cget(self, key):
        return self._o[key] if key in self._o else super().cget(key)

    def invoke(self):
        if self._o["state"] != "disabled" and self._o["command"]:
            self._o["command"]()

    def _font(self):
        f = self._o["font"]
        return f if isinstance(f, tkfont.Font) else tkfont.Font(font=f)

    def _size(self):
        f = self._font()
        tw = f.measure(self._o["text"]) if self._o["width"] is None else f.measure("0") * int(self._o["width"])
        super().configure(width=tw + 2 * self._px + 2, height=f.metrics("linespace") + 2 * self._py + 3)
        self._draw()

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    def _press(self, e):
        if self._o["state"] != "disabled":
            self._down = True
            self._draw()

    def _release(self, e):
        was = self._down
        self._down = False
        self._draw()
        if was and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.invoke()

    def _draw(self):
        self.delete("all")
        w, h = max(self.winfo_width(), int(super().cget("width"))), max(self.winfo_height(), int(super().cget("height")))
        if w < 4 or h < 4:
            return
        r, col, fg = self._r, self._o["bg"], self._o["fg"]
        off = self._o["state"] == "disabled"
        if off:
            col, fg = mix(col, BG, 0.5), mix(fg, BG, 0.5)
        elif self._down:
            col = mix(col, "#000000", 0.18)
        elif self._hover:
            col = mix(col, "#ffffff", 0.12)
        dy = 1 if self._down else 0
        rounded(self, 1, 3, w - 1, h - 1, r, fill=mix(col, "#000000", 0.55), outline="")          # ombre
        rounded(self, 1, 1 + dy, w - 1, h - 3 + dy, r, fill=col, outline=mix(col, "#ffffff", 0.18))  # corps
        rounded(self, 3, 2 + dy, w - 3, (h - 3) / 2 + dy, max(2, r - 3),                        # reflet
                fill=mix(col, "#ffffff", 0.10), outline="")
        self.create_text(w / 2, (h - 2) / 2 + dy, text=self._o["text"], fill=fg, font=self._o["font"])


def win_dark(w):
    """Barre de titre Windows en SOMBRE (au lieu du blanc) : Windows 10 (1809+) et 11."""
    if os.name != "nt":
        return
    try:
        import ctypes
        w.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(w.winfo_id()) or w.winfo_id()
        on = ctypes.c_int(1)
        for attr in (20, 19):                               # DWMWA_USE_IMMERSIVE_DARK_MODE (nouveau, ancien)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                break
        pref = ctypes.c_int(2)                              # Windows 11 : coins arrondis
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), 4)
    except Exception:
        pass


def win_round(w, r=18):
    """Coins ARRONDIS pour une fenêtre sans bordure (mini menu, boîtes de l'appli)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        w.update_idletasks()
        hwnd = int(w.wm_frame(), 16)
        ww, hh = w.winfo_width(), w.winfo_height()
        if getattr(w, "_rgn_size", None) == (ww, hh):
            return
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, ww + 1, hh + 1, r, r)
        ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        w._rgn_size = (ww, hh)
    except Exception:
        pass


class Pics:
    """Images redimensionnées (Pillow si présent, sinon tkinter) ; bulles rondes avec liseré."""

    def __init__(self):
        try:
            from PIL import Image, ImageDraw, ImageTk
            self.pil = (Image, ImageDraw, ImageTk)
        except ImportError:
            self.pil = None
        self.cache = {}

    def get(self, path, size, circle=False, ring=None, back=None, hard=False):
        """hard = bords nets (alpha 0 ou 255) : pour les fenêtres à couleur transparente (pas de liseré sombre)."""
        if not path:
            return None
        back = back or CARD
        k = (str(path), size, circle, ring, back, hard)
        if k in self.cache:
            return self.cache[k]
        img = None
        try:
            if self.pil:
                Image, ImageDraw, ImageTk = self.pil
                im = Image.open(path).convert("RGBA")
                w, h = im.size
                s = min(w, h)
                im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
                ss = size * 3
                im = im.resize((ss, ss), Image.LANCZOS)
                if circle:
                    disc = Image.new("RGBA", (ss, ss), hex_rgb(back) + (255,))
                    inner = round(ss * 0.68)                # marge : le blanc de la bête ne touche plus le rond
                    small = im.resize((inner, inner), Image.LANCZOS)
                    disc.alpha_composite(small, ((ss - inner) // 2, (ss - inner) // 2))
                    mask = Image.new("L", (ss, ss), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, ss - 1, ss - 1), fill=255)
                    out = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
                    out.paste(disc, (0, 0), mask)
                    if ring:
                        ImageDraw.Draw(out).ellipse((2, 2, ss - 3, ss - 3), outline=hex_rgb(ring) + (255,), width=3 * 3)
                    im = out
                im = im.resize((size, size), Image.LANCZOS)
                if hard:
                    a = im.getchannel("A").point(lambda v: 255 if v >= 110 else 0)
                    im.putalpha(a)
                img = ImageTk.PhotoImage(im)
            else:
                ph = tk.PhotoImage(file=str(path))
                f = max(1, round(ph.width() / size))
                img = ph.subsample(f, f)
        except Exception:
            img = None
        self.cache[k] = img
        return img


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = config.load()
        self.cfg["theme"] = apply_theme(self.cfg.get("theme"))
        lang.set_lang(self.cfg.get("lang", "auto"))
        self.lien = None
        if full_app_dir():                                   # rangé dans Kill_Farm : mêmes farms que l'appli complète
            try:
                import lien
                self.lien = lien.Lien(full_app_dir())
            except Exception:
                self.lien = None
        self.farms = fm.Farms(self.lien)
        self.farms.sync()
        for f in self.farms.farms.values():                  # nom français à jour (orthographe corrigée)
            sp = gd.species_by_en(f.get("species_en"))
            if sp:
                f["name"] = gd.fr_name(sp)
        self.pics = Pics()
        self.events, self.hk = queue.Queue(), queue.Queue()
        self.map_id = None
        self.saves = None
        self.suggest = None                                  # dernière bête ramassée sans farm : (en, nom, rid)
        self.anim = None                                     # (début, grade) : « +1 » / « GREAT ONE ! »
        self.status = T("Recherche de ta sauvegarde…")
        self.hidden = False
        self.mode = None
        self.tiktok = self.stream = self.stream_bg = None
        self._front = None                                   # l'appli a le focus : ses fenêtres passent devant la barre
        root.title(f"{config.APP_NAME} {config.VERSION}")
        self._set_icon()
        root.configure(bg=BG)
        root.resizable(False, False)
        self._style()
        self._build_window()
        root.after(30, lambda: win_dark(root))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(50, self._start)

    # ================================================================ démarrage
    def _set_icon(self):
        """Logo de l'appli : barre de titre, barre des tâches, Alt+Tab."""
        try:
            if WIN and config.LOGO_ICO.exists():
                self.root.iconbitmap(default=str(config.LOGO_ICO))
            img = self.pics.get(config.LOGO_PNG, 64) if config.LOGO_PNG.exists() else None
            if img:
                self.root.iconphoto(True, img)
        except tk.TclError:
            pass

    def make_shortcut(self, quiet=False):
        """Raccourci « KillFarm Lite » sur le Bureau, avec le logo (Windows)."""
        if not WIN:
            return False
        import subprocess
        if getattr(sys, "frozen", False):
            target, args = sys.executable, ""
        else:
            exe = Path(sys.executable)
            pyw = exe.with_name("pythonw.exe")
            target, args = str(pyw if pyw.exists() else exe), f'"{config.APP_DIR / "killfarm_lite.py"}"'
        ps = ("$d=[Environment]::GetFolderPath('Desktop');"
              "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'KillFarm Lite.lnk'));"
              f"$s.TargetPath='{target}';$s.Arguments='{args}';$s.WorkingDirectory='{config.APP_DIR}';"
              f"$s.IconLocation='{target if getattr(sys, 'frozen', False) else config.LOGO_ICO},0';"
              "$s.Description='KillFarm Lite - compteur de farm';$s.Save()")
        try:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           check=True, timeout=20, creationflags=0x08000000)       # CREATE_NO_WINDOW
            ok = True
        except Exception:
            ok = False
        if not quiet:
            if ok:
                messagebox.showinfo(config.APP_NAME, T("Raccourci « KillFarm Lite » créé sur ton Bureau."), parent=self.root)
            else:
                messagebox.showwarning(config.APP_NAME, T("Je n'ai pas pu créer le raccourci. Lance l'appli en "
                                       "double-cliquant sur « KillFarm Lite.exe »."), parent=self.root)
        return ok

    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TSpinbox", fieldbackground=PANEL, background=BTN, foreground=FG, arrowcolor=FG, bordercolor=EDGE)
        st.configure("Vertical.TScrollbar", background=BTN, troughcolor=PANEL, arrowcolor=FG, bordercolor=EDGE)

    def _start(self):
        webbar.start()
        self.render()
        self.saves = save_locator.find_saves_dir(self.cfg)
        if not self.saves:
            messagebox.showinfo(
                config.APP_NAME,
                T("Je ne trouve pas la sauvegarde de theHunter: Call of the Wild.\n\n"
                  "Choisis le dossier :  Documents > Avalanche Studios > COTW > Saves > (ton numéro Steam).\n\n"
                  "Astuce : lance le jeu une fois avant, pour que la sauvegarde existe."), parent=self.root)
            self.pick_saves(restart=False)
        if self.saves:
            self.detector = KillDetector(self.cfg, self.saves, self.events)
            self.detector.start()
            self.status = T("Sauvegarde trouvée ✓ · le compteur suit tes bêtes ramassées") + (
                f"\nFarms {self.farms.lien.label()}" if self.farms.lien else "")
            self._last_from_save()
        else:
            self.status = T("Pas de sauvegarde : compteur à la main seulement (⚙ > Dossier de sauvegarde)")
        HotkeyManager(self.cfg["hotkeys"], self.hk).start()
        self.set_mode(self.cfg.get("mode", "fenetre"), save=False)
        self.render()
        if not self.cfg.get("tuto_vu"):                       # 1er lancement : le tutoriel s'ouvre tout seul
            self.cfg["nouveautes_vues"] = config.VERSION      # (nouveau joueur : pas d'affiche de mise à jour)
            config.save(self.cfg)
            self.root.after(700, self.tutorial)
        elif self.cfg.get("nouveautes_vues") != config.VERSION and not full_app_dir():
            self.root.after(600, self.news)                   # mise à jour : l'affiche des nouveautés, une fois
        self.root.after(250, self._poll)

    def _last_from_save(self):
        """Dernière bête du journal de chasse : proposée pour lancer un farm en 1 clic."""
        try:
            entries = hunting_log.read_harvests(Path(self.saves) / "hunting_log_adf")
            e = max(entries, key=lambda x: x["Timestamp"])
        except Exception:
            return
        sp = referentiel.species_by_hash(e["SpeciesName"])
        if not sp:
            return
        rid = save_locator.latest_map_id(self.saves)
        try:
            lh = last_harvest.read_last(Path(self.saves) / "trophy_lodges_adf")
            if last_harvest.matches(e, lh):
                rid = int(lh["HarvestReserve"])
        except Exception:
            pass
        self.map_id = rid
        if not self.farms.match(sp["en"], rid):
            self.suggest = (sp["en"], gd.name(sp), rid, None)

    def pick_saves(self, restart=True):
        d = filedialog.askdirectory(title=T("Dossier Saves\\(numéro Steam) de theHunter"), parent=self.root,
                                    initialdir=str(save_locator.documents_dir() / "Avalanche Studios" / "COTW" / "Saves"))
        if not d:
            return
        if not save_locator.looks_like_saves_dir(Path(d)):
            if not messagebox.askyesno(config.APP_NAME, T("Ce dossier ne ressemble pas à une sauvegarde du jeu "
                                       "(pas de fichier hunting_log_adf).\nLe garder quand même ?"), parent=self.root):
                return
        self.cfg["saves_dir"] = d
        config.save(self.cfg)
        self.saves = Path(d)
        if restart:
            messagebox.showinfo(config.APP_NAME, T("C'est noté. Relance KillFarm Lite pour lire cette sauvegarde."),
                                parent=self.root)

    def switch_to_full(self):
        """Ferme Lite et ouvre l'appli complète Cotw_KillFarm (Lite est rangé dans son dossier)."""
        d = full_app_dir()
        if not d:
            return
        import subprocess
        exe = Path(sys.executable)
        pyw = exe.with_name("pythonw.exe")
        full_exe = d / "Kill_Farm.exe" if (d / "Kill_Farm.exe").exists() else d / "Cotw_KillFarm.exe"
        if full_exe.exists() and (getattr(sys, "frozen", False) or not (d / "main.py").exists()):
            cmd = [str(full_exe), "--normal"]               # version .exe : pas besoin de Python
        else:
            cmd = [str(pyw if pyw.exists() else exe), str(d / "main.py"), "--normal"]
        try:
            subprocess.Popen(cmd, cwd=str(d), creationflags=0x08000000 if WIN else 0)
        except OSError:
            messagebox.showerror(config.APP_NAME, T("Je n'ai pas pu ouvrir Kill_Farm."), parent=self.root)
            return
        self.quit()

    def quit(self):
        webbar.stop()
        try:
            if getattr(self, "detector", None):
                self.detector.stop()
        finally:
            self.root.destroy()

    # ================================================================ événements
    def _poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev["type"] == "map":
                    self.map_id = ev["map_id"]
                elif ev["type"] == "kill":
                    self.on_kill(ev)
        except queue.Empty:
            pass
        try:
            while True:
                kind, name = self.hk.get_nowait()
                if kind == "hotkey" and name == "mode":
                    self.cycle_mode()
                elif kind == "hotkey" and name == "hide":
                    self.toggle_hidden()
                elif kind == "hotkey" and name == "lock":
                    self.toggle_lock()
                elif kind != "hotkey":
                    self.status = T("Raccourci déjà pris par une autre appli : {name}", name=name)
                    self.render()
        except queue.Empty:
            pass
        self._tick = getattr(self, "_tick", 0) + 1
        front = self._we_have_focus()
        if self._tick % 8 == 0 or front != bool(self._front):
            self._keep_on_top(front)
        if self._tick % 8 == 0 and self.farms.lien and self.farms.lien.changed_outside():
            if self.farms.sync():                            # l'appli complète a changé ses farms : on suit
                self.render()
        if self._tick % 8 == 0:
            if self.mode == "stream" and getattr(self, "_clock_shown", None) != time.strftime("%H:%M"):
                self.render()
        self.root.after(250, self._poll)

    def _diag_kill(self, ev):
        """Journal des bêtes ramassées (Documents\\KillFarm_Lite\\diag_kills.log) : pour vérifier les Great Ones."""
        try:
            import json as _j
            p = config.USER_DIR / "diag_kills.log"
            lines = p.read_text(encoding="utf-8").splitlines()[-299:] if p.exists() else []
            e = {k: (str(v) if k in ("SpeciesName", "VariationName", "RegionName") else v)
                 for k, v in ev["entry"].items()}
            lines.append(_j.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "entry": e, "last": ev.get("last")},
                                  ensure_ascii=False))
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    def on_kill(self, ev):
        self._diag_kill(ev)
        r, last = ev["entry"], ev.get("last")
        sp = referentiel.species_by_hash(r["SpeciesName"])
        rid = last["reserve"] if last and last.get("reserve") is not None else (ev.get("map_id") or self.map_id)
        if last and last.get("reserve") is not None:
            self.map_id = last["reserve"]
        grade = fm.GO if last and last.get("great") else fm.journal_to_grade(r.get("TrophyScore"))
        name = gd.name(sp) if sp else T("Bête inconnue")
        when = time.strftime("%H:%M", time.localtime(r.get("Timestamp") or time.time()))
        self.status = T("Dernière bête ramassée : {name} · {grade} · {when}", name=name, grade=T(fm.GRADES[grade]), when=when)
        if grade == fm.GO:
            self.status = T("🏆 GREAT ONE ! Compteur remis à 0.") + "\n" + self.status
        if not sp:
            self.render()
            self.ask_unknown(r.get("SpeciesName"), rid, grade, r.get("Timestamp"))
            return
        keys = self.farms.match(sp["en"], rid)
        for k in keys:
            self.farms.add_kill(k, grade, r.get("Timestamp"))
        if keys:
            if self.farms.active not in keys:
                self.farms.set_active(keys[0])
            self.suggest = None
            self.bump(grade)
        else:
            self.suggest = (sp["en"], name, rid, grade)
        self.render()

    def ask_unknown(self, code, rid, grade, ts):
        """Bête que l'appli ne reconnaît pas (nouvelle bête du jeu, nom interne différent) : on te demande laquelle
        c'était, le kill est compté, et l'appli s'en souvient pour les suivantes (especes_apprises.json)."""
        if code is None:
            return
        cands = [k for k in self.farms.order if self.farms.farms[k].get("rid") in (None, rid) or rid is None]
        if not cands:
            self.status = T("Bête ramassée non reconnue : lance son farm, la prochaine sera demandée.")
            self.render()
            return
        old = getattr(self, "_unk", None)
        if old is not None and old.winfo_exists():
            old.destroy()
        w = self._unk = tk.Toplevel(self.root)
        w.title(config.APP_NAME)
        w.configure(bg=BG, padx=16, pady=14)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        res = gd.reserve_label(rid) if rid is not None else T("réserve inconnue")
        tk.Label(w, text=T("Tu viens de ramasser une bête que je ne reconnais pas ({res}, {grade}).", res=res,
                           grade=T(fm.GRADES[grade])),
                 bg=BG, fg=FG, font=(UI, 10, "bold"), wraplength=380, justify="left").pack(anchor="w")
        tk.Label(w, text=T("C'était laquelle ? Elle sera comptée, et je m'en souviendrai pour les prochaines."),
                 bg=BG, fg=DIM, font=(UI, 9), wraplength=380, justify="left").pack(anchor="w", pady=(2, 10))

        def choose(k):
            f = self.farms.farms.get(k)
            w.destroy()
            if not f:
                return
            referentiel.learn(code, gd.canon(f["species_en"]))
            for key in self.farms.match(f["species_en"], rid):
                self.farms.add_kill(key, grade, ts)
            self.farms.set_active(k)
            self.suggest = None
            self.status = T("Retenu : cette bête = {name}. Les prochaines seront comptées toutes seules.", name=fname(f))
            self.bump(grade)
            self.render()

        for k in cands[:8]:
            f = self.farms.farms[k]
            self._btn(w, f"{fname(f)} · {fres(f)}", lambda k=k: choose(k), primary=(k == self.farms.active)).pack(
                fill="x", pady=2)
        self._btn(w, T("Aucune de mes bêtes de farm (ne rien compter)"), w.destroy).pack(fill="x", pady=(8, 0))
        w.update_idletasks()                                  # au milieu de l'écran (pas sous la barre Stream)
        w.geometry(f"+{(w.winfo_screenwidth() - w.winfo_reqwidth()) // 2}+{(w.winfo_screenheight() - w.winfo_reqheight()) // 3}")
        w.lift()

    def bump(self, grade):
        self.anim = (time.time(), grade)
        self._animate()

    def _animate(self):
        if not self.anim:
            return
        if time.time() - self.anim[0] > (3.0 if self.anim[1] == fm.GO else 1.4):
            self.anim = None
            self.render()
            return
        self.render()
        self.root.after(40, self._animate)

    def _anim_t(self):
        if not self.anim:
            return None
        return min(1.0, (time.time() - self.anim[0]) / (3.0 if self.anim[1] == fm.GO else 1.4))

    # ================================================================ actions
    def farm_key(self):
        return self.farms.active

    def plus(self):
        if self.farm_key():
            self.farms.add_kill(self.farm_key(), None, manual=True)
            self.bump(None)

    def minus(self):
        if self.farm_key():
            self.farms.remove_one(self.farm_key())
            self.render()

    def undo(self):
        k = self.farm_key()
        done = self.farms.undo(k) if k else False
        if done == "go":
            self.status = T("Great One retiré : les chiffres sont revenus comme avant.")
        elif done:
            self.status = T("Dernier kill retiré du farm.")
        else:
            self.status = T("Rien à annuler.")
        self.render()

    def grade_menu(self, event, g):
        k = self.farm_key()
        if not k:
            return
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC)
        if g == fm.GO:
            m.add_command(label=T("🏆 Mon dernier kill était un Great One"), command=self.mark_go)
        m.add_command(label=f"+1 {T(fm.GRADES[g])}", command=lambda: (self.farms.add_grade(k, g, 1), self.render()))
        m.add_command(label=f"−1 {T(fm.GRADES[g])}", command=lambda: (self.farms.add_grade(k, g, -1), self.render()))
        m.tk_popup(event.x_root, event.y_root)

    def mark_go(self):
        """Great One pas reconnu tout seul : on le marque à la main (compteur depuis le dernier GO remis à 0)."""
        k = self.farm_key()
        if not k:
            return
        f = self.farms.get(k)
        if f["since_go"] <= 0:
            messagebox.showinfo(config.APP_NAME, T("Aucun kill compté depuis le dernier Great One.\n\n"
                                "Ton Great One n'a pas été compté du tout ? Clique d'abord sur « +1 », puis reviens ici."),
                                parent=self.root)
            return
        if not messagebox.askyesno(config.APP_NAME, T("Ton dernier kill ({name}) était un Great One ?\n\n"
                                   "• Great Ones : {a} → {b}\n"
                                   "• Dernier GO tombé en {k}\n"
                                   "• Le compteur depuis le dernier GO repart de 0\n\n"
                                   "(Erreur ? « ↶ Annuler le dernier kill » remet tout comme avant.)", name=fname(f),
                                   a=f['go_total'], b=f['go_total'] + 1, k=kills(f['since_go'])), parent=self.root):
            return
        self.farms.mark_go(k)
        self.status = T("Great One ajouté. Félicitations ! 🏆")
        self.bump(fm.GO)
        self.render()

    def farms_menu(self, widget=None, event=None):
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG)
        if self.farms.order:
            var = tk.StringVar(value=self.farms.active)
            for k in self.farms.order:
                f = self.farms.farms[k]
                m.add_radiobutton(label=f"{fname(f)} · {fres(f)}   ({kills(f['count'])})", variable=var, value=k,
                                  command=lambda k=k: (self.farms.set_active(k), self.render()))
            m.add_separator()
        m.add_command(label=T("▶ Lancer un nouveau farm…"), command=self.new_farm)
        if self.farm_key():
            m.add_command(label=T("🏆 Mon dernier kill était un Great One…"), command=self.mark_go)
            m.add_command(label=T("✎ Modifier les chiffres du farm…"), command=self.edit_numbers)
            m.add_command(label=T("✕ Supprimer ce farm…"), command=self.delete_farm)
        self._popup(m, widget, event)

    def settings_menu(self, widget=None, event=None):
        """⚙ rangé par thème : Affichage · Live / Stream · Sauvegarde · Aide."""
        st = dict(tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG, font=(UI, 10))
        m = tk.Menu(self.root, **st)
        # --- affichage
        aff = tk.Menu(m, **st)
        big = tk.StringVar(value=self.cfg["big"])
        sub = tk.Menu(aff, **st)
        sub.add_radiobutton(label=T("Kills depuis le dernier Great One"), variable=big, value="since",
                            command=lambda: self._set("big", "since"))
        sub.add_radiobutton(label=T("Total du farm"), variable=big, value="total", command=lambda: self._set("big", "total"))
        aff.add_cascade(label=T("Grand chiffre"), menu=sub)
        size = tk.StringVar(value=self.cfg["tiktok_size"])
        sub2 = tk.Menu(aff, **st)
        for s_, lab in (("S", "Petite"), ("M", "Moyenne"), ("L", "Grande")):
            sub2.add_radiobutton(label=T(lab), variable=size, value=s_, command=lambda s_=s_: self._set("tiktok_size", s_, rebuild=True))
        aff.add_cascade(label=T("Taille de la carte TikTok"), menu=sub2)
        aff.add_cascade(label=T("Écran (barre, carte, mini menu)"), menu=self._screen_menu(aff))
        aff.add_cascade(label=T("Couleur"), menu=self._theme_menu(aff))
        aff.add_cascade(label="Language / Langue", menu=self._lang_menu(aff))
        bv = tk.BooleanVar(value=self._bubble_on())
        aff.add_checkbutton(label=T("Mini menu au bord de l'écran"), variable=bv, command=self.toggle_bubble)
        m.add_cascade(label=T("Affichage"), menu=aff)
        # --- barre stream / live
        lv = tk.Menu(m, **st)
        lv.add_command(label=T("Lien de la barre pour le live (TikTok LIVE Studio / OBS)…"), command=self.web_link)
        side = tk.StringVar(value=self.cfg["bar_side"])
        sub3 = tk.Menu(lv, **st)
        for s_, lab in BAR_SIDES:
            sub3.add_radiobutton(label=T(lab), variable=side, value=s_, command=lambda s_=s_: self._set("bar_side", s_, rebuild=True))
        lv.add_cascade(label=T("Position de la barre"), menu=sub3)
        if not self._live():
            lv.add_cascade(label=T("Transparence de la barre"), menu=self._opacity_menu(lv))
        live = tk.BooleanVar(value=self._live())
        lv.add_checkbutton(label=T("Barre opaque (sans transparence)"), variable=live, command=self.toggle_live)
        lock = tk.BooleanVar(value=bool(self.cfg.get("click_through", True)))
        lv.add_checkbutton(label=T("La souris passe à travers la barre (touche ²)"), variable=lock, command=self.toggle_lock)
        lw = tk.BooleanVar(value=bool(self.cfg.get("live_window")))
        lv.add_checkbutton(label=T("Fenêtre Live (capture de fenêtre)"), variable=lw, command=self.toggle_live_window)
        m.add_cascade(label=T("Barre Stream & live"), menu=lv)
        # --- sauvegarde / fichiers
        sv = tk.Menu(m, **st)
        sv.add_command(label=T("Dossier de sauvegarde du jeu…"), command=self.pick_saves)
        sv.add_command(label=T("Ouvrir le dossier de mes farms"), command=self.open_data)
        if WIN:
            sv.add_command(label=T("Créer un raccourci sur le Bureau"), command=self.make_shortcut)
        m.add_cascade(label=T("Sauvegarde & fichiers"), menu=sv)
        # --- aide
        hp = tk.Menu(m, **st)
        hp.add_command(label=T("Tutoriel : apprendre l'appli"), command=self.tutorial)
        hp.add_command(label=T("Nouveautés de la version"), command=self.news)
        hp.add_command(label=T("Aide"), command=self.help)
        hp.add_separator()
        hp.add_command(label=T("Discord : mises à jour et aide"), command=lambda: self.open_url(config.DISCORD_URL))
        hp.add_command(label=f"TikTok {config.TIKTOK_NAME}", command=lambda: self.open_url(config.TIKTOK_URL))
        m.add_cascade(label=T("Aide & réseaux"), menu=hp)
        m.add_separator()
        if full_app_dir():
            m.add_command(label=T("⇄ Passer à Kill_Farm (l'appli complète)"), command=self.switch_to_full)
        m.add_command(label=T("Quitter KillFarm"), command=self.quit)
        self._popup(m, widget, event)

    def _theme_menu(self, parent):
        var = tk.StringVar(value=self.cfg.get("theme", "automne"))
        sub = tk.Menu(parent, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG)
        for key, (label, pal) in THEMES.items():
            sub.add_radiobutton(label=T(label), variable=var, value=key, foreground=pal["ACC"],
                                command=lambda k=key: self.set_theme(k))
        return sub

    def _lang_menu(self, parent):
        var = tk.StringVar(value=lang.LANG)
        sub = tk.Menu(parent, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG)
        for key, label in (("en", "English"), ("fr", "Français")):
            sub.add_radiobutton(label=label, variable=var, value=key, command=lambda k=key: self.set_language(k))
        return sub

    def set_language(self, code):
        """Nouvelle langue : on reconstruit la fenêtre et les overlays (comme pour une couleur)."""
        if code == lang.LANG:
            return
        self.cfg["lang"] = code
        lang.set_lang(code)
        if self.suggest:                                     # nom de la bête proposée, dans la nouvelle langue
            sp = gd.species_by_en(self.suggest[0])
            if sp:
                self.suggest = (self.suggest[0], gd.name(sp)) + tuple(self.suggest[2:])
        self.set_theme(self.cfg.get("theme", "automne"))
        self.status = T("Langue : Français")

    def _opacity_menu(self, parent):
        var = tk.DoubleVar(value=self._opacity())
        sub = tk.Menu(parent, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG)
        for v, lab in BAR_OPACITY:
            sub.add_radiobutton(label=T("Couleur de la barre : {x}", x=T(lab)), variable=var, value=v,
                                command=lambda v=v: self.set_opacity(v))
        return sub

    def _opacity(self):
        try:
            return min(1.0, max(0.15, float(self.cfg.get("bar_opacity", 0.6))))
        except (TypeError, ValueError):
            return 0.6

    def _live(self):
        """Barre « live » : UNE fenêtre opaque, sans transparence. TikTok LIVE Studio (et la capture BitBlt d'OBS)
        ne voient pas les fenêtres transparentes (-transparentcolor / -alpha) : elles sortent noires."""
        return bool(self.cfg.get("bar_live", False))

    def toggle_live(self):
        self._set("bar_live", not self._live(), rebuild=True)
        self.status = T("Barre Stream opaque : dans TikTok LIVE Studio, Capture de fenêtre > « KillFarm Lite – Stream »"
                        if self._live() else "Barre Stream transparente")
        self.render()

    # ---------------------------------------------------------------- MINI MENU + LOGO (bord de l'écran)
    # cfg["mini"] : "ouvert" (le mini menu est affiché) | "reduit" (seul le logo dépasse du bord) | "off"
    bub = None                                              # fenêtre du LOGO (onglet au bord)
    mini = None                                             # fenêtre du MINI MENU
    TAB = 58                                                # taille du logo (px)
    MW = 270                                                # largeur du mini menu

    def _bubble_on(self):
        return self.cfg.get("mini", "reduit") != "off"

    def toggle_bubble(self):
        """⚙ : afficher / enlever le mini menu et son logo."""
        self.cfg["mini"] = "off" if self._bubble_on() else "reduit"
        config.save(self.cfg)
        self._mini_close_all()
        self.status = T("Logo au bord de l'écran : clic = mini menu" if self._bubble_on()
                        else "Mini menu enlevé (⚙ pour le remettre)")
        self.render()

    def _mini_close_all(self):
        for w in (self.bub, self.mini):
            if w is not None:
                try:
                    w.destroy()
                except tk.TclError:
                    pass
        self.bub = self.mini = None

    def mini_open(self):
        self.cfg["mini"] = "ouvert"
        config.save(self.cfg)
        self.render()

    def open_main(self):
        """Mini menu > Fenêtre : la grande fenêtre revient, le mini menu se range (logo)."""
        self.cfg["mini"] = "reduit" if self._bubble_on() else "off"
        config.save(self.cfg)
        self.set_mode("fenetre")
        self._bring(self.root)

    def mini_reduce(self):
        self.cfg["mini"] = "reduit"
        config.save(self.cfg)
        self.render()

    def _side(self):
        return "gauche" if self.cfg.get("bubble_side", "droite") == "gauche" else "droite"

    def _scr(self):
        """(x, y, largeur, hauteur) de l'écran choisi (⚙ > Affichage > Écran) ; principal par défaut."""
        mons = monitors()
        try:
            i = int(self.cfg.get("screen", 0))
        except (TypeError, ValueError):
            i = 0
        x, y, w, h = mons[i] if 0 <= i < len(mons) else mons[0]
        if w is None:
            w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        return x, y, w, h

    def set_screen(self, i):
        self.cfg["screen"] = i
        config.save(self.cfg)
        self._destroy_overlays()
        self.set_mode(self.mode, save=False)
        self.status = T("Barre, carte et mini menu sur l'écran {n}", n=i + 1)
        self.render()

    def _screen_menu(self, parent):
        st = dict(tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG, font=(UI, 10))
        sub = tk.Menu(parent, **st)
        var = tk.IntVar(value=int(self.cfg.get("screen", 0) or 0))
        for i, (x, y, w, h) in enumerate(monitors()):
            lab = T("Écran {n}", n=i + 1) + (T(" (principal)") if i == 0 else "") + (f"  ·  {w} x {h}" if w else "")
            sub.add_radiobutton(label=lab, variable=var, value=i, command=lambda i=i: self.set_screen(i))
        return sub

    def _mini_y(self, h):
        _x, Y, _w, H = self._scr()
        try:
            fy = min(0.95, max(0.0, float(self.cfg.get("bubble_y", 0.42))))
        except (TypeError, ValueError):
            fy = 0.42
        return Y + max(0, min(H - h, round(fy * H)))

    def _bubble_update(self, d):
        st = self.cfg.get("mini", "reduit")
        if st == "off":
            return self._mini_close_all()
        if st == "ouvert":
            if self.bub is not None:
                self.bub.withdraw()
            if self.root.state() != "withdrawn":            # mini menu ouvert = la grande fenêtre se ferme
                self.root.withdraw()
            self._mini_render(d)
        else:
            if self.mini is not None:
                self.mini.withdraw()
            self._tab_render()

    # ----- le logo (mini menu réduit)
    def _tab_render(self):
        S = self.TAB
        if self.bub is None or not self.bub.winfo_exists():
            self.bub, self.cv_bub = self._overlay(f"{config.APP_NAME} – Logo")
            self.cv_bub.config(width=S, height=S, cursor="hand2")
            self.cv_bub.unbind("<Button-3>")
            self.cv_bub.bind("<ButtonPress-1>", self._bub_press)
            self.cv_bub.bind("<B1-Motion>", self._bub_move)
            self.cv_bub.bind("<ButtonRelease-1>", self._bub_release)
            self.cv_bub.bind("<Button-3>", lambda e: self.quick_menu())
            self.root.after(120, self._keep_on_top)
        self._tab_place()
        self.bub.deiconify()
        cv = self.cv_bub
        cv.delete("all")
        p = config.IMG_DIR / "logo_tab.png"
        img = self.pics.get(p, S, hard=True) if p.exists() else None
        if img:
            cv.create_image(S / 2, S / 2, image=img)
        else:
            rounded(cv, 1, 1, S - 1, S - 1, 14, fill=ACC, outline=BG, width=2)
            cv.create_text(S / 2, S / 2, text="KF", fill=BG, font=(NUM, 16, "bold"))

    def _tab_place(self):
        S = self.TAB
        X, _y, W, _h = self._scr()
        x = X if self._side() == "gauche" else X + W - S
        self.bub.geometry(f"{S}x{S}+{x}+{self._mini_y(S)}")

    def _bub_press(self, e):
        self._bub_drag = (e.x_root, e.y_root, e.x_root - self.bub.winfo_x(), e.y_root - self.bub.winfo_y(), False)

    def _bub_move(self, e):
        x0, y0, dx, dy, moved = self._bub_drag
        if not moved and abs(e.x_root - x0) + abs(e.y_root - y0) < 6:
            return
        self._bub_drag = (x0, y0, dx, dy, True)
        self.bub.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def _bub_release(self, e):
        moved = getattr(self, "_bub_drag", (0, 0, 0, 0, False))[4]
        if not moved:                                       # simple clic : le mini menu sort
            return self.mini_open()
        self.bub.update_idletasks()
        self._snap(self.bub.winfo_x() + self.TAB / 2, self.bub.winfo_y())
        self._tab_place()

    def _snap(self, cx, y):
        mons = monitors()                                   # glissé sur un autre écran : il y reste
        for i, (mx, my, mw, mh) in enumerate(mons):
            if mw and mx <= cx < mx + mw:
                self.cfg["screen"] = i
                break
        X, Y, W, H = self._scr()
        self.cfg["bubble_side"] = "gauche" if cx < X + W / 2 else "droite"      # collé au bord le plus proche
        self.cfg["bubble_y"] = round(max(0, y - Y) / H, 4)
        config.save(self.cfg)

    # ----- le mini menu
    def _mini_build(self):
        w = tk.Toplevel(self.root)
        w.title(f"{config.APP_NAME} – Mini menu")
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=ACC)                                 # liseré de couleur (2 px)
        box = tk.Frame(w, bg=PANEL)
        box.pack(fill="both", expand=True, padx=2, pady=2)
        # en-tête (on le prend pour déplacer le menu)
        top = tk.Frame(box, bg=BG)
        top.pack(fill="x")
        p = config.IMG_DIR / "logo_tab.png"
        self._mini_logo = self.pics.get(p, 22, back=BG) if p.exists() else None
        lg = tk.Label(top, image=self._mini_logo, bg=BG) if self._mini_logo else tk.Label(top, text="KF", bg=BG, fg=ACC)
        lg.pack(side="left", padx=(12, 6), pady=8)
        tl = tk.Label(top, text="KILLFARM", bg=BG, fg=FG, font=(UI, 10, "bold"))
        tl.pack(side="left")
        red = tk.Label(top, text=" › " if self._side() == "droite" else " ‹ ", bg=BG, fg=FG, font=(UI, 14, "bold"),
                       cursor="hand2")
        red.pack(side="right", padx=(0, 10))
        red.bind("<Button-1>", lambda e: self.mini_reduce())
        gear = tk.Label(top, text="⚙", bg=BG, fg=DIM, font=(UI, 12), cursor="hand2")
        gear.pack(side="right", padx=4)
        gear.bind("<Button-1>", lambda e: self.settings_menu(gear, e))
        for h in (top, tl, lg):
            h.bind("<ButtonPress-1>", self._mini_press)
            h.bind("<B1-Motion>", self._mini_move)
            h.bind("<ButtonRelease-1>", self._mini_release)
        tk.Frame(box, bg=ACC, height=2).pack(fill="x")
        # fiche du farm actif
        self.cv_mini = tk.Canvas(box, width=self.MW - 4, height=176, bg=PANEL, highlightthickness=0)
        self.cv_mini.pack()
        self.cv_mini.bind("<Button-3>", lambda e: self.quick_menu())
        self.cv_mini.bind("<Button-1>", lambda e: self._mini_popup(self._farms_menu(), self.cv_mini, e))

        def flat(parent, text, cmd, primary=False, big=False):
            return RButton(parent, text=text, command=cmd, bg=ACC if primary else BTN,
                           fg="#ffffff" if primary else FG, font=(UI, 13 if big else 9, "bold"),
                           pady=9 if big else 6, radius=12 if big else 9)
        pad = dict(padx=8)
        flat(box, T("+1  KILL"), self.plus, primary=True, big=True).pack(fill="x", pady=(2, 6), **pad)
        r1 = tk.Frame(box, bg=PANEL)
        r1.pack(fill="x", **pad)
        flat(r1, T("Annuler"), self.undo).pack(side="left", fill="x", expand=True, padx=(0, 3))
        flat(r1, "Great One", self.mark_go).pack(side="left", fill="x", expand=True, padx=(3, 0))
        r2 = tk.Frame(box, bg=PANEL)
        r2.pack(fill="x", pady=6, **pad)
        self._mini_farm_btn = flat(r2, T("Changer de farm ▾"), lambda: self._mini_popup(self._farms_menu(),
                                                                                       self._mini_farm_btn))
        self._mini_farm_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        flat(r2, T("Nouveau farm"), self.new_farm).pack(side="left", fill="x", expand=True, padx=(3, 0))
        # pied : liens discrets
        foot = tk.Frame(box, bg=BG)
        foot.pack(fill="x")

        def link(text, cmd):
            l = tk.Label(foot, text=text, bg=BG, fg=DIM, font=(UI, 9), cursor="hand2", pady=6)
            l.pack(side="left", expand=True)
            l.bind("<Button-1>", lambda e: cmd())
            l.bind("<Enter>", lambda e: l.config(fg=ACC))
            l.bind("<Leave>", lambda e: l.config(fg=DIM))
            return l
        self._mini_aff_lnk = link(T("Affichage ▾"), lambda: self._mini_popup(self._modes_menu(), self._mini_aff_lnk))
        link(T("Lien du live"), self.web_link)
        link(T("Grande fenêtre"), self.open_main)
        self.mini = w
        self.root.after(120, self._keep_on_top)

    def _mini_popup(self, menu, widget, e=None):
        try:
            if e is not None:
                menu.tk_popup(e.x_root, e.y_root)
            else:
                menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())
        finally:
            menu.grab_release()

    def _farms_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG, font=(UI, 10))
        for k in self.farms.order[:25]:
            f = self.farms.farms[k]
            m.add_command(label=("● " if k == self.farms.active else "   ") + f"{fname(f)} · {fres(f)}",
                          command=lambda k=k: (self.farms.set_active(k), self.render()))
        if not self.farms.order:
            m.add_command(label=T("Aucun farm lancé"), state="disabled")
        m.add_separator()
        m.add_command(label=T("▶ Lancer un nouveau farm…"), command=lambda: (self._bring(self.root), self.new_farm()))
        return m

    def _modes_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground=BG, font=(UI, 10))
        for md in ("tiktok", "stream"):                     # « Fenêtre » : c'est la grande fenêtre (lien en bas)
            m.add_command(label=("●  " if md == self.mode else "    ") + T(MODE_NAMES[md]),
                          command=lambda md=md: self.set_mode(md))
        if self.mode in ("tiktok", "stream"):
            m.add_separator()
            m.add_command(label=T("Cacher / montrer (F8)"), command=self.toggle_hidden)
        return m

    def _mini_render(self, d):
        if self.mini is None or not self.mini.winfo_exists():
            self._mini_build()
        self.mini.update_idletasks()
        h = self.mini.winfo_reqheight()
        X, _y, W, _h = self._scr()
        x = X if self._side() == "gauche" else X + W - self.MW
        if not getattr(self, "_mini_dragging", False):
            self.mini.geometry(f"{self.MW}x{h}+{x}+{self._mini_y(h)}")
        self.mini.deiconify()
        win_round(self.mini, 22)
        cv, Wc = self.cv_mini, self.MW - 4
        cv.delete("all")
        if not d:
            cv.create_text(Wc / 2, 74, text=T("Aucun farm lancé"), fill=FG, font=(UI, 12, "bold"))
            cv.create_text(Wc / 2, 98, text=T("« Nouveau farm » pour commencer"), fill=DIM, font=(UI, 9))
            return
        # bête + nom (clic = changer de farm)
        pic = self.pics.get(d["img"], 52, circle=True, ring=ACC, back=PANEL)
        if pic:
            cv.create_image(36, 38, image=pic)
        fn, fr = tkfont.Font(family=UI, size=11, weight="bold"), tkfont.Font(family=UI, size=9)
        cv.create_text(70, 28, text=fit(d["name"], fn, Wc - 92), anchor="w", fill=FG, font=fn)
        cv.create_text(70, 48, text=fit(d["reserve"], fr, Wc - 92), anchor="w", fill=DIM, font=fr)
        cv.create_text(Wc - 12, 28, text="▾", anchor="e", fill=DIM, font=(UI, 10))
        # 3 chiffres
        y0, y1 = 70, 118
        cols = ((T("FARM"), fmt(d["since"]), ACC, 20), (T("DERNIER GO"), fmt(d["last_go"]) if d["last_go"] else "—", GOLD, 14),
                (T("TOTAL"), fmt(d["count"]), FG, 14))
        cw = (Wc - 24) / 3
        for i, (lab, val, col, fs) in enumerate(cols):
            x1 = 8 + i * (cw + 4)
            rounded(cv, x1, y0, x1 + cw, y1, 7, fill=BG, outline=ACC if i == 0 else EDGE, width=1)
            cv.create_text(x1 + cw / 2, y0 + 11, text=lab, fill=DIM, font=(UI, 7, "bold"))
            fv = tkfont.Font(family=NUM, size=fs, weight="bold")
            cv.create_text(x1 + cw / 2, y0 + 31, text=fit(val, fv, cw - 6), fill=col, font=fv)
        self._plus_anim(cv, 8 + cw - 18, y0 + 14, 11)
        # grades : badge au-dessus, nombre dessous
        step = (Wc - 16) / 6
        fg_ = tkfont.Font(family=NUM, size=10, weight="bold")
        for g in range(6):
            cx = 8 + step * g + step / 2
            im = self.pics.get(gd.badge(g), 24, back=PANEL)
            if im:
                cv.create_image(cx, 140, image=im)
            cv.create_text(cx, 163, text=short_num(d["grades"][g]), fill=GRADE_COL[g], font=fg_)
        self._go_flash(cv, Wc / 2, 94, 15)

    def _mini_press(self, e):
        self._mini_drag = (e.x_root - self.mini.winfo_x(), e.y_root - self.mini.winfo_y())
        self._mini_dragging = True

    def _mini_move(self, e):
        dx, dy = self._mini_drag
        self.mini.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def _mini_release(self, e):
        self._mini_dragging = False
        self.mini.update_idletasks()
        self._snap(self.mini.winfo_x() + self.MW / 2, self.mini.winfo_y())
        self._mini_build_again()

    def _mini_build_again(self):
        """Côté changé : on reconstruit (la flèche « réduire » change de sens)."""
        if self.mini is not None:
            self.mini.destroy()
            self.mini = None
        self.render()

    def quick_menu(self, x=None, y=None):
        """Menu rapide RANGÉ (clic droit sur le logo, le mini menu, la carte ou la barre)."""
        st = dict(tearoff=0, bg=PANEL, fg=FG, activebackground=ACC, activeforeground="#ffffff", font=(UI, 10))
        m = tk.Menu(self.root, **st)
        d = self.data()
        if d:
            m.add_command(label=f"  {d['name']}  ·  {d['reserve']}", state="disabled")
            m.add_command(label=T("  {a} depuis le dernier GO  ·  total {b}", a=kills(d["since"]), b=fmt(d["count"])),
                          state="disabled")
            m.add_separator()
            m.add_command(label=T("+1 kill"), command=self.plus)
            m.add_command(label=T("Annuler le dernier kill"), command=self.undo)
            m.add_command(label=T("Mon dernier kill était un Great One"), command=self.mark_go)
            m.add_separator()
        m.add_cascade(label=T("Changer de farm"), menu=self._farms_menu())
        m.add_cascade(label=T("Affichage"), menu=self._modes_menu())
        bar = tk.Menu(m, **st)                              # tout ce qui concerne la barre et le live
        side = tk.StringVar(value=self.cfg["bar_side"])
        for s_, lab in BAR_SIDES:
            bar.add_radiobutton(label=T(lab), variable=side, value=s_, command=lambda s_=s_: self._set("bar_side", s_, True))
        bar.add_separator()
        bar.add_cascade(label=T("Transparence de la barre"), menu=self._opacity_menu(bar))
        if self.mode == "stream":
            bar.add_command(label=T("Bloquer / débloquer la barre (²)"), command=self.toggle_lock)
        bar.add_separator()
        bar.add_command(label=T("Lien de la barre pour le live…"), command=self.web_link)
        m.add_cascade(label=T("Barre Stream & live"), menu=bar)
        m.add_cascade(label=T("Écran"), menu=self._screen_menu(m))
        m.add_cascade(label=T("Couleur"), menu=self._theme_menu(m))
        m.add_separator()
        if self.cfg.get("mini", "reduit") == "ouvert":
            m.add_command(label=T("Réduire le mini menu"), command=self.mini_reduce)
        else:
            m.add_command(label=T("Ouvrir le mini menu"), command=self.mini_open)
        m.add_command(label=T("Grande fenêtre"), command=self.open_main)
        if self.mode in ("tiktok", "stream"):
            m.add_command(label=T("Cacher (F8)"), command=self.toggle_hidden)
        m.add_separator()
        m.add_command(label=T("Quitter KillFarm"), command=self.quit)
        if x is None:
            x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    # ---------------------------------------------------------------- barre WEB (source « Lien » / « Navigateur »)
    def _web_payload(self, d):
        cols = dict(card=CARD, acc=ACC, gold=GOLD, leaf=LEAF, fg=FG, dim=DIM, edge=EDGE, bg=BG)
        out = {"theme": cols, "opacity": self._opacity(), "lang": lang.LANG,
               "labels": {"since": T("KILLS DU FARM"), "last_go": T("DERNIER GO"),
                          "count": T("TOTAL DU FARM"), "tab": T("KILLFARM · FARM EN COURS")},
               "grade_cols": [GRADE_COL[g] for g in range(6)],
               "badges": [webbar.img_url(gd.badge(g)) for g in range(6)],
               "sig": f"{config.SIGNATURE} · {config.TIKTOK_NAME}",
               "none": config.APP_NAME + T(" · aucun farm lancé"), "farm": None}
        if d:
            out["farm"] = {"key": self.farms.active, "name": d["name"], "reserve": d["reserve"],
                           "since": d["since"], "last_go": d["last_go"], "count": d["count"], "go": d["go"],
                           "grades": list(d["grades"]), "img": webbar.img_url(d["img"]),
                           "go_label": T("{n} Great One" if d["go"] <= 1 else "{n} Great Ones", n=fmt(d["go"]))}
        return out

    def web_link(self):
        """Lien de la barre pour le live : une vraie boîte de l'appli (pas la boîte Windows)."""
        u0 = webbar.start()
        # TikTok LIVE Studio refuse « 127.0.0.1 » et « localhost » : nip.io renvoie au même endroit (ton PC)
        u = u0.replace("127.0.0.1", "127.0.0.1.nip.io") if u0 else None
        old = getattr(self, "_linkwin", None)
        if old is not None and old.winfo_exists():
            old.destroy()
        w = self._linkwin = tk.Toplevel(self.root)
        w.title(T("Barre pour ton live"))
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=ACC)
        box = tk.Frame(w, bg=PANEL)
        box.pack(fill="both", expand=True, padx=2, pady=2)
        head = tk.Frame(box, bg=BG)
        head.pack(fill="x")
        p = config.IMG_DIR / "logo_tab.png"
        w._logo = self.pics.get(p, 26, back=BG) if p.exists() else None
        if w._logo:
            tk.Label(head, image=w._logo, bg=BG).pack(side="left", padx=(14, 8), pady=10)
        tk.Label(head, text=T("BARRE POUR TON LIVE"), bg=BG, fg=FG, font=(UI, 12, "bold")).pack(side="left")
        x = tk.Label(head, text="✕", bg=BG, fg=DIM, font=(UI, 12, "bold"), cursor="hand2")
        x.pack(side="right", padx=14)
        x.bind("<Button-1>", lambda e: w.destroy())
        tk.Frame(box, bg=ACC, height=2).pack(fill="x")
        body = tk.Frame(box, bg=PANEL, padx=18, pady=14)
        body.pack(fill="both")
        if not u:
            tk.Label(body, text=T("Impossible de lancer la barre web (ports 8777 à 8797 déjà pris)."), bg=PANEL, fg=FG,
                     font=(UI, 10)).pack(anchor="w")
        else:
            tk.Label(body, text=T("Ton adresse (elle ne marche que sur ce PC) :"), bg=PANEL, fg=DIM,
                     font=(UI, 9)).pack(anchor="w")
            row = tk.Frame(body, bg=PANEL)
            row.pack(fill="x", pady=(6, 12))
            cv = tk.Canvas(row, width=320, height=40, bg=PANEL, highlightthickness=0)
            cv.pack(side="left")
            rounded(cv, 1, 1, 319, 39, 10, fill=BG, outline=EDGE)
            cv.create_text(14, 20, text=u, anchor="w", fill=GOLD, font=("Consolas", 11, "bold"))
            msg = tk.Label(body, text="", bg=PANEL, fg=LEAF, font=(UI, 9, "bold"))

            def copy(text, what):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                except tk.TclError:
                    pass
                msg.config(text=T("✓ {x} copiée", x=what))
            RButton(row, text=T("Copier"), command=lambda: copy(u, T("Adresse")), bg=ACC, fg="#ffffff",
                    font=(UI, 10, "bold"), pady=9).pack(side="left", padx=(10, 0))
            steps = ((T("TikTok LIVE Studio"), T("Ajouter une source  ›  Lien  ›  colle l'adresse  ›  1120 x 124")),
                     ("OBS", T("Sources  ›  +  ›  Navigateur  ›  colle l'adresse  ›  1120 x 124")))
            for title, text in steps:
                card = tk.Canvas(body, width=420, height=52, bg=PANEL, highlightthickness=0)
                card.pack(pady=3)
                rounded(card, 1, 1, 419, 51, 12, fill=CARD, outline=EDGE)
                card.create_rectangle(12, 14, 15, 38, fill=ACC, outline="")
                card.create_text(26, 17, text=title, anchor="w", fill=FG, font=(UI, 10, "bold"))
                card.create_text(26, 36, text=text, anchor="w", fill=DIM, font=(UI, 9))
            tr = tk.Frame(body, bg=PANEL)
            tr.pack(fill="x", pady=(10, 0))
            tk.Label(tr, text=T("Fond transparent :"), bg=PANEL, fg=DIM, font=(UI, 9)).pack(side="left")
            RButton(tr, text=T("Copier l'adresse sans fond"), command=lambda: copy(u + "?fond=0", T("Adresse sans fond")),
                    bg=BTN, fg=FG, font=(UI, 9, "bold")).pack(side="left", padx=8)
            msg.pack(anchor="w", pady=(8, 0))
            foot = tk.Frame(body, bg=PANEL)
            foot.pack(fill="x", pady=(10, 0))
            RButton(foot, text=T("Voir l'aperçu"), command=lambda: self.open_url(u0), bg=BTN, fg=FG,
                    font=(UI, 9, "bold")).pack(side="left")
            RButton(foot, text="OK", command=w.destroy, bg=ACC, fg="#ffffff", font=(UI, 10, "bold"), padx=22).pack(side="right")
            tk.Label(body, text=T("Garde KillFarm ouvert pendant le live."), bg=PANEL, fg=EDGE,
                     font=(UI, 8)).pack(anchor="w", pady=(10, 0))
            copy(u, T("Adresse"))
        # déplacer en tenant l'en-tête
        def press(e):
            w._d = (e.x_root - w.winfo_x(), e.y_root - w.winfo_y())

        def move(e):
            w.geometry(f"+{e.x_root - w._d[0]}+{e.y_root - w._d[1]}")
        head.bind("<ButtonPress-1>", press)
        head.bind("<B1-Motion>", move)
        w.bind("<Escape>", lambda e: w.destroy())
        w.update_idletasks()
        ww, hh = w.winfo_reqwidth(), w.winfo_reqheight()
        w.geometry(f"+{(w.winfo_screenwidth() - ww) // 2}+{(w.winfo_screenheight() - hh) // 2}")
        w.after(30, lambda: win_round(w, 24))
        w.focus_force()

    # ---------------------------------------------------------------- fenêtre « Live » (pour TikTok LIVE Studio)
    live_win = None
    cv_live = None

    def toggle_live_window(self):
        """Ouvre / ferme la fenêtre « KillFarm Lite – Live » : une VRAIE fenêtre Windows (barre de titre, opaque), que
        TikTok LIVE Studio sait capturer (Capture de fenêtre). Elle montre la même barre que l'affichage Stream."""
        on = not self.cfg.get("live_window", False)
        self.cfg["live_window"] = on
        config.save(self.cfg)
        if not on:
            self._close_live_win()
        self.status = T("Fenêtre Live ouverte : dans TikTok LIVE Studio, Capture de fenêtre > « KillFarm Lite – Live »"
                        if on else "Fenêtre Live fermée")
        self.render()

    def _close_live_win(self):
        w, self.live_win, self.cv_live = self.live_win, None, None
        if w is not None:
            try:
                self.cfg["live_geo"] = w.geometry()
                config.save(self.cfg)
                w.destroy()
            except tk.TclError:
                pass

    def _ensure_live_win(self):
        if self.live_win is not None and self.live_win.winfo_exists():
            return
        w = tk.Toplevel(self.root)
        w.title(f"{config.APP_NAME} – Live")
        w.configure(bg=CARD)
        cv = tk.Canvas(w, bg=BG, highlightthickness=0, bd=0, width=1120, height=118)
        cv.pack(fill="both", expand=True)
        cv.bind("<Button-3>", lambda e: self.overlay_menu(e))
        w.minsize(700, 70)
        geo = self.cfg.get("live_geo")
        try:
            w.geometry(geo if geo else "1120x118+100+200")
        except tk.TclError:
            w.geometry("1120x118+100+200")

        def resized(e, cv=cv):
            if e.widget is cv and (int(cv.cget("width")) != e.width or int(cv.cget("height")) != e.height):
                cv.config(width=e.width, height=e.height)
                self.root.after_idle(self.render)
        cv.bind("<Configure>", resized)

        def closed():                                       # croix de la fenêtre = option désactivée
            self.cfg["live_window"] = False
            config.save(self.cfg)
            self._close_live_win()
        w.protocol("WM_DELETE_WINDOW", closed)
        self.live_win, self.cv_live = w, cv

    def set_opacity(self, v):
        """Le fond coloré de la barre devient transparent (on voit le jeu à travers) ; textes et images restent nets."""
        was_full = self._opacity() >= 0.99
        self.cfg["bar_opacity"] = v
        config.save(self.cfg)
        if was_full != (self._opacity() >= 0.99):           # 1 fenêtre <-> 2 fenêtres : on reconstruit la barre
            self._destroy_overlays()
            self.set_mode(self.mode, save=False)
        if self.stream_bg is not None:
            try:
                self.stream_bg.attributes("-alpha", self._opacity())
            except tk.TclError:
                pass
        self.status = T("Barre Stream : couleur {x} %", x=round(self._opacity() * 100))
        self.render()

    def set_theme(self, name):
        """Nouvelle couleur : on reconstruit la fenêtre et les overlays avec la nouvelle palette."""
        self.cfg["theme"] = apply_theme(name)
        config.save(self.cfg)
        for c in self.root.winfo_children():
            if not isinstance(c, tk.Toplevel):
                c.destroy()
        self._destroy_overlays()
        self.root.configure(bg=BG)
        self._style()
        self._build_window()
        self.set_mode(self.mode, save=False)
        self.status = T("Couleur : {x}", x=T(THEMES[self.cfg['theme']][0]))
        self.render()

    def tutorial(self):
        Tutorial(self)

    NEWS = (("🎨", "Nouvelles couleurs", "TikTok (rose et cyan), Twitch (violet), YouTube (rouge) : ⚙ > Affichage > Couleur. "
                                        "Boutons arrondis en relief, barre de titre sombre."),
            ("📌", "Mini menu", "Ton logo est collé au bord de l'écran : clic dessus = le mini menu sort (+1, annuler, "
                               "Great One, changer de farm…). Quand il est ouvert, la grande fenêtre se range."),
            ("🏁", "Nouvelle barre Stream", "Un tableau en bas au centre de l'écran : kills du farm, dernier GO, total et "
                                           "tes 6 grades. Position : ⚙ > Barre Stream & live."),
            ("🔴", "Barre pour ton live", "⚙ > Barre Stream & live > Lien de la barre : à coller dans TikTok LIVE Studio "
                                         "(source Lien) ou OBS (source Navigateur). Fond transparent, rien en blanc."),
            ("🦌", "Photos des bêtes", "Les bêtes ne touchent plus le rond de couleur."),
            ("⚙", "Réglages rangés", "Le menu ⚙ est rangé en 4 parties : Affichage, Barre Stream & live, Sauvegarde, Aide."))

    def news(self):
        """Affiche de la mise à jour (une fois après l'installation ; ensuite ⚙ > Nouveautés)."""
        w = tk.Toplevel(self.root)
        w.title(T("{app} · Mise à jour {v}", app=config.APP_NAME, v=config.VERSION))
        w.configure(bg=ACC)
        w.resizable(False, False)
        box = tk.Frame(w, bg=BG, padx=24, pady=18)
        box.pack(padx=3, pady=3)
        head = tk.Frame(box, bg=BG)
        head.pack(fill="x")
        w._logo = self.pics.get(config.LOGO_PNG, 60, back=BG) if config.LOGO_PNG.exists() else None
        if w._logo:
            tk.Label(head, image=w._logo, bg=BG).pack(side="left", padx=(0, 12))
        t = tk.Frame(head, bg=BG)
        t.pack(side="left")
        tk.Label(t, text=T("MISE À JOUR"), fg=DIM, bg=BG, font=(UI, 9, "bold")).pack(anchor="w")
        tk.Label(t, text=f"{config.APP_NAME} {config.VERSION}", fg=ACC, bg=BG, font=(UI, 19, "bold")).pack(anchor="w")
        tk.Label(t, text=config.SIGNATURE, fg=GOLD, bg=BG, font=(UI, 9, "italic")).pack(anchor="w")
        tk.Frame(box, bg=EDGE, height=2).pack(fill="x", pady=(12, 8))
        for icon, title, text in self.NEWS:
            row = tk.Frame(box, bg=BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=icon, fg=ACC, bg=BG, font=("Segoe UI Emoji", 14), width=2).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=BG)
            col.pack(side="left", padx=(8, 0))
            tk.Label(col, text=T(title), fg=FG, bg=BG, font=(UI, 10, "bold")).pack(anchor="w")
            tk.Label(col, text=T(text), fg=DIM, bg=BG, font=(UI, 9), wraplength=430, justify="left").pack(anchor="w")
        tk.Label(box, text=T("Tes réglages sont gardés : affichage au démarrage, couleur, position de la barre, raccourcis, "
                           "farms et chiffres."), fg=LEAF, bg=BG, font=(UI, 8), wraplength=470, justify="left").pack(
            anchor="w", pady=(10, 0))

        def ok():
            self.cfg["nouveautes_vues"] = config.VERSION
            config.save(self.cfg)
            w.destroy()

        self._btn(box, T("C'est parti !"), ok, primary=True).pack(pady=(14, 0))
        w.protocol("WM_DELETE_WINDOW", ok)
        w.update_idletasks()
        w.geometry(f"+{(w.winfo_screenwidth() - w.winfo_reqwidth()) // 2}+{max(0, (w.winfo_screenheight() - w.winfo_reqheight()) // 3)}")
        self._bring(w)
        return w

    def _popup(self, m, widget, event):
        if event is not None:
            m.tk_popup(event.x_root, event.y_root)
        elif widget is not None:
            m.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())

    def _set(self, k, v, rebuild=False):
        self.cfg[k] = v
        config.save(self.cfg)
        if rebuild:
            self._destroy_overlays()
            self.set_mode(self.mode, save=False)
        self.render()

    @staticmethod
    def open_url(url):
        import webbrowser
        webbrowser.open(url)

    def open_data(self):
        config.USER_DIR.mkdir(parents=True, exist_ok=True)
        if WIN:
            os.startfile(str(config.USER_DIR))
        else:
            messagebox.showinfo(config.APP_NAME, str(config.USER_DIR), parent=self.root)

    def help(self):
        lien = T("Farms {x} : mêmes farms, mêmes chiffres dans les 2 applis.\n\n", x=self.farms.lien.label()) if self.farms.lien else ""
        messagebox.showinfo(
            f"{config.APP_NAME} {config.VERSION}",
            T("LANCER UN FARM\n"
            "« ▶ Lancer un farm » : choisis la réserve et l'animal (ou « Farmer celle-là » pour ta dernière bête).\n"
            "Joue : chaque bête RAMASSÉE de ton farm est comptée toute seule, avec son grade. "
            "L'appli lit la sauvegarde du jeu, elle ne la modifie jamais.\n\n"
            "AFFICHAGES  (F7 = changer, F8 = cacher / montrer)\n"
            "• Fenêtre : le compteur complet.\n"
            "• TikTok : une carte à glisser où tu veux à la souris ; clic droit = menu.\n"
            "• Stream : une barre en bas ou en haut de l'écran, on voit le jeu à travers. La souris passe à travers : "
            "touche ² (sous Échap) pour la débloquer, puis clic droit = menu.\n\n"
            "CORRIGER\n"
            "• −1 / +1, « Annuler le dernier kill ».\n"
            "• Clic droit sur un badge de grade : +1 / −1.\n"
            "• Great One pas reconnu : ☰ Mes farms > « Mon dernier kill était un Great One ».\n"
            "• Bête pas reconnue : l'appli te demande laquelle c'était et s'en souvient.\n\n"
            "IMPORTANT\n"
            "Mets le jeu en « Fenêtré sans bordure » (Options > Affichage) : en « Plein écran », la carte et la barre "
            "sont cachées.\n\n")
            + lien
            + T("Tes farms : {x}\n", x=config.USER_DIR)
            + T("Mises à jour et aide : Discord {x}\n", x=config.DISCORD_URL.replace('https://', ''))
            + f"{config.APP_NAME} {config.VERSION} · {config.SIGNATURE} · TikTok {config.TIKTOK_NAME}",
            parent=self.root)

    def delete_farm(self):
        f = self.farms.get()
        both = T("\n\n(Il sera aussi supprimé dans Kill_Farm : les 2 applis ont les mêmes farms.)") if self.farms.lien else ""
        if f and messagebox.askyesno(config.APP_NAME, T("Supprimer le farm « {name} · {res} » et ses {k} ?",
                                     name=fname(f), res=fres(f), k=kills(f['count'])) + both, parent=self.root):
            self.farms.delete(self.farms.active)
            self.render()

    def new_farm(self, preset=None):
        """Une seule fenêtre « Lancer un farm » à la fois : si elle est déjà ouverte, on la ramène devant."""
        nf = getattr(self, "_nf", None)
        if nf is not None and nf.win.winfo_exists():
            self._bring(nf.win)
            if preset:
                nf.use(preset)
            return nf
        self._nf = NewFarm(self, preset)
        self.root.after(30, lambda: self._bring(self._nf.win))
        return self._nf

    def edit_numbers(self):
        en = EditNumbers(self)
        self.root.after(30, lambda: getattr(en, "win", None) is not None and self._bring(en.win))

    def _bring(self, win):
        """Ouvre une fenêtre de l'appli DEVANT la barre / la carte (et devant le jeu), avec le focus."""
        try:
            if not win.winfo_exists():
                return
            win.deiconify()
            win.lift()
            win.focus_force()
        except tk.TclError:
            return
        self._keep_on_top(True)

    # ================================================================ modes
    def cycle_mode(self):
        self.set_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)] if self.mode in MODES else "fenetre")

    def set_mode(self, mode, save=True):
        mode = mode if mode in MODES else "fenetre"
        self.mode = mode
        self.hidden = False
        if save:
            self.cfg["mode"] = mode
            config.save(self.cfg)
        if mode == "tiktok":
            self._show_tiktok()
            self._hide(self.stream)
            self._hide(self.stream_bg)
        elif mode == "stream":
            self._show_stream()
            self._hide(self.tiktok)
        else:
            self._hide(self.tiktok)
            self._hide(self.stream)
            self._hide(self.stream_bg)
            self.root.deiconify()
            self.root.lift()
        self.render()

    @staticmethod
    def _hide(win):
        if win is not None:
            win.withdraw()

    def _destroy_overlays(self):
        for w in (self.tiktok, self.stream, self.stream_bg):
            if w is not None:
                w.destroy()
        self.tiktok = self.stream = self.stream_bg = None
        self._mini_close_all()
        if self.live_win is not None:
            self._close_live_win()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        win = self.tiktok if self.mode == "tiktok" else self.stream if self.mode == "stream" else self.root
        if win is None:
            self.hidden = False
            return
        if self.hidden:
            if win is self.root:
                win.iconify()                               # reste dans la barre des tâches : on la retrouve toujours
            else:
                win.withdraw()
                if win is self.stream:
                    self._hide(self.stream_bg)
        else:
            if win is self.stream and self.stream_bg is not None:
                self.stream_bg.deiconify()
            win.deiconify()
            self._keep_on_top()

    def toggle_lock(self):
        """Touche ² : la souris passe à travers la carte / la barre (bloqué) ou peut cliquer dessus (débloqué)."""
        self.cfg["click_through"] = not self.cfg.get("click_through", True)
        config.save(self.cfg)
        self._apply_lock()
        on = self.cfg["click_through"]
        self.status = T("Barre Stream BLOQUÉE : la souris passe à travers (² pour débloquer)" if on else
                        "Barre Stream DÉBLOQUÉE : clic droit = menu (² pour bloquer)")
        self.flash_lock = (time.time(), on)
        self.render()
        self.root.after(1600, self.render)

    def _apply_lock(self):
        on = bool(self.cfg.get("click_through", True))
        for w in (self.tiktok, self.stream, self.stream_bg):
            if w is None or not WIN:
                continue
            if w is self.stream and self._live():
                continue                                    # barre opaque : jamais LAYERED (sinon invisible pour TikTok Studio)
            w_on = on and w is not self.tiktok             # la carte TikTok se déplace TOUJOURS ; seule la barre se bloque
            try:
                import ctypes
                u32 = ctypes.windll.user32
                hwnd = int(w.wm_frame(), 16)
                ex = u32.GetWindowLongW(hwnd, -20)                          # GWL_EXSTYLE
                flags = 0x00080000 | 0x00000020 | 0x08000000                # LAYERED | TRANSPARENT | NOACTIVATE
                u32.SetWindowLongW(hwnd, -20, (ex | flags) if w_on else (ex & ~(0x00000020 | 0x08000000)))
            except Exception:
                pass

    def _lock_note(self, cv, x, y, anchor="center"):
        """Petit message 1,5 s après ² (bloqué / débloqué)."""
        fl = getattr(self, "flash_lock", None)
        if not fl or time.time() - fl[0] > 1.5:
            return
        txt = T("BLOQUÉ · la souris passe à travers" if fl[1] else "DÉBLOQUÉ · clic droit = menu")
        f = tkfont.Font(family=UI, size=10, weight="bold")
        w = f.measure(txt) / 2 + 12
        rounded(cv, x - w, y - 14, x + w, y + 14, 10, fill=CARD, outline=GOLD, width=2)
        cv.create_text(x, y, text=txt, fill=GOLD, font=f)

    def _overlay(self, title, alpha=None, opaque=False):
        w = tk.Toplevel(self.root)
        w.title(title)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        if opaque:                                          # barre « live » : rien de transparent, capturable partout
            w.configure(bg=CARD)
            cv = tk.Canvas(w, bg=CARD, highlightthickness=0, bd=0)
            cv.pack()
            cv.bind("<Button-3>", lambda e: self.overlay_menu(e))
            return w, cv
        w.configure(bg=KEY)
        if WIN:
            try:
                w.wm_attributes("-transparentcolor", KEY)
            except tk.TclError:
                pass
        if alpha is not None:                               # fond de la barre : couleur transparente (le jeu se voit)
            try:
                w.attributes("-alpha", alpha)
            except tk.TclError:
                pass
        cv = tk.Canvas(w, bg=KEY, highlightthickness=0, bd=0)
        cv.pack()
        cv.bind("<Button-3>", lambda e: self.overlay_menu(e))
        return w, cv

    def overlay_menu(self, e):
        """Clic droit sur la carte / la barre : le même menu rangé que le logo."""
        self.quick_menu(e.x_root, e.y_root)

    def _show_tiktok(self):
        if self.tiktok is None:
            self.tiktok, self.cv_t = self._overlay(f"{config.APP_NAME} – TikTok")
            self.cv_t.bind("<ButtonPress-1>", self._drag_start)
            self.cv_t.bind("<B1-Motion>", self._drag_move)
            self.cv_t.bind("<ButtonRelease-1>", self._drag_end)
            s = {"S": 0.8, "M": 1.0, "L": 1.3}.get(self.cfg["tiktok_size"], 1.0)
            self.t_scale = s
            W, H = round(300 * s), round(470 * s)
            self.cv_t.config(width=W, height=H)
            pos = self.cfg.get("tiktok_pos") or [self.root.winfo_screenwidth() - W - 40, 120]
            x = min(max(0, int(pos[0])), self.root.winfo_screenwidth() - 60)
            y = min(max(0, int(pos[1])), self.root.winfo_screenheight() - 60)
            self.tiktok.geometry(f"{W}x{H}+{x}+{y}")
        self.tiktok.deiconify()
        self.root.after(80, self._apply_lock)

    def _drag_start(self, e):
        self._drag = (e.x_root - self.tiktok.winfo_x(), e.y_root - self.tiktok.winfo_y())

    def _drag_move(self, e):
        dx, dy = self._drag
        self.tiktok.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def _drag_end(self, _e):
        self.cfg["tiktok_pos"] = [self.tiktok.winfo_x(), self.tiktok.winfo_y()]
        config.save(self.cfg)

    def _show_stream(self):
        """Barre Stream = 2 fenêtres l'une sur l'autre : derrière le fond coloré, transparent (réglable),
        devant les chiffres, les images et les traits, bien nets."""
        if self.stream is None:
            W, H, x, y = self._card_geo()
            if self._live() or self._opacity() >= 0.99:     # barre pleine : UNE fenêtre, textes nets (lissés sur le fond)
                self.stream, self.cv_s = self._overlay(f"{config.APP_NAME} – Stream")
                self.cv_s.config(width=W, height=H)
                self.stream.geometry(f"{W}x{H}+{x}+{y}")
                self.stream.deiconify()
                self.root.after(80, self._apply_lock)
                self.root.after(120, self._keep_on_top)
                return
            self.stream_bg, self.cv_b = self._overlay(f"{config.APP_NAME} – Stream (fond)", alpha=self._opacity())
            self.cv_b.config(width=W, height=H)
            self.stream_bg.geometry(f"{W}x{H}+{x}+{y}")
            self.stream, self.cv_s = self._overlay(f"{config.APP_NAME} – Stream")
            self.cv_s.config(width=W, height=H)
            self.stream.geometry(f"{W}x{H}+{x}+{y}")
        if self.stream_bg is not None:
            self.stream_bg.deiconify()
        self.stream.deiconify()
        if self.stream_bg is not None:
            self.stream.lift(self.stream_bg)
        self.root.after(80, self._apply_lock)
        self.root.after(120, self._keep_on_top)
        self.root.after(150, self._check_alpha)

    def _check_alpha(self):
        """La transparence du fond de barre, remise si Windows / Linux l'a perdue (fenêtre cachée puis remontrée…)."""
        w = self.stream_bg
        if w is None or not w.winfo_exists():
            return
        try:
            if abs(float(w.attributes("-alpha")) - self._opacity()) > 0.005:
                w.attributes("-alpha", self._opacity())
        except (tk.TclError, ValueError):
            pass

    def _app_windows(self):
        """Fenêtres de l'appli (principale, Lancer un farm, chiffres, tutoriel…), sans la carte ni la barre."""
        over = (self.tiktok, self.stream, self.stream_bg, getattr(self, "_unk", None), self.bub, self.mini)
        out = [self.root] + [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel) and w not in over]
        return [w for w in out if w.winfo_exists() and w.winfo_ismapped() and w.state() != "iconic"]

    @staticmethod
    def _we_have_focus():
        """L'utilisateur est sur une fenêtre de l'appli (pas sur le jeu) ?"""
        if not WIN:
            return False
        try:
            import ctypes
            u32 = ctypes.windll.user32
            pid = ctypes.c_ulong()
            u32.GetWindowThreadProcessId(u32.GetForegroundWindow(), ctypes.byref(pid))
            return pid.value == os.getpid()
        except Exception:
            return False

    def _keep_on_top(self, front=None):
        """Le jeu (fenêtré sans bordure) peut passer devant : on remet l'overlay au premier plan, sans prendre le focus.
        Quand tu es sur l'appli (menu, « Lancer un farm », chiffres…), ses fenêtres passent DEVANT la barre ;
        quand tu retournes sur le jeu, elles redeviennent normales (le jeu passe devant elles, pas devant la barre)."""
        front = self._we_have_focus() if front is None else front
        if self.mode == "stream":
            self._check_alpha()
        wins = [] if self.hidden else [w for w in ((self.stream_bg, self.stream) if self.mode == "stream" else
                                                   (self.tiktok,) if self.mode == "tiktok" else ()) if w is not None]
        for b in (self.bub, self.mini):                       # logo et mini menu : toujours devant le jeu
            if b is not None and b.winfo_exists() and b.state() != "withdrawn":
                wins.append(b)
        try:
            if WIN:
                import ctypes
                u32 = ctypes.windll.user32
                flags = 0x0001 | 0x0002 | 0x0010                      # NOSIZE | NOMOVE | NOACTIVATE
                unk = getattr(self, "_unk", None)                     # question « quelle bête ? » : toujours devant
                for w in wins + ([unk] if unk is not None and unk.winfo_exists() else []):
                    u32.SetWindowPos(int(w.wm_frame(), 16), -1, 0, 0, 0, 0, flags | 0x0040)
                if front or self._front:
                    for w in self._app_windows():                     # -1 = TOPMOST (devant la barre), -2 = normal
                        u32.SetWindowPos(int(w.wm_frame(), 16), -1 if front else -2, 0, 0, 0, 0, flags)
            else:
                for w in wins:
                    w.attributes("-topmost", True)
                if self.stream is not None and self.stream_bg is not None and self.mode == "stream":
                    self.stream.lift(self.stream_bg)
                for w in self._app_windows() if (front or self._front) else ():
                    w.attributes("-topmost", bool(front))
                    if front:
                        w.lift()
        except Exception:
            pass
        self._front = front

    # ================================================================ données affichées
    def data(self):
        f = self.farms.get()
        if not f:
            return None
        big = f["since_go"] if self.cfg["big"] == "since" else f["count"]
        return {"name": fname(f), "reserve": fres(f), "count": f["count"], "since": f["since_go"],
                "last_go": f.get("last_go"), "total": f.get("total", f["count"]),
                "go": f["go_total"], "grades": f["grades"], "big": big,
                "big_label": T("kills du farm · depuis le GO" if self.cfg["big"] == "since" else "total du farm"),
                "img": gd.animal_image(f["species_en"]), "rid": f.get("rid")}

    # ================================================================ fenêtre principale
    def _btn(self, parent, text, cmd, primary=False, w=None):
        """Bouton arrondi en relief (RButton)."""
        return RButton(parent, text=text, command=cmd, bg=ACC if primary else BTN, fg="#ffffff" if primary else FG,
                       font=(UI, 9, "bold"), width=w)

    def _build_window(self):
        r = self.root
        self.cv_w = tk.Canvas(r, width=380, height=268, bg=BG, highlightthickness=0)
        self.cv_w.pack(padx=12, pady=(12, 0))
        self.sug = tk.Frame(r, bg=PANEL, padx=10, pady=8)
        self.sug_lbl = tk.Label(self.sug, text="", bg=PANEL, fg=FG, font=(UI, 9), justify="left", wraplength=250)
        self.sug_lbl.pack(side="left")
        self._btn(self.sug, T("Farmer celle-là"), self._farm_suggest, primary=True).pack(side="right")
        row = tk.Frame(r, bg=BG)
        row.pack(fill="x", padx=12, pady=(10, 0))
        self.b_new = self._btn(row, T("▶ Lancer un farm"), self.new_farm, primary=True)
        self.b_new.pack(side="left")
        b = self.b_farms = self._btn(row, T("☰ Mes farms"), None)
        b.config(command=lambda b=b: self.farms_menu(b))
        b.pack(side="left", padx=6)
        b2 = self.b_set = self._btn(row, "⚙", None)
        b2.config(command=lambda b=b2: self.settings_menu(b))
        b2.pack(side="right")
        row2 = self.row_fix = tk.Frame(r, bg=BG)
        row2.pack(fill="x", padx=12, pady=(6, 0))
        self._btn(row2, "−1", self.minus, w=4).pack(side="left")
        self._btn(row2, "+1", self.plus, w=4).pack(side="left", padx=6)
        self._btn(row2, T("↶ Annuler le dernier kill"), self.undo).pack(side="left")
        row3 = self.row_modes = tk.Frame(r, bg=BG)
        row3.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(row3, text=T("Affichage :"), bg=BG, fg=DIM, font=(UI, 9)).pack(side="left")
        self.mode_btns = {}
        for md in MODES:
            b = self._btn(row3, T(MODE_NAMES[md]), lambda md=md: self.set_mode(md))
            b.pack(side="left", padx=(6, 0))
            self.mode_btns[md] = b
        self.lbl_status = tk.Label(r, text="", bg=BG, fg=DIM, font=(UI, 8), anchor="w", justify="left", wraplength=380)
        self.lbl_status.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(r, text=T("F7 = affichage · F8 = cacher · ² = bloquer / débloquer la barre Stream"), bg=BG, fg=EDGE,
                 font=(UI, 8)).pack(fill="x", padx=12, pady=(2, 12), anchor="w")

    def _farm_suggest(self):
        if self.suggest:
            self.new_farm(preset=self.suggest)

    def render(self):
        d = self.data()
        try:
            webbar.set_data(self._web_payload(d))
        except Exception:
            pass
        self._render_window(d)
        if self.mode == "tiktok" and self.tiktok is not None:
            self._render_tiktok(d)
        if self.mode == "stream" and self.stream is not None:
            self._render_stream(d)
            if self._opacity() < 0.99 and not self._live():
                self._shadow(self.cv_s)
        self._bubble_update(d)
        if self.cfg.get("live_window"):
            self._ensure_live_win()
            if self.live_win is not None:
                self._render_stream(d, cv=self.cv_live, solo=True)

    @staticmethod
    def _shadow(cv):
        """Barre transparente : une ombre noire sous chaque texte, pour le lire même sur un décor clair (neige, ciel)."""
        for it in cv.find_all():
            if cv.type(it) != "text" or "flat" in cv.gettags(it):     # texte posé sur un fond plein : pas d'ombre
                continue
            x, y = cv.coords(it)
            for dx, dy in ((1, 1), (2, 2)):
                sh = cv.create_text(x + dx, y + dy, text=cv.itemcget(it, "text"), font=cv.itemcget(it, "font"),
                                    anchor=cv.itemcget(it, "anchor"), fill="#000000")
                cv.tag_lower(sh, it)

    def _render_window(self, d):
        cv = self.cv_w
        cv.delete("all")
        W, H = 380, 268
        rounded(cv, 1, 1, W - 1, H - 1, 18, fill=CARD, outline=EDGE)
        if not d:
            logo = self.pics.get(config.LOGO_PNG, 56) if config.LOGO_PNG.exists() else None
            if logo:
                cv.create_image(W / 2, 40, image=logo)
            cv.create_text(W / 2, 86, text=T("Aucun farm lancé"), fill=FG, font=(UI, 15, "bold"))
            cv.create_text(W / 2, 146, text=T("Clique sur « ▶ Lancer un farm » :\nchoisis la réserve et l'animal.\n"
                           "Chaque bête ramassée sera\ncomptée toute seule."), fill=DIM, font=(UI, 10), justify="center",
                           width=W - 40)
            self._render_grades(cv, None, 12, 206, W - 24)
        else:
            bub = self.pics.get(d["img"], 78, circle=True, ring=ACC)
            if bub:
                cv.create_image(54, 54, image=bub)
            f_name = fit_font(d["name"], UI, 15, W - 120, min_size=11)
            cv.create_text(104, 40, text=fit(d["name"], f_name, W - 120), anchor="w", fill=FG, font=f_name)
            logo = self.pics.get(gd.reserve_logo(d["rid"]), 18) if d["rid"] is not None else None
            x = 104
            if logo:
                cv.create_image(x + 9, 66, image=logo)
                x += 22
            f_res = tkfont.Font(family=UI, size=10)
            cv.create_text(x, 64, text=fit(d["reserve"], f_res, W - x - 16), anchor="w", fill=DIM, font=f_res)
            f_info = tkfont.Font(family=UI, size=9, weight="bold")
            info = T("Dernier GO tombé en {x}", x=kills(d['last_go']) if d['last_go'] else T("— (pas encore de GO)"))
            cv.create_text(104, 87, text=fit(info, f_info, W - 120), anchor="w", fill=GOLD, font=f_info)
            cv.create_line(16, 104, W - 16, 104, fill=EDGE)
            f_lab = tkfont.Font(family=UI, size=8, weight="bold")
            cv.create_text(20, 122, text=fit(d["big_label"].upper(), f_lab, W - 190), anchor="w", fill=DIM, font=f_lab)
            other = (T("Total du farm"), d["count"]) if self.cfg["big"] == "since" else (T("Depuis le dernier GO"), d["since"])
            f_other = fit_font(fmt(other[1]), NUM, 16, 150)
            right_w = max(f_other.measure(fmt(other[1])), 130) + 30   # place prise par la colonne de droite
            f_big = fit_font(fmt(d["big"]), NUM, 40, W - 16 - right_w - 30)
            cv.create_text(16, 158, text=fmt(d["big"]), anchor="w", fill=ACC if self.cfg["big"] == "since" else FG, font=f_big)
            self._plus_anim(cv, 16 + f_big.measure(fmt(d["big"])) + 8, 158, 20)
            cv.create_text(W - 20, 130, text=other[0], anchor="e", fill=DIM, font=(UI, 8, "bold"))
            cv.create_text(W - 20, 150, text=fmt(other[1]), anchor="e", fill=FG,
                           font=f_other)
            go_img = self.pics.get(gd.badge(5), 18)
            go_txt = f"{d['go']} Great One{'s' if d['go'] > 1 else ''}"
            cv.create_text(W - 20, 176, text=go_txt, anchor="e", fill=GOLD, font=(UI, 10, "bold"))
            if go_img:
                cv.create_image(W - 26 - tkfont.Font(family=UI, size=10, weight="bold").measure(go_txt) - 8, 176, image=go_img)
            self._render_grades(cv, d["grades"], 12, 206, W - 24)
            self._go_flash(cv, W / 2, 152, 22)
        # suggestion « Farmer celle-là »
        if self.suggest:
            en, name, rid, g = self.suggest
            res = gd.reserve_label(rid) if rid is not None else T("réserve inconnue")
            head = T("Tu viens de ramasser" if g is not None else "Ta dernière bête ramassée")
            self.sug_lbl.config(text=T("{head} : {name} ({res}).\nLancer un farm de cette bête ?", head=head, name=name,
                                       res=res))
            if not self.sug.winfo_ismapped():
                self.sug.pack(fill="x", padx=12, pady=(10, 0), after=self.cv_w)
        elif self.sug.winfo_ismapped():
            self.sug.pack_forget()
        self.b_new.config(text=T("▶ Lancer un farm" if not d else "▶ Nouveau farm"))
        for md, b in self.mode_btns.items():
            b.config(bg=ACC if md == self.mode else BTN, fg="#ffffff" if md == self.mode else FG)
        self.lbl_status.config(text=self.status)
        box = getattr(self, "tuto_box", None)                 # zone montrée par le tutoriel
        if box:
            cv.create_rectangle(*box, outline=GOLD, width=3, dash=(6, 3))

    def _render_grades(self, cv, grades, x0, y0, width, size=30, tag="g"):
        cw = width / 6
        for g in range(6):
            cx = x0 + cw * g + cw / 2
            img = self.pics.get(gd.badge(g), size)
            t = f"{tag}{g}"
            if img:
                cv.create_image(cx, y0 + size / 2, image=img, tags=(t,))
            n = "–" if grades is None else short_num(grades[g])
            cv.create_text(cx, y0 + size + 14, text=n, fill=GRADE_COL[g], font=(NUM, 13, "bold"), tags=(t,))
            cv.tag_bind(t, "<Button-3>", lambda e, g=g: self.grade_menu(e, g))

    def _plus_anim(self, cv, x, y, size):
        t = self._anim_t()
        if t is None or self.anim[1] == fm.GO:
            return
        cv.create_text(x, y - 4 - 20 * t, text="+1", anchor="w", fill=mix(LEAF, CARD, max(0.0, (t - 0.45) / 0.55)),
                       font=(NUM, size, "bold"))

    def _go_flash(self, cv, x, y, size):
        t = self._anim_t()
        if t is None or self.anim[1] != fm.GO:
            return
        col = GOLD if int(t * 12) % 2 == 0 else FG
        f = tkfont.Font(family=NUM, size=size, weight="bold")
        w, h = f.measure("GREAT ONE !") / 2 + 18, f.metrics("linespace") / 2 + 6
        rounded(cv, x - w, y - h, x + w, y + h, 12, fill=CARD, outline=GOLD, width=2)    # bandeau par-dessus le reste
        cv.create_text(x, y, text="GREAT ONE !", fill=col, font=f)

    # ================================================================ carte TikTok
    def _render_tiktok(self, d):
        cv, s = self.cv_t, self.t_scale
        cv.delete("all")
        W, H = round(300 * s), round(470 * s)
        S = lambda v: round(v * s)
        rounded(cv, 2, 2, W - 2, H - 2, S(26), fill=CARD, outline=ACC, width=2)
        if not d:
            cv.create_text(W / 2, H / 2, text=T("Aucun farm\n\nClic droit >\n▶ Lancer un nouveau farm"), fill=DIM,
                           font=(UI, S(12), "bold"), justify="center")
            return
        bub = self.pics.get(d["img"], S(124), circle=True, ring=ACC)
        if bub:
            cv.create_image(W / 2, S(84), image=bub)
        f_name = fit_font(d["name"].upper(), UI, S(15), W - S(30), min_size=max(8, S(10)))
        cv.create_text(W / 2, S(166), text=fit(d["name"].upper(), f_name, W - S(30)), fill=ACC, font=f_name)
        cv.create_text(W / 2, S(188), text=d["reserve"], fill=DIM, font=(UI, S(10)))
        f_big = fit_font(fmt(d["big"]), NUM, S(50), W - S(70))
        cv.create_text(W / 2, S(240), text=fmt(d["big"]), fill=ACC if self.cfg["big"] == "since" else FG, font=f_big)
        self._plus_anim(cv, W / 2 + f_big.measure(fmt(d["big"])) / 2 + S(6), S(240), S(20))
        cv.create_text(W / 2, S(280), text=d["big_label"], fill=DIM, font=(UI, S(9)))
        sub = (T("Total du farm {n} · {go} GO", n=fmt(d['count']), go=d['go']) if self.cfg["big"] == "since"
               else T("{n} depuis le dernier GO · {go} GO", n=fmt(d['since']), go=d['go']))
        cv.create_text(W / 2, S(302), text=sub, fill=ACC, font=(UI, S(10), "bold"))
        f_inf = tkfont.Font(family=UI, size=S(9), weight="bold")
        inf = T("Dernier GO tombé en {x}", x=kills(d['last_go']) if d['last_go'] else '—')
        cv.create_text(W / 2, S(323), text=fit(inf, f_inf, W - S(24)), fill=GOLD, font=f_inf)
        cv.create_line(S(24), S(342), W - S(24), S(342), fill=EDGE)
        cw = (W - S(30)) / 3                                  # grades : 3 colonnes x 2 lignes
        for g in range(6):
            col, row = g % 3, g // 3
            cx, cy = S(15) + cw * col + cw / 2, S(370) + row * S(40)
            img = self.pics.get(gd.badge(g), S(28))
            if img:
                cv.create_image(cx - S(18), cy, image=img)
            gt = short_num(d["grades"][g])
            cv.create_text(cx - S(2), cy, text=gt, anchor="w", fill=GRADE_COL[g],
                           font=fit_font(gt, NUM, S(14), cw / 2 + S(14), min_size=8))
        cv.create_text(W / 2, H - S(14), text=f"{config.APP_NAME} · {config.SIGNATURE} · {config.TIKTOK_NAME}", fill=ACC,
                       font=(UI, max(7, S(8)), "italic"))
        self._go_flash(cv, W / 2, S(240), S(26))

    # ================================================================ barre Stream
    CARD_W, CARD_H = 1120, 118                              # tableau « compétitif » de la barre Stream

    def _card_geo(self):
        """Taille et place du tableau : centré, en bas (défaut) ou en haut de l'écran."""
        X, Y, SW, SH = self._scr()
        W, H = min(self.CARD_W, SW - 40), self.CARD_H
        side = self.cfg["bar_side"]
        y = 6 if side == "haut" else round(SH * 0.052) if side == "haut_hud" else SH - H - round(SH * 0.03)
        return W, H, X + (SW - W) // 2, Y + y

    @staticmethod
    def _chamfer(cv, x1, y1, x2, y2, c, **kw):
        """Rectangle aux coins coupés (style e-sport)."""
        pts = (x1 + c, y1, x2 - c, y1, x2, y1 + c, x2, y2 - c, x2 - c, y2, x1 + c, y2, x1, y2 - c, x1, y1 + c)
        return cv.create_polygon(*pts, **kw)

    def _render_stream(self, d, compact=0, cv=None, solo=False):
        """Barre Stream = TABLEAU compétitif : bête, kills du farm, dernier GO, total, 6 grades.
        solo = fenêtre « Live » (cv) : opaque, le tableau remplit la fenêtre."""
        cv = cv if cv is not None else self.cv_s
        cv.delete("all")
        W, H = int(cv.cget("width")), int(cv.cget("height"))
        k = W / self.CARD_W                                 # échelle (petit écran : tout rétrécit)
        z = lambda v: max(1, round(v * k))
        bg = getattr(self, "cv_b", None) if (self.stream_bg is not None and not solo) else None
        top, bot = z(18), H - 2
        body = dict(fill=CARD, outline="")
        if bg is not None:                                  # fond (réglable) dans la fenêtre transparente de derrière
            bg.delete("all")
            self._chamfer(bg, 1, top, W - 1, bot, z(16), **body)
        else:
            self._chamfer(cv, 1, top, W - 1, bot, z(16), **body)
        self._chamfer(cv, 1, top, W - 1, bot, z(16), fill="", outline=ACC, width=2)
        # onglet du haut : nom de l'appli à gauche, heure + signature à droite
        tab = (z(24), 0, z(24) + z(300), top + z(4))
        cv.create_polygon(tab[0], tab[1], tab[2], tab[1], tab[2] - z(12), tab[3], tab[0] + z(12), tab[3],
                          fill=ACC, outline="")
        cv.create_text(tab[0] + z(22), (tab[1] + tab[3]) / 2, text=T("KILLFARM · FARM EN COURS"), anchor="w",
                       fill="#ffffff", font=(UI, z(9), "bold"), tags="flat")
        clock = time.strftime("%H:%M")
        self._clock_shown = clock
        rt = (W - z(24) - z(250), 0, W - z(24), top + z(4))
        cv.create_polygon(rt[0], rt[1], rt[2], rt[1], rt[2] - z(12), rt[3], rt[0] + z(12), rt[3], fill=BG, outline=ACC)
        cv.create_text(rt[2] - z(24), (rt[1] + rt[3]) / 2, text=clock, anchor="e", fill=FG, font=(NUM, z(11), "bold"),
                       tags="flat")
        cv.create_text(rt[0] + z(24), (rt[1] + rt[3]) / 2, text=f"{config.SIGNATURE} · {config.TIKTOK_NAME}",
                       anchor="w", fill=ACC, font=(UI, z(8), "italic"), tags="flat")
        mid = (top + bot) / 2 + z(2)
        if not d:
            cv.create_text(W / 2, mid, text=config.APP_NAME + T(" · aucun farm lancé (clic droit > ▶ Lancer un nouveau farm)"),
                           fill=DIM, font=(UI, z(12), "bold"))
            return
        # bête
        B = z(80)
        bub = self.pics.get(d["img"], B, circle=True, ring=ACC)
        x = z(20)
        if bub:
            cv.create_image(x + B / 2, mid, image=bub)
        x += B + z(14)
        f_name, f_res = tkfont.Font(family=UI, size=z(15), weight="bold"), tkfont.Font(family=UI, size=z(9))
        name, res = fit(d["name"], f_name, z(220)), fit(d["reserve"], f_res, z(220))
        cv.create_text(x, mid - z(20), text=name, anchor="w", fill=FG, font=f_name)
        cv.create_text(x, mid + z(2), text=res, anchor="w", fill=DIM, font=f_res)
        gi = self.pics.get(gd.badge(fm.GO), z(18))
        gx = x
        if gi:
            cv.create_image(gx + z(9), mid + z(24), image=gi)
            gx += z(22)
        n_go = d["go"]
        cv.create_text(gx, mid + z(24), text=T("{n} Great One" if n_go <= 1 else "{n} Great Ones", n=fmt(n_go)),
                       anchor="w", fill=GOLD, font=(UI, z(9), "bold"))
        x += max(f_name.measure(name), f_res.measure(res), z(150)) + z(18)
        # chiffres (blocs)
        go_txt = fmt(d["last_go"]) if d["last_go"] else "—"
        blocks = ((T("KILLS DU FARM"), fmt(d["since"]), ACC, z(176), z(30)),
                  (T("DERNIER GO"), go_txt, GOLD, z(128), z(22)),
                  (T("TOTAL DU FARM"), fmt(d["count"]), FG, z(128), z(22)))
        for i, (lab, val, col, bw, fs) in enumerate(blocks):
            rounded(cv, x, mid - z(34), x + bw, mid + z(34), z(8), fill=BG, outline=EDGE if i else ACC, width=1 if i else 2)
            cv.create_text(x + bw / 2, mid - z(21), text=lab, fill=DIM, font=(UI, z(8), "bold"), tags="flat")
            fv = tkfont.Font(family=NUM, size=fs, weight="bold")
            cv.create_text(x + bw / 2, mid + z(8), text=fit(val, fv, bw - z(10)), fill=col, font=fv, tags="flat")
            if i == 0:
                self._plus_anim(cv, x + bw / 2 + fv.measure(val) / 2 + z(4), mid + z(2), z(14))
            x += bw + z(10)
        # grades : badge au-dessus, nombre dessous
        x += z(6)
        avail = W - z(18) - x
        cw = avail / 6
        bs = min(z(34), round(cw * 0.62))
        f_g = tkfont.Font(family=NUM, size=z(12), weight="bold")
        for g in range(6):
            cx = x + cw * g + cw / 2
            img = self.pics.get(gd.badge(g), bs)
            if img:
                cv.create_image(cx, mid - z(10), image=img)
            cv.create_text(cx, mid + z(24), text=short_num(d["grades"][g]), fill=GRADE_COL[g], font=f_g)
        self._go_flash(cv, W / 2, mid, z(26))
        if not solo:
            self._lock_note(cv, W / 2, mid)


# ==================================================================== lancer un farm
class NewFarm:
    COLS = 5

    def __init__(self, app, preset=None):
        self.app = app
        self.win = w = tk.Toplevel(app.root)
        w.title(T("Lancer un farm"))
        w.configure(bg=BG)
        if app.root.winfo_ismapped():                       # mini menu : la fenêtre principale est cachée
            w.transient(app.root)
        h = min(800, w.winfo_screenheight() - 80)
        w.geometry(f"700x{h}+{max(0, (w.winfo_screenwidth() - 700) // 2)}+{max(0, (w.winfo_screenheight() - h) // 2 - 20)}")
        w.protocol("WM_DELETE_WINDOW", self.close)
        w.minsize(600, 560)
        self.res_en = None                                  # None = toutes les réserves
        self.res_rid = None
        self.res_label = "Toutes les réserves"
        self.sp = None
        self.live_grade = None                              # « Farmer celle-là » juste après la récolte : elle compte
        self._imgs = []
        tk.Label(w, text=T("Lancer un farm"), bg=BG, fg=ACC, font=(UI, 15, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
        sug = app.suggest
        if sug:
            box = tk.Frame(w, bg=PANEL, padx=10, pady=8)
            box.pack(fill="x", padx=16, pady=(8, 0))
            res = gd.reserve_label(sug[2]) if sug[2] is not None else T("réserve inconnue")
            tk.Label(box, text=T("⚡ Ta dernière bête ramassée : {name} ({res})", name=sug[1], res=res), bg=PANEL, fg=FG,
                     font=(UI, 10, "bold")).pack(side="left")
            app._btn(box, T("Farmer celle-là"), lambda: self.use(sug), primary=True).pack(side="right")
        # 1. réserve
        tk.Label(w, text=T("1 · Réserve"), bg=BG, fg=FG, font=(UI, 11, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        self.res_frame = tk.Frame(w, bg=BG)
        self.res_frame.pack(fill="x", padx=16)
        self.res_btns = {}
        items = [(None, None, "Toutes les réserves", None)] + [(r[0], r[3], r[2], gd.reserve_logo(en=r[3])) for r in gd.RESERVES]
        for i, (rid, en, short, logo) in enumerate(items):
            img = app.pics.get(logo, 22, back=BTN) if logo else None
            if img:
                self._imgs.append(img)
            b = tk.Button(self.res_frame, text=" " + (gd.reserve_label(rid) if rid is not None else T(short)), image=img, compound="left", anchor="w", bd=0, padx=6, pady=3,
                          bg=BTN, fg=FG, activebackground=EDGE, activeforeground=FG, font=(UI, 9), cursor="hand2",
                          command=lambda rid=rid, en=en, short=short: self.pick_reserve(rid, en, short))
            b.grid(row=i // 4, column=i % 4, sticky="ew", padx=2, pady=2)
            self.res_btns[en] = b
        for c in range(4):
            self.res_frame.columnconfigure(c, weight=1)
        # 2. animal
        top = tk.Frame(w, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(top, text=T("2 · Animal"), bg=BG, fg=FG, font=(UI, 11, "bold")).pack(side="left")
        self.q = tk.StringVar()
        e = tk.Entry(top, textvariable=self.q, bg=PANEL, fg=FG, insertbackground=FG, relief="flat", font=(UI, 10), width=24)
        e.pack(side="right", ipady=3)
        tk.Label(top, text=T("Chercher :"), bg=BG, fg=DIM, font=(UI, 9)).pack(side="right", padx=4)
        self.q.trace_add("write", lambda *_: self.fill_animals())
        bot = tk.Frame(w, bg=PANEL, padx=12, pady=10)
        bot.pack(side="bottom", fill="x", padx=16, pady=12)
        mid = tk.Frame(w, bg=BG)
        mid.pack(fill="both", expand=True, padx=16)
        self.cv = tk.Canvas(mid, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.grid = tk.Frame(self.cv, bg=BG)
        self.cv.create_window(0, 0, window=self.grid, anchor="nw")
        self.grid.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        for wdg in (self.cv, self.grid):
            wdg.bind("<Enter>", lambda e: self._wheel(True))
            wdg.bind("<Leave>", lambda e: self._wheel(False))
        # 3. départ
        self.lbl_sel = tk.Label(bot, text=T("Choisis un animal ci-dessus."), bg=PANEL, fg=FG, font=(UI, 11, "bold"), anchor="w")
        self.lbl_sel.grid(row=0, column=0, columnspan=6, sticky="w")
        tk.Label(bot, text=T("Déjà commencé avant ? (sinon laisse 0)"), bg=PANEL, fg=DIM, font=(UI, 8)).grid(
            row=1, column=0, columnspan=6, sticky="w", pady=(4, 2))
        self.v_count, self.v_since, self.v_go = tk.IntVar(value=0), tk.IntVar(value=0), tk.IntVar(value=0)
        self.v_total, self.v_lastgo = tk.IntVar(value=0), tk.IntVar(value=0)
        fields = ((("Kills déjà faits", self.v_count), ("Depuis le dernier GO", self.v_since),
                   ("Great Ones déjà eus", self.v_go)),
                  (("Dernier GO tombé en (kills)", self.v_lastgo),))
        for r, row in enumerate(fields):
            for c, (lab, var) in enumerate(row):
                tk.Label(bot, text=T(lab), bg=PANEL, fg=FG, font=(UI, 9)).grid(row=2 + r, column=c * 2, sticky="w",
                                                                            padx=(0, 4), pady=2)
                ttk.Spinbox(bot, from_=0, to=9999999, textvariable=var, width=8).grid(row=2 + r, column=c * 2 + 1,
                                                                                      sticky="w", padx=(0, 12))
        self.b_go = app._btn(bot, T("▶ Démarrer le farm"), self.create, primary=True)
        self.b_go.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        self.b_go.config(state="disabled")
        self.pick_reserve(app.map_id if app.map_id in gd.BY_RID else None,
                          gd.BY_RID[app.map_id][3] if app.map_id in gd.BY_RID else None,
                          gd.BY_RID[app.map_id][2] if app.map_id in gd.BY_RID else "Toutes les réserves")
        if preset:
            self.use(preset)
        e.focus_set()

    def close(self):
        self._wheel(False)
        self.win.destroy()

    def _scroll(self, n):
        try:
            self.cv.yview_scroll(n, "units")
        except tk.TclError:                                 # fenêtre déjà fermée
            pass

    def _wheel(self, on):
        if on:
            self.win.bind_all("<MouseWheel>", lambda e: self._scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1)))
            self.win.bind_all("<Button-4>", lambda e: self._scroll(-2))
            self.win.bind_all("<Button-5>", lambda e: self._scroll(2))
        else:
            for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.win.unbind_all(s)

    def pick_reserve(self, rid, en, short):
        self.res_rid, self.res_en, self.res_label = rid, en, short
        for k, b in self.res_btns.items():
            b.config(bg=ACC if k == en else BTN, fg=BG if k == en else FG)
        if self.sp and en and en not in (self.sp.get("reserves") or {}):
            self.sp = None
        self.fill_animals()
        self.update_sel()

    def fill_animals(self):
        for c in self.grid.winfo_children():
            c.destroy()
        q = gd.norm(self.q.get())
        sps = [sp for sp in gd.species_list(self.res_en) if not q or q in gd.norm(gd.fr_name(sp)) or q in gd.norm(sp["en"])
               or q in gd.norm(gd.name(sp))]
        if not sps:
            hint = T("Aucun animal trouvé.") + (T("\nIl n'est peut-être pas dans {x} : essaie « Toutes les réserves ».",
                                                  x=self._res_shown()) if self.res_en else "")
            tk.Label(self.grid, text=hint, bg=BG, fg=DIM, font=(UI, 10), justify="left").grid(row=0, column=0, pady=20,
                                                                                              columnspan=self.COLS)
        for i, sp in enumerate(sps):
            img = self.app.pics.get(gd.animal_image(sp["en"]), 64, circle=True, ring=EDGE, back=BG)
            if img:
                self._imgs.append(img)
            sel = self.sp is not None and sp["en"] == self.sp["en"]
            b = tk.Button(self.grid, text=gd.name(sp), image=img, compound="top", bd=0, width=112, wraplength=108,
                          bg=ACC if sel else BG, fg=BG if sel else FG, activebackground=EDGE, activeforeground=FG,
                          font=(UI, 9), cursor="hand2", padx=2, pady=4,
                          command=lambda sp=sp: self.pick_species(sp))
            b.grid(row=i // self.COLS, column=i % self.COLS, padx=3, pady=3, sticky="n")
        self.cv.yview_moveto(0)

    def pick_species(self, sp):
        self.sp = sp
        self.fill_animals()
        self.update_sel()

    def use(self, sug):
        en, name, rid = sug[:3]
        self.live_grade = sug[3] if len(sug) > 3 else None
        r = gd.BY_RID.get(rid)
        self.pick_reserve(rid if r else None, r[3] if r else None, r[2] if r else "Toutes les réserves")
        sp = gd.species_by_en(en)
        if sp:
            self.pick_species(sp)

    def _res_shown(self):
        return gd.reserve_label(self.res_rid) if self.res_en and self.res_rid is not None else T(self.res_label)

    def update_sel(self):
        if self.sp:
            self.lbl_sel.config(text=f"Farm : {gd.name(self.sp)} · {self._res_shown()}")
            self.b_go.config(state="normal")
        else:
            self.lbl_sel.config(text=T("Choisis un animal ci-dessus."))
            self.b_go.config(state="disabled")

    def create(self):
        if not self.sp:
            return
        def num(v):
            try:
                return max(0, int(v.get()))
            except (tk.TclError, ValueError):
                return 0
        count, since, go = num(self.v_count), num(self.v_since), num(self.v_go)
        total, last_go = num(self.v_total), num(self.v_lastgo)
        count = max(count, since)                           # « depuis le dernier GO » ne peut pas dépasser le total
        rid = self.res_rid if self.res_en else None
        self.app.farms.create(self.sp["en"], gd.fr_name(self.sp), rid, self.res_label, count=count,
                              since_go=since if (since or go) else count, go_total=go,
                              grades=[0, 0, 0, 0, 0, go], last_go=last_go or None, total=max(total, count))
        sug = self.app.suggest
        if sug and sug[0] == self.sp["en"]:
            if sug[3] is not None and self.live_grade is not None:     # la bête qu'on vient de ramasser compte
                self.app.farms.add_kill(self.app.farms.active, sug[3])
            self.app.suggest = None
        self.app.status = T("Farm lancé : {name} · {res}. Bonne chasse !", name=gd.name(self.sp), res=self._res_shown())
        self.close()
        self.app.render()


# ==================================================================== tutoriel
class Tutorial:
    """Visite guidée : une bulle à côté de la fenêtre, l'élément expliqué clignote (ou est entouré)."""
    W = 330

    def __init__(self, app):
        old = getattr(app, "_tuto", None)
        if old is not None:
            old.finish(save=False)
        app._tuto = self
        self.app = app
        self.i = 0
        self.blink_job = None
        self.target = None
        if app.mode != "fenetre":
            app.set_mode("fenetre")
        app.root.deiconify()
        app.root.lift()
        has_farm = bool(app.farms.order)
        self.steps = [(T(a), T(b), c) for a, b, c in [
            ('Bienvenue dans KillFarm Lite',
             "L'appli compte toute seule les bêtes que tu RAMASSES dans theHunter, avec leur grade.\n\nElle lit seulement ta sauvegarde : elle ne touche jamais au jeu.\n\nCe tuto te montre tout en 1 minute.",
             None),
            ('1. Lancer un farm',
             "Clique ici, choisis la réserve (celle où tu joues est déjà choisie), puis l'animal. C'est tout !\n\nFarm déjà commencé ? Mets tes chiffres au départ. Plus rapide : quand tu ramasses une bête sans farm, un bandeau « Farmer celle-là » apparaît.",
             lambda: app.b_new),
            ('2. Ton compteur',
             'Le grand chiffre = tes kills depuis le dernier Great One (ou le total du farm : au choix dans ⚙ > Affichage).\n\nÀ droite : le total du farm et tes Great Ones. En haut : en combien de kills est tombé ton dernier GO.',
             (8, 8, 372, 198)),
            ('3. Les grades et le Great One',
             "Chaque bête ramassée est rangée selon sa médaille : sans médaille, bronze, argent, or, diamant, Great One.\n\nQuand ton Great One tombe, le compteur repart de 0 tout seul et « GREAT ONE ! » s'affiche. Pas reconnu ? Clic droit > « Mon dernier kill était un Great One ». Clic droit sur un badge = +1 / −1.",
             (8, 200, 372, 264)),
            ('4. Corriger',
             '« −1 / +1 » pour ajuster le compteur.\n« Annuler le dernier kill » si une bête a été comptée par erreur.',
             lambda: app.row_fix),
            ('5. Mes farms',
             "Tous tes farms : passe de l'un à l'autre, modifie les chiffres ou supprime un farm.\n\nTous tes farms comptent en même temps.",
             lambda: app.b_farms),
            ('6. Les affichages',
             "Fenêtre = ce panneau.\nTikTok = une carte à glisser où tu veux, pour tes vidéos.\nStream = un tableau en bas au centre de l'écran : bête, kills du farm, dernier GO, total, grades.\n\nF7 = changer d'affichage, F8 = cacher / montrer, ² (sous Échap) = la souris passe à travers le tableau ou non.",
             lambda: app.row_modes),
            ('7. Le mini menu',
             "Ton logo reste collé au bord droit de l'écran, par-dessus le jeu. Glisse-le : il se colle au bord le plus proche.\n\nUn clic dessus : le mini menu sort (+1 KILL, Annuler, Great One, Changer de farm) et cette grande fenêtre se range. « Grande fenêtre » la rouvre.",
             None),
            ('8. Ta barre sur ton live',
             "Mini menu > « Lien du live » : l'adresse est copiée.\n\nTikTok LIVE Studio : Ajouter une source > Lien > colle > résolution 1120 x 124.\nOBS : source Navigateur, 1120 x 124.\n\nLes chiffres bougent en direct pendant ton live. Garde l'appli ouverte.",
             None),
            ('9. Réglages',
             '⚙ en 4 parties : Affichage (7 couleurs dont TikTok, Twitch, YouTube, écran, langue), Barre Stream & live, Sauvegarde & fichiers, Aide & réseaux (ce tuto, Discord).\n\nClic droit sur le tableau, la carte ou le logo = le même menu rapide.',
             lambda: app.b_set),
            ('Dernier conseil',
             'Mets le jeu en « Fenêtré sans bordure » (Options > Affichage) : en « Plein écran », Windows cache le tableau et le mini menu derrière le jeu.\n\nBonne chasse !',
             None),
        ]]
        self.has_farm = has_farm
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=ACC)
        inner = tk.Frame(w, bg=PANEL, padx=14, pady=12)
        inner.pack(padx=2, pady=2)
        top = tk.Frame(inner, bg=PANEL)
        top.pack(fill="x")
        self.logo = app.pics.get(config.LOGO_PNG, 36, back=PANEL) if config.LOGO_PNG.exists() else None
        if self.logo:
            tk.Label(top, image=self.logo, bg=PANEL).pack(side="left", padx=(0, 8))
        self.l_step = tk.Label(top, text="", bg=PANEL, fg=DIM, font=(UI, 8, "bold"), anchor="w")
        self.l_step.pack(side="left", fill="x")
        self.l_title = tk.Label(inner, text="", bg=PANEL, fg=ACC, font=(UI, 12, "bold"), anchor="w", justify="left",
                                wraplength=self.W)
        self.l_title.pack(fill="x", pady=(2, 6))
        self.l_text = tk.Label(inner, text="", bg=PANEL, fg=FG, font=(UI, 10), anchor="w", justify="left",
                               wraplength=self.W)
        self.l_text.pack(fill="x")
        bar = tk.Frame(inner, bg=PANEL)
        bar.pack(fill="x", pady=(12, 0))
        self.b_skip = app._btn(bar, T("Passer"), lambda: self.finish())
        self.b_skip.pack(side="left")
        self.b_next = app._btn(bar, T("Suivant ▶"), self.next, primary=True)
        self.b_next.pack(side="right")
        self.b_prev = app._btn(bar, "◀", self.prev)
        self.b_prev.pack(side="right", padx=6)
        w.bind("<Escape>", lambda e: self.finish())
        for wid in (w, inner, top):                        # la bulle du tuto se déplace aussi à la souris
            wid.bind("<ButtonPress-1>", self._grab, add="+")
            wid.bind("<B1-Motion>", self._drag, add="+")
        self.show()

    def _grab(self, e):
        if isinstance(e.widget, tk.Button):                  # « Suivant », « Passer »… : pas un déplacement
            self._d = None
            return
        self._d = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _drag(self, e):
        d = getattr(self, "_d", None)
        if d:
            self.moved = True
            self.win.geometry(f"+{e.x_root - d[0]}+{e.y_root - d[1]}")

    def show(self):
        app = self.app
        self._unhighlight()
        title, text, target = self.steps[self.i]
        last = self.i == len(self.steps) - 1
        self.l_step.config(text=T("TUTORIEL · {a} / {b}", a=self.i + 1, b=len(self.steps)))
        self.l_title.config(text=title)
        self.l_text.config(text=text)
        self.b_prev.config(state="normal" if self.i else "disabled")
        self.b_next.config(text=T(("▶ Lancer mon premier farm" if not self.has_farm else "Terminer") if last else "Suivant ▶"))
        app.tuto_box = target if isinstance(target, tuple) else None
        self.target = target() if callable(target) else None
        app.render()
        self._blink(True)
        self._place()

    def _place(self):
        r = self.app.root
        if getattr(self, "moved", False):                    # tu as déplacé la bulle : elle reste où tu l'as mise
            self.win.lift()
            return
        r.update_idletasks()
        self.win.update_idletasks()
        tw, th = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        x = r.winfo_rootx() + r.winfo_width() + 14
        if x + tw > sw:                                      # pas la place à droite : à gauche de la fenêtre
            x = max(0, r.winfo_rootx() - tw - 14)
        title, text, target = self.steps[self.i]
        if self.target is not None:
            y = self.target.winfo_rooty() - 20
        elif isinstance(target, tuple):
            y = self.app.cv_w.winfo_rooty() + target[1]
        else:
            y = r.winfo_rooty() + 20
        y = max(0, min(y, sh - th - 40))
        self.win.geometry(f"+{x}+{y}")
        self.win.lift()

    def _blink(self, on):
        """Fait clignoter l'élément expliqué (un bouton, ou chaque bouton d'une rangée) en doré."""
        t = self.target
        if t is None:
            return
        try:
            if getattr(self, "_orig", None) is None:
                ws = [c for c in t.winfo_children() if isinstance(c, (tk.Button, RButton))] if isinstance(t, tk.Frame) else [t]
                self._orig = {wd: (wd.cget("bg"), wd.cget("fg")) for wd in ws}
            for wd, (bg, fg) in self._orig.items():
                wd.config(bg=GOLD if on else bg, fg=BG if on else fg)
        except tk.TclError:
            return
        self.blink_job = self.app.root.after(550, lambda: self._blink(not on))

    def _unhighlight(self):
        if self.blink_job:
            self.app.root.after_cancel(self.blink_job)
            self.blink_job = None
        for wd, (bg, fg) in (getattr(self, "_orig", None) or {}).items():
            try:
                wd.config(bg=bg, fg=fg)
            except tk.TclError:
                pass
        self._orig = None

    def next(self):
        if self.i < len(self.steps) - 1:
            self.i += 1
            self.show()
            return
        self.finish()
        if not self.has_farm:
            self.app.new_farm()

    def prev(self):
        if self.i:
            self.i -= 1
            self.show()

    def finish(self, save=True):
        self._unhighlight()
        self.app.tuto_box = None
        self.app._tuto = None
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        first = save and not self.app.cfg.get("tuto_vu")
        if first:
            self.app.cfg["tuto_vu"] = True
            config.save(self.app.cfg)
        self.app.render()
        if first and WIN:
            if messagebox.askyesno(config.APP_NAME, T("Créer un raccourci « KillFarm Lite » (avec le logo) sur ton Bureau ?\n\n"
                                   "Tu pourras lancer l'appli en double-cliquant dessus."), parent=self.app.root):
                self.app.make_shortcut()


# ==================================================================== modifier les chiffres
class EditNumbers:
    """Modifier les chiffres du farm (farm commencé avant l'appli, oubli…). Un seul champ pour les Great Ones."""

    def __init__(self, app):
        f = app.farms.get()
        if not f:
            return
        self.app = app
        w = self.win = tk.Toplevel(app.root)
        w.title(T("Modifier les chiffres"))
        w.configure(bg=BG, padx=16, pady=14)
        if app.root.winfo_ismapped():
            w.transient(app.root)
        w.resizable(False, False)
        tk.Label(w, text=f"{fname(f)} · {fres(f)}", bg=BG, fg=ACC, font=(UI, 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.vars = {}
        rows = [("count", T("Total du farm (tous les kills)"), f["count"], FG),
                ("since_go", T("Kills depuis le dernier Great One"), f["since_go"], FG),
                ("go_total", "Great Ones", f["go_total"], GRADE_COL[fm.GO]),
                ("last_go", T("Dernier GO tombé en (kills)"), f.get("last_go") or 0, FG)]
        rows += [(f"g{i}", T(fm.GRADES[i]), f["grades"][i], GRADE_COL[i]) for i in range(5)]
        for i, (k, lab, val, col) in enumerate(rows, 1):
            if i == 5:
                tk.Label(w, text=T("Grades des bêtes ramassées"), bg=BG, fg=DIM, font=(UI, 8, "bold")).grid(
                    row=50, column=0, columnspan=2, sticky="w", pady=(8, 2))
            tk.Label(w, text=lab, bg=BG, fg=col, font=(UI, 10)).grid(row=i if i < 5 else 50 + i, column=0, sticky="w",
                                                                     pady=2, padx=(0, 12))
            v = tk.IntVar(value=val)
            ttk.Spinbox(w, from_=0, to=9999999, textvariable=v, width=9).grid(row=i if i < 5 else 50 + i, column=1,
                                                                               sticky="w")
            self.vars[k] = v
        bar = tk.Frame(w, bg=BG)
        bar.grid(row=99, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        app._btn(bar, T("Enregistrer"), self.ok, primary=True).pack(side="left")
        app._btn(bar, T("Annuler"), w.destroy).pack(side="left", padx=6)
        w.update_idletasks()
        w.geometry(f"+{(w.winfo_screenwidth() - w.winfo_reqwidth()) // 2}+{(w.winfo_screenheight() - w.winfo_reqheight()) // 3}")

    def ok(self):
        try:
            v = {k: max(0, int(x.get())) for k, x in self.vars.items()}
        except (tk.TclError, ValueError):
            messagebox.showerror(T("Modifier les chiffres"), T("Mets uniquement des nombres."), parent=self.win)
            return
        count = max(v["count"], v["since_go"])              # « depuis le dernier GO » ne dépasse jamais le total
        grades = [v[f"g{i}"] for i in range(5)] + [v["go_total"]]
        self.app.farms.set_numbers(self.app.farms.active, count, v["since_go"], v["go_total"], grades,
                                   last_go=v["last_go"] or None)
        self.win.destroy()
        self.app.status = T("Chiffres enregistrés ✓")
        self.app.render()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
