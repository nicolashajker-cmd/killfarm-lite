"""Farms de KillFarm Lite (Documents\\KillFarm_Lite\\farms.json).

Un farm = une espèce, dans une réserve (ou « toutes les réserves »). Pour chaque farm :
count (kills du farm), since_go (kills depuis le dernier Great One), go_total (Great Ones obtenus),
last_go (kills qu'il a fallu pour le DERNIER Great One : fixe jusqu'au prochain), total (TOUS tes kills de cette espèce
dans cette réserve, y compris avant le farm : tapé au départ, puis +1 à chaque kill),
grades [sans médaille, bronze, argent, or, diamant, Great One], log (derniers kills, pour « Annuler »).
Tout est modifiable à la main."""
import time

import config
import storage

GRADES = ("Sans médaille", "Bronze", "Argent", "Or", "Diamant", "Great One")
GO = 5
LOG_MAX = 200


def journal_to_grade(raw):
    """Médaille du journal de chasse du jeu (0 Diamant, 1 Or, 2 Argent, 3 Bronze, 4 aucune) -> 0 aucune .. 4 Diamant."""
    try:
        raw = int(raw)
    except (TypeError, ValueError):
        return 0
    if raw == 5:                                            # 5 = Great One (même code que ScoreRank du jeu)
        return GO
    return 4 - raw if 0 <= raw <= 4 else 0


def make_key(species_en, rid):
    return species_en if rid is None else f"{species_en}@{rid}"


