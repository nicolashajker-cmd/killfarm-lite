"""Raccourcis clavier globaux (marchent même quand le jeu a le focus). Windows uniquement, sans dépendance."""
import sys
import threading

MODS = {"ALT": 1, "CTRL": 2, "CONTROL": 2, "SHIFT": 4, "WIN": 8}
NAMED = {"²": 0xDE, "SQUARE": 0xDE, "PAGEUP": 0x21, "PAGEDOWN": 0x22, "END": 0x23, "HOME": 0x24, "INSERT": 0x2D, "DELETE": 0x2E}


UNDER_ESC = {"²", "SQUARE", "`", "~", "BACKQUOTE", "GRAVE", "UNDER_ESC"}


def under_esc_vk():
    """La touche sous Échap (² en AZERTY, ` en QWERTY, ^ en QWERTZ…) : même touche physique (code 0x29) quel que soit
    le clavier ; Windows dit quelle touche virtuelle elle donne sur le clavier de l'utilisateur."""
    try:
        import ctypes
        vk = ctypes.windll.user32.MapVirtualKeyW(0x29, 1)                    # MAPVK_VSC_TO_VK
        if vk:
            return vk
    except Exception:
        pass
    return 0xDE


def parse(spec):
    parts = [p.strip().upper() for p in spec.split("+")]
    mods = 0
    for p in parts[:-1]:
        mods |= MODS[p]
    key = parts[-1]
    if key in UNDER_ESC:
        vk = under_esc_vk()
    elif key in NAMED:
        vk = NAMED[key]
    elif key.startswith("F") and key[1:].isdigit():
        vk = 0x70 + int(key[1:]) - 1
    elif len(key) == 1:
        vk = ord(key)
    else:
        raise KeyError(key)
    return mods, vk


class HotkeyManager(threading.Thread):
    def __init__(self, bindings, out_queue):
        super().__init__(daemon=True)
        self.bindings, self.out = bindings, out_queue

    def run(self):
        if not sys.platform.startswith("win"):
            return
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        ids = {}
        for i, (name, spec) in enumerate(self.bindings.items(), 1):
            try:
                mods, vk = parse(spec)
                ok = user32.RegisterHotKey(None, i, mods | 0x4000, vk)   # 0x4000 = MOD_NOREPEAT
            except Exception:
                ok = False
            if ok:
                ids[i] = name
            else:
                self.out.put(("hotkey_failed", f"{name} ({spec})"))
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312 and msg.wParam in ids:               # WM_HOTKEY
                self.out.put(("hotkey", ids[msg.wParam]))
