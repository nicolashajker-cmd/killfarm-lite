"""Référentiel du jeu : espèces (classe, seuils de médaille), armes/munitions, et reconnaissance
AUTOMATIQUE des codes d'espèce de la sauvegarde.

Le code d'espèce stocké dans hunting_log_adf est le hachage Jenkins lookup3 de « animal_<clé>_name »
(vérifié sur chevreuil = animal_roedeer_name, loup ibérique = animal_iberianwolf_name, faisan =
animal_pheasant_name). On calcule donc les hachages de toutes les espèces connues : plus besoin de les
nommer à la main quand la clé est devinée (sinon l'ancien dialogue de nommage reste disponible).

Sources : n3m3sis.fr (PDF FR 08.2023 : noms, seuils argent/or/diamant, poids) et tableau diamant par
réserve (classe, niveau max, diamant) fourni par l'utilisateur.
"""
import json
import re
import zlib  # noqa: F401  (réservé : autres hachages éventuels)
import config
from config import DATA_DIR

_M = 0xFFFFFFFF
# Clés internes qui ne se déduisent pas du nom anglais (à compléter quand une espèce reste « inconnue »).
# (plusieurs écritures possibles : toutes sont essayées, une bête est reconnue dès que l'une correspond)
ALIASES = {"Ring-Necked Pheasant": ["pheasant", "ringneckpheasant"],
           "Puma": ["mountainlion", "cougar"],
           "Merriam Turkey": ["turkey", "merriamsturkey", "wildturkey"],
           "Feral Pig": ["wildhog", "feralhog", "wildpig", "pig"],
           "Monitoban Elk": ["manitobanelk", "manitobaelk", "wapitidumanitoba"],
           "Javen Rusa": ["javanrusa", "rusa", "rusadeer", "javanrusadeer"],
           "Whitetail Deer": ["whitetail", "whitetaileddeer"],
           "Grey Wolf": ["graywolf"], "Grey Fox": ["grayfox"],
           "Tahr": ["himalayantahr"],
           "Eastern Grey Kangaroo": ["easterngraykangaroo", "kangaroo", "greykangaroo"],
           "Bobwhite Quail": ["northernbobwhitequail", "northernbobwhite", "bobwhite"],
           "Sambar Deer": ["sambar"], "Wildebeest": ["bluewildebeest"],
           "Reindeer": ["mountainreindeer"], "Caribou": ["grantcaribou"],
           "Bighorn Sheep": ["rockymountainbighornsheep"],
           "Common Raccoon": ["raccoon"], "Eastern Cottontail Rabbit": ["cottontailrabbit", "easterncottontail"],
           "Northern Red Muntjac": ["muntjac", "indianmuntjac", "redmuntjac"],
           "Blue Sheep": ["bharal"], "Bengal Tiger": ["tiger"], "Wild Yak": ["yak"],
           "Snow Leopard": ["snowleopard"], "Tibetan Fox": ["tibetansandfox"],
           "North American Beaver": ["beaver"], "European Bison": ["wisent"],
           "Eurasian Teal": ["commonteal"], "Goldeneye": ["commongoldeneye"],
           "Saltwater Crocodile": ["crocodile"], "American Alligator": ["alligator"],
           "Black Caiman": ["caiman"], "South American Tapir": ["tapir"], "Greater Grison": ["grison"],
           "Western Mountain Coati": ["coati", "mountaincoati"], "Siberian Musk Deer": ["muskdeer"],
           "Southeastern Spanish Ibex": ["southeasternibex"], "Iberian Mouflon": ["mouflon"]}


def _rot(x, k):
    return ((x << k) | (x >> (32 - k))) & _M