class Farms:
    def __init__(self, lien=None):
        """lien : appli complète Cotw_KillFarm (lien.Lien) -> mêmes farms, mêmes chiffres ; None = Lite tout seul."""
        self.lien = lien if lien is not None and lien.ok else None
        self._deleted = []
        self.path = config.USER_DIR / "farms.json"
        if self.lien:
            own = self.lien.lite_file()
            if not own.exists() and self.path.exists() and not any(config.USER_DIR.glob("farms_profil_*.json")):
                self.lien.backup_once(self.path)            # 1re liaison : tes farms Lite partent avec ce profil
                config.USER_DIR.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(self.path, own)
            elif not own.exists():
                self.lien.backup_once(None)
            self.path = own
        data = storage.read_json(self.path, {})
        data = data if isinstance(data, dict) else {}
        self.farms = data.get("farms") or {}
        self.order = [k for k in data.get("order", []) if k in self.farms]
        self.order += [k for k in self.farms if k not in self.order]
        self.active = data.get("active") if data.get("active") in self.farms else (self.order[0] if self.order else None)
        for f in self.farms.values():
            f.setdefault("grades", [0] * 6)
            f.setdefault("log", [])
            for k in ("count", "since_go", "go_total"):
                f.setdefault(k, 0)
            f.setdefault("last_go", None)
            f.setdefault("total", f["count"])

    def save(self, propagate=True):
        config.USER_DIR.mkdir(parents=True, exist_ok=True)
        if propagate and self.lien:                         # chaque changement part aussi dans l'appli complète
            try:
                self.lien.push(self, deleted=self._deleted)
                self._deleted = []
            except Exception:
                pass
        storage.write_json(self.path, {"version": 1, "active": self.active, "order": self.order, "farms": self.farms})

    def sync(self):
        """Relit les farms de l'appli complète (liée). -> True si quelque chose a changé."""
        if not self.lien:
            return False
        try:
            return self.lien.pull(self)
        except Exception:
            return False

    # ----- lecture
    def get(self, key=None):
        key = key or self.active
        return self.farms.get(key) if key else None

    def match(self, species_en, rid):
        """Farms qui comptent cette bête : même espèce, et même réserve (ou farm « toutes réserves »,
        ou réserve de la bête inconnue)."""
        import gamedata
        out = []
        for k in self.order:
            f = self.farms[k]
            if gamedata.canon(f["species_en"]) != gamedata.canon(species_en):
                continue
            if f.get("rid") is None or rid is None or f["rid"] == rid:
                out.append(k)
        return out

    # ----- création / suppression
    def create(self, species_en, name, rid, reserve, count=0, since_go=None, go_total=0, grades=None, last_go=None,
               total=None, save=True, front=True):
        key = make_key(species_en, rid)
        old = next((k for k in self.match(species_en, rid) if self.farms[k].get("rid") == rid), None)
        key = old or key                                     # même bête sous un ancien nom : on rouvre ce farm
        if key in self.farms:                               # déjà là : on le rouvre
            if front:
                self.active = key
                self.save()
            return key
        self.farms[key] = {"species_en": species_en, "name": name, "rid": rid, "reserve": reserve,
                           "count": int(count), "since_go": int(count if since_go is None else since_go),
                           "go_total": int(go_total), "grades": list(grades or [0] * 6), "log": [],
                           "last_go": int(last_go) if last_go else None,
                           "total": max(int(total or 0), int(count)),
                           "created": time.time()}
        if front:
            self.order.insert(0, key)
            self.active = key
        else:                                               # farm venu de l'appli complète : à la fin de la liste
            self.order.append(key)
            self.active = self.active or key
        if save:
            self.save()
        return key

    def delete(self, key, save=True, propagate=True):
        if key in self.farms:
            if propagate and self.farms[key].get("lien"):
                self._deleted.append(self.farms[key]["lien"])
            del self.farms[key]
            self.order = [k for k in self.order if k != key]
            if self.active == key:
                self.active = self.order[0] if self.order else None
            if save:
                self.save()

    def set_active(self, key):
        if key in self.farms:
            self.active = key
            self.save()

    # ----- kills
    def add_kill(self, key, grade, ts=None, manual=False):
        f = self.farms[key]
        f["count"] += 1
        f["total"] = f.get("total", 0) + 1
        if grade is not None:
            f["grades"][grade] += 1
        if grade == GO:
            f["go_total"] += 1
            f["log"].append({"t": ts or time.time(), "g": grade, "since_before": f["since_go"], "m": manual,
                             "last_go_before": f.get("last_go")})
            f["last_go"] = f["since_go"] + 1                 # ce Great One est tombé au (since_go + 1)e kill
            f["since_go"] = 0
        else:
            f["since_go"] += 1
            f["log"].append({"t": ts or time.time(), "g": grade, "m": manual})
        f["log"] = f["log"][-LOG_MAX:]
        self.save()

    def mark_go(self, key):
        """« Le dernier kill était un Great One » (pas reconnu tout seul) : +1 Great One, le compteur depuis le dernier
        GO repart de 0, et « Dernier GO tombé en » = ce compteur. Annulable avec « Annuler »."""
        f = self.farms[key]
        f["log"].append({"t": time.time(), "mark_go": True, "since_before": f["since_go"],
                         "last_go_before": f.get("last_go")})
        f["log"] = f["log"][-LOG_MAX:]
        f["go_total"] += 1
        f["grades"][GO] += 1
        f["last_go"] = f["since_go"] or None
        f["since_go"] = 0
        self.save()

    def undo(self, key):
        """Retire le dernier kill du farm (ou le dernier « c'était un Great One »). -> True si quelque chose a changé."""
        f = self.farms.get(key)
        if not f or not f["log"]:
            return False
        last = f["log"].pop()
        if last.get("mark_go"):
            f["go_total"] = max(0, f["go_total"] - 1)
            f["grades"][GO] = max(0, f["grades"][GO] - 1)
            f["since_go"] = last.get("since_before", 0)
            f["last_go"] = last.get("last_go_before")
            self.save()
            return "go"
        f["count"] = max(0, f["count"] - 1)
        f["total"] = max(0, f.get("total", 0) - 1)
        g = last.get("g")
        if g is not None:
            f["grades"][g] = max(0, f["grades"][g] - 1)
        if g == GO:
            f["go_total"] = max(0, f["go_total"] - 1)
            f["since_go"] = last.get("since_before", 0)
            f["last_go"] = last.get("last_go_before")
        else:
            f["since_go"] = max(0, f["since_go"] - 1)
        self.save()
        return True

    def remove_one(self, key):
        """−1 à la main : retire un kill sans grade (corrige un kill en trop)."""
        f = self.farms[key]
        f["count"] = max(0, f["count"] - 1)
        f["since_go"] = max(0, f["since_go"] - 1)
        f["total"] = max(0, f.get("total", 0) - 1)
        self.save()

    def add_grade(self, key, g, delta):
        f = self.farms[key]
        f["grades"][g] = max(0, f["grades"][g] + delta)
        if g == GO:
            f["go_total"] = max(0, f["go_total"] + delta)
        self.save()

    def set_numbers(self, key, count, since_go, go_total, grades, last_go=None, total=None):
        f = self.farms[key]
        f["count"], f["since_go"], f["go_total"] = int(count), int(since_go), int(go_total)
        f["last_go"] = int(last_go) if last_go else None
        if total is not None:
            f["total"] = int(total)
        f["grades"] = [int(x) for x in grades]
        self.save()
