"""Prépare le zip à partager (version Python) : dans le zip, juste
    KillFarm Lite/  ->  KillFarm Lite.bat  +  LISEZMOI.txt  +  fichiers/ (l'appli)
Double-clic sur partager.bat. Résultat à côté de ce dossier : KillFarm_Lite_v<version>.zip"""
import zipfile
from pathlib import Path

import config

APP = Path(__file__).resolve().parent
SKIP_FILES = {"partager.py", "partager.bat", "construire_exe.py", "construire_exe.bat", "KillFarm_Lite.bat",
              "LISEZMOI.txt", "portable.txt", "Europeanhare_frame_wip.png", "Background.png"}


def keep(p):
    return (p.is_file() and p.name not in SKIP_FILES and "__pycache__" not in p.parts
            and p.suffix not in (".pyc", ".tmp", ".log") and not p.name.startswith("."))


def main():
    z = APP.parent / f"KillFarm_Lite_v{config.VERSION}.zip"
    root = Path("KillFarm Lite")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(APP / "KillFarm_Lite.bat", root / "KillFarm Lite.bat")
        zf.write(APP / "LISEZMOI.txt", root / "LISEZMOI.txt")
        for p in sorted(APP.rglob("*")):
            if keep(p):
                zf.write(p, root / "fichiers" / p.relative_to(APP))
    print(f"Prêt : {z}")
    return z


if __name__ == "__main__":
    main()