def hashlittle(data, initval=0):
    """Jenkins lookup3 (hashlittle), le hachage de noms utilisé par les fichiers ADF d'Avalanche."""
    if isinstance(data, str):
        data = data.encode()
    n = len(data)
    a = b = c = (0xDEADBEEF + n + initval) & _M
    i = 0
    while n - i > 12:
        a = (a + int.from_bytes(data[i:i + 4], "little")) & _M
        b = (b + int.from_bytes(data[i + 4:i + 8], "little")) & _M
        c = (c + int.from_bytes(data[i + 8:i + 12], "little")) & _M
        a = (a - c) & _M; a ^= _rot(c, 4); c = (c + b) & _M
        b = (b - a) & _M; b ^= _rot(a, 6); a = (a + c) & _M
        c = (c - b) & _M; c ^= _rot(b, 8); b = (b + a) & _M
        a = (a - c) & _M; a ^= _rot(c, 16); c = (c + b) & _M
        b = (b - a) & _M; b ^= _rot(a, 19); a = (a + c) & _M
        c = (c - b) & _M; c ^= _rot(b, 4); b = (b + a) & _M
        i += 12
    rem = data[i:]
    if not rem:
        return c
    rem += b"\0" * (12 - len(rem))
    a = (a + int.from_bytes(rem[0:4], "little")) & _M
    b = (b + int.from_bytes(rem[4:8], "little")) & _M
    c = (c + int.from_bytes(rem[8:12], "little")) & _M
    c ^= b; c = (c - _rot(b, 14)) & _M
    a ^= c; a = (a - _rot(c, 11)) & _M
    b ^= a; b = (b - _rot(a, 25)) & _M
    c ^= b; c = (c - _rot(b, 16)) & _M
    a ^= c; a = (a - _rot(c, 4)) & _M
    b ^= a; b = (b - _rot(a, 14)) & _M
    c ^= b; c = (c - _rot(b, 24)) & _M
    return c


def _load(name):
    try:
        return json.loads(config.data_path(name).read_text(encoding="utf-8"))
    except Exception:
        return []


SPECIES = _load("especes.json")
WEAPONS = [w for w in _load("armes.json") + _load("armes_perso.json") if not str(w.get("categorie", "")).startswith("_")]   # armes_perso.json : tes ajouts (DLC récents), même format


def _letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def _learned():
    """Bêtes apprises (tu as dit à l'appli quelle bête c'était) : {code: nom anglais}."""
    try:
        return {int(k): v for k, v in json.loads((config.USER_DIR / "especes_apprises.json").read_text(encoding="utf-8")).items()}
    except Exception:
        return {}


def learn(h, en):
    """Retient : ce code de la sauvegarde = cette espèce (fichier especes_apprises.json, à côté des farms)."""
    sp = next((s for s in SPECIES if s["en"] == en), None)
    if sp is None:
        return
    d = _learned()
    d[int(h)] = en
    config.USER_DIR.mkdir(parents=True, exist_ok=True)
    (config.USER_DIR / "especes_apprises.json").write_text(json.dumps({str(k): v for k, v in d.items()}, ensure_ascii=False,
                                                                       indent=1), encoding="utf-8")
    _BY_HASH[int(h)] = sp


def _build_hash_table():
    last = {}
    for sp in SPECIES:
        last.setdefault(_letters(sp["en"].split()[-1]), []).append(sp)
    table = {}
    for sp in SPECIES:
        keys = {_letters(sp["en"])} | set(ALIASES.get(sp["en"], []))
        w = _letters(sp["en"].split()[-1])
        if len(last[w]) == 1:                      # dernier mot seulement s'il est unique (« pheasant »)
            keys.add(w)
        for k in keys:
            table.setdefault(hashlittle(f"animal_{k}_name"), sp)
    by_en = {sp["en"]: sp for sp in SPECIES}
    for h, en in _learned().items():
        if en in by_en:
            table[h] = by_en[en]
    return table


_BY_HASH = _build_hash_table()


def species_by_hash(h):
    """Code d'espèce de la sauvegarde -> fiche espèce, ou None si pas reconnu."""
    try:
        return _BY_HASH.get(int(h))
    except (TypeError, ValueError):
        return None


