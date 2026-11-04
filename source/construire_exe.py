"""Construit « KillFarm Lite.exe » en UN SEUL fichier (données, images et logo dedans) : double-clic sur
construire_exe.bat (il faut Internet la 1re fois, pour installer PyInstaller).

Résultat, à côté de ce dossier (sur ton Bureau) :
- KillFarm_Lite_v<version>.zip  ->  à partager : KillFarm Lite/ -> KillFarm Lite.exe + LISEZMOI.txt + README.txt
- le dossier « KillFarm Lite v<version> »  ->  le même contenu dézippé, pour l'essayer toi-même
Aucun Python nécessaire pour les joueurs. Aucune donnée perso dans le zip (elles sont dans Documents\\KillFarm_Lite)."""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parent
SKIP_IMAGES = {"Europeanhare_frame_wip.png", "Background.png"}      # images inutilisées : pas dans le .exe


def run(*cmd, cwd=APP):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.check_call([str(c) for c in cmd], cwd=str(cwd))


def main():
    import config
    work = APP.parent / "_build_killfarm_lite"
    shutil.rmtree(work, ignore_errors=True)
    images = work / "Image"
    shutil.copytree(APP / "Image", images, ignore=lambda d, names: [n for n in names if n in SKIP_IMAGES])
    run(sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "pyinstaller", "pillow")
    sep = os.pathsep
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed", "--noupx",
        "--name", "KillFarm Lite", "--icon", APP / "Image" / "logo.ico",
        "--add-data", f"{APP / 'data'}{sep}data", "--add-data", f"{images}{sep}Image",
        "--distpath", work / "dist", "--workpath", work / "build", "--specpath", work, APP / "killfarm_lite.py")
    exe = work / "dist" / "KillFarm Lite.exe"
    def txt(name):                                  # fin de ligne Windows + en-tête UTF-8 (accents OK dans le Bloc-notes)
        return (APP / name).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8-sig")
    docs = {"LISEZMOI.txt": txt("LISEZMOI.txt"), "README.txt": txt("README.txt")}
    z = APP.parent / f"KillFarm_Lite_v{config.VERSION}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe, "KillFarm Lite/KillFarm Lite.exe")
        for name, data in docs.items():
            zf.writestr(f"KillFarm Lite/{name}", data)
    test = APP.parent / f"KillFarm Lite v{config.VERSION}"
    shutil.rmtree(test, ignore_errors=True)
    test.mkdir()
    shutil.copy2(exe, test / "KillFarm Lite.exe")
    for name, data in docs.items():
        (test / name).write_bytes(data)
    shutil.rmtree(work, ignore_errors=True)
    print(f"\nTERMINÉ. Sur ton Bureau :")
    print(f"  {z.name}  ({z.stat().st_size / 1e6:.0f} Mo)  -> à partager (KillFarm Lite.exe + LISEZMOI + README)")
    print(f"  dossier « {test.name} »  -> double-clic sur KillFarm Lite.exe pour l'essayer")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\nERREUR pendant la construction : {exc}\n(Vérifie ta connexion Internet et relance.)")
        sys.exit(1)
