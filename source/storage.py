"""Lecture / écriture JSON sûres pour les mémoires (écriture atomique + copie de secours si fichier corrompu)."""
import json
import os
import shutil
import time


def read_json(path, default):
    """Lit un JSON. Fichier absent -> default. Fichier corrompu -> copie « .corrompu-<heure> » puis default
    (on n'écrase donc jamais silencieusement une mémoire illisible)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return default
    try:
        return json.loads(text)
    except ValueError:
        try:
            shutil.copy2(path, path.with_name(f"{path.name}.corrompu-{int(time.time())}"))
        except OSError:
            pass
        return default


def write_json(path, data):
    """Écriture atomique : fichier temporaire puis remplacement (pas de mémoire à moitié écrite si le PC plante)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except OSError:                                    # antivirus / indexeur qui tient le fichier un instant
            time.sleep(0.1)
    os.replace(tmp, path)