def info(sp, reserve=None):
    """Fiche compatible avec le HUD : {'nom', 'niveau' (= classe de l'animal), ...}."""
    r = (sp.get("reserves") or {}).get(reserve) if reserve else None
    classe = (r or {}).get("classe") or sp.get("classe")
    return {"nom": sp.get("fr") or sp["en"], "en": sp["en"], "niveau": classe if classe else "?",
            "niveau_max": (r or {}).get("niveau_max"), "diamant": (r or {}).get("diamant")}


def medal(sp, score, reserve=None):
    """Médaille théorique d'après le score de trophée (indicatif : la sauvegarde stocke déjà la médaille)."""
    p = sp.get("pdf_2023") or {}
    r = (sp.get("reserves") or {}).get(reserve) if reserve else None
    dia = (r or {}).get("diamant") or p.get("diamant") or next(
        (v["diamant"] for v in sp.get("reserves", {}).values() if v.get("diamant")), None)
    if dia and score >= dia:
        return "Diamant"
    if p.get("or_") and score >= p["or_"]:
        return "Or"
    if p.get("argent") and score >= p["argent"]:
        return "Argent"
    return "Bronze"


def ammo_verdict(animal_class, cmin, cmax):
    """Le jeu contrôle la MUNITION : sa plage de classes doit contenir la classe de l'animal."""
    if animal_class in (None, "?"):
        return "? classe inconnue"
    if animal_class < cmin:
        return f"✖ Munition trop forte (cl.{cmin}-{cmax} > cl.{animal_class})"
    if animal_class > cmax:
        return f"✖ Munition trop faible (cl.{cmin}-{cmax} < cl.{animal_class})"
    return "✔ Éthique"


_SYN = (("grenaille", ("plombs", "plomb", "birdshot", "shot")), ("chevrotine", ("buckshot",)), ("balle", ("slug", "balles")),
        ("", ("cartouches", "cartouche", "pointe polymere", "pointe plate", "pointe creuse", "tete molle", "polymer tip",
              "soft point", "full metal jacket", "ammo", "munitions")))


def _norm(s):
    """Nom de munition -> forme comparable : sans accents ni casse, synonymes FR/EN unifiés (plomb = grenaille...)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\(cl\.?[^)]*\)", " ", t)                  # « (cl.4-8) » ajouté par le HUD
    for canon, words in _SYN:
        for w in words:
            t = re.sub(r"\b%s\b" % re.escape(w), canon, t)
    toks = [x for x in re.split(r"[^a-z0-9]+", t) if x and x not in ("a", "de", "du", "au", "en", "la", "le", "les", "des")]
    return "".join(sorted(toks))                           # l'ordre des mots ne compte pas (« 16 GA plomb » = « plomb 16 GA »)


def ammo_range(name):
    """Nom de munition saisi (ex. « .243 », « 12 GA Balle ») -> (classe_min, classe_max) d'après data/armes.json,
    ou None. Plusieurs armes pour la même munition : on prend l'union des plages."""
    n = _norm(name)
    if not n:
        return None
    exact, loose = [], []
    for w in WEAPONS:
        for m in w.get("munitions", []):
            k = _norm(m["nom"])
            (exact if k == n else loose if (n in k or k in n) else []).append((m["classe_min"], m["classe_max"]))
    hits = exact or loose
    return (min(h[0] for h in hits), max(h[1] for h in hits)) if hits else None


_LEVELS = (_load("niveaux_poids.json") or {}).get("especes", {}) if isinstance(_load("niveaux_poids.json"), dict) else {}


def level_from_weight(en, weight, great=False):
    """NIVEAU de la bête (difficulté 1..9 ; Great One = 10), d'après son poids et les tranches de data/niveaux_poids.json.
    À ne pas confondre avec la CLASSE (1..9 : munition requise). -> int, ou None si inconnu."""
    if great:
        return 10
    tranches = _LEVELS.get(en)
    if not tranches or weight is None:
        return None
    try:
        w = float(weight)
    except (TypeError, ValueError):
        return None
    for i, (lo, hi) in enumerate(tranches):
        if w < hi:
            return i + 1
    return len(tranches)
