"""Réserves et espèces du jeu (noms FR, images), pour KillFarm Lite."""
import json
import re
import unicodedata

import config
import lang
import referentiel

# numéro de réserve dans la sauvegarde, nom FR, nom court, nom anglais (data/especes.json), logo (Image/Logo map)
RESERVES = (
    (0, "Réserve de chasse d'Hirschfelden", "Hirschfelden", "Hirschfelden Hunting Reserve", "Hirschfelden_hunting_reserve.png"),
    (1, "Layton Lake District", "Layton Lake", "Layton Lake District", "Layton_lake_district.png"),
    (2, "Parc national Taïga-Medved", "Taïga-Medved", "Medved-Taiga National Park", "Medved_taiga_national_park.png"),
    (3, "Savane de Vurhonga", "Vurhonga", "Vurhonga Savanna", "Vurhonga_savanna_reserve_icon.png"),
    (4, "Parque Fernando", "Parque Fernando", "Parque Fernando", "Fernando.png"),
    (6, "Réserve naturelle Vallée du Yukon", "Yukon", "Yukon Valley", "Yukon.png"),
    (8, "Réserve de chasse des Cuatro Colinas", "Cuatro Colinas", "Cuatro Colinas Game Reserve", "Cuatrocolinas.png"),
    (9, "Silver Ridge Peaks", "Silver Ridge", "Silver Ridge Peaks", "SilverRidgeLogo.png"),
    (10, "Parc national Te Awaroa", "Te Awaroa", "Te Awaroa National Park", "TeAwaroa.png"),
    (11, "Rancho del Arroyo", "Rancho del Arroyo", "Rancho del Arroyo", "Rancho.png"),
    (12, "Réserve naturelle de Mississippi Acres", "Mississippi", "Mississippi Acres Preserve", "Mississippi.png"),
    (13, "Côte de Revontuli", "Revontuli", "Revontuli Coast", "Revontuli.png"),
    (14, "New England Mountains", "New England", "New England Mountains", "NewEngland.png"),
    (16, "Côte d'Émeraude, Australie", "Côte d'Émeraude", "Emerald Coast", "Emerald_Coast.png"),
    (17, "Sundarpatan", "Sundarpatan", "Sundarpatan", "Sundarpatan.png"),
    (18, "Salzwiesen Park", "Salzwiesen", "Salzwiesen Park", "SalzwiesenPark.png"),
    (19, "Askiy Ridge", "Askiy Ridge", "Askiy Ridge Hunting Preserve", "AskiyRidge.png"),
    (20, "Tòrr nan Sithean (Écosse)", "Tòrr nan Sithean", "Tòrr nan Sithean", "Scotland.png"),
    (21, "Intisuyu (Pérou)", "Intisuyu", "Intisuyu", "Peru.png"),
)
BY_RID = {r[0]: r for r in RESERVES if r[0] is not None}
BY_EN = {r[3]: r for r in RESERVES}

try:
    _ANIMAL_FILES = json.loads(config.data_path("animal_images.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    _ANIMAL_FILES = {}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def fr_name(sp):
    """Nom français (celui enregistré dans farms.json)."""
    return sp.get("fr") or sp["en"]


EN_FIX = {"Monitoban Elk": "Manitoban Elk", "Javen Rusa": "Javan Rusa"}      # fautes du nom interne du jeu


def name(sp):
    """Nom de la bête dans la langue de l'appli."""
    if lang.LANG == "en":
        return EN_FIX.get(sp["en"], sp["en"])
    return fr_name(sp)


# Anciens noms / doublons du jeu -> fiche unique (un farm créé sous l'ancien nom compte toujours)
CANON = {"Mountain Lion": "Puma", "Turkey": "Merriam Turkey", "Wild Hog": "Feral Pig",
         "Wapiti du Manitoba": "Monitoban Elk", "Manitoban Elk": "Monitoban Elk", "Javan Rusa": "Javen Rusa"}


def canon(en):
    return CANON.get(en, en)


try:   # espèces de chaque réserve, tirées des fichiers de population du jeu (la source la plus sûre)
    _BY_RESERVE = json.loads(config.data_path("reserves_especes.json").read_text(encoding="utf-8"))["reserves"]
except (OSError, ValueError, KeyError):
    _BY_RESERVE = {}


def species_list(reserve_en=None):
    """Espèces (fiches de data/especes.json), triées par nom FR ; filtrées par réserve si donnée."""
    r = BY_EN.get(reserve_en)
    names = _BY_RESERVE.get(str(r[0])) if r and r[0] is not None else None
    if not reserve_en:
        out = list(referentiel.SPECIES)
    elif names:
        out = [sp for sp in referentiel.SPECIES if sp["en"] in names]
    else:
        out = [sp for sp in referentiel.SPECIES if reserve_en in (sp.get("reserves") or {})]
    return sorted(out, key=lambda sp: norm(name(sp)))


def species_by_en(en):
    en = canon(en)
    return next((sp for sp in referentiel.SPECIES if sp["en"] == en), None)


def animal_image(en):
    """Chemin de l'image de la bête (Image/logo animal), ou None."""
    f = _ANIMAL_FILES.get(re.sub(r"[^a-z0-9]", "", (en or "").lower()))
    p = config.IMG_DIR / "logo animal" / (f or "Placeholder.png")
    return p if p.exists() else None


def reserve_logo(rid=None, en=None):
    r = BY_RID.get(rid) if rid is not None else BY_EN.get(en)
    p = config.IMG_DIR / "Logo map" / r[4] if r else None
    return p if p and p.exists() else None


SHORT_EN = {2: "Medved-Taiga", 16: "Emerald Coast"}       # noms courts anglais (sinon pareil qu'en français)


def reserve_label(rid):
    """Nom court de la réserve, dans la langue de l'appli (affichage)."""
    if lang.LANG == "en":
        if rid in SHORT_EN:
            return SHORT_EN[rid]
        r = BY_RID.get(rid)
        return r[2] if r else (f"Reserve #{rid}" if rid is not None else "")
    return reserve_short(rid)


def reserve_short(rid):
    r = BY_RID.get(rid)
    return r[2] if r else (f"Réserve n°{rid}" if rid is not None else "")


def badge(grade):
    files = ("badge_rien.png", "badge_bronze.png", "badge_argent.png", "badge_or.png", "badge_diamant.png",
             "badge_great_one.png")
    p = config.IMG_DIR / "Logo rang" / files[grade]
    return p if p.exists() else None
