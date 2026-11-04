"""LIEN avec l'appli complète Cotw_KillFarm : mêmes farms, mêmes chiffres dans les 2 applis.

Seulement quand KillFarm Lite est rangé dans le dossier de Cotw_KillFarm (sous-dossier « KillFarm_Lite »).
- Lite suit le PROFIL de Cotw_KillFarm utilisé en dernier : ses farms (Documents\\Cotw_KillFarm\\profils\\<id>\\
  memoire_farm.json) sont ceux de Lite, et Lite y écrit chaque changement (kill, grade, correction, nouveau farm,
  suppression). Dans Lite, les farms de ce profil sont gardés dans farms_profil_<id>.json.
- Au lancement (et toutes les 2 s si l'appli complète tourne en même temps), Lite relit les farms de l'appli complète :
  farm ajouté -> ajouté dans Lite ; chiffres changés -> repris ; farm supprimé -> supprimé.
- Première liaison : un farm présent des 2 côtés garde les chiffres du côté qui a le PLUS de kills. Avant, une copie
  de chaque fichier est faite (….avant-lien-lite) : rien ne peut être perdu.
Un farm dont la bête n'a pas de nom connu (« #12345 », nom tapé à la main) reste seulement dans l'appli complète.
"""
import json
import shutil
import time
from pathlib import Path

import config
import gamedata as gd
import storage

FIELDS = ("count", "go_total", "since_go", "grades")


def _documents():
    try:
        import save_locator
        return save_locator.documents_dir()
    except Exception:
        return Path.home() / "Documents"


class Lien:
    def __init__(self, full_dir):
        self.full = Path(full_dir)
        user = self.full if (self.full / "portable.txt").exists() else _documents() / "Cotw_KillFarm"     # dossier des données : NE PAS renommer
        self.profiles = user / "profils"
        self.pid, self.pname = self._last_profile()
        self.path = self.profiles / self.pid / "memoire_farm.json" if self.pid else None
        self._mtime = None
        self._names()

    # ------------------------------------------------------------------ profil, noms
    def _last_profile(self):
        best = (None, None, -1)
        try:
            for d in self.profiles.iterdir():
                m = d / "profil.json"
                if d.is_dir() and m.exists():
                    try:
                        meta = json.loads(m.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        meta = {}
                    t = float(meta.get("dernier_lancement") or 0)
                    if t > best[2]:
                        best = (d.name, meta.get("nom") or d.name, t)
        except OSError:
            pass
        return best[0], best[1]

    def _names(self):
        """Nom de la bête dans l'appli complète (clé de ses farms) <-> nom anglais (Lite)."""
        try:
            sp = json.loads((self.full / "data" / "especes.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            sp = []
        self.to_en, self.to_main = {}, {}
        for s in sp:
            nom = s.get("fr") or s["en"]
            en = gd.canon(s["en"])
            self.to_en[nom] = en
            self.to_en[s["en"]] = en
            self.to_main.setdefault(en, nom)
            if gd.canon(s["en"]) == s["en"]:              # le vrai nom passe avant un doublon (Mountain Lion…)
                self.to_main[en] = nom

    @property
    def ok(self):
        return self.path is not None

    def label(self):
        import lang
        return lang.T("lié à Kill_Farm (profil « {x} »)", x=self.pname)

    def lite_file(self):
        return config.USER_DIR / f"farms_profil_{self.pid}.json"

    # ------------------------------------------------------------------ fichier de l'appli complète
    def _read(self):
        d = storage.read_json(self.path, {}) if self.path.exists() else {}
        d = d if isinstance(d, dict) else {}
        d.setdefault("version", 2)
        d.setdefault("farms", {})
        d.setdefault("order", [k for k in d["farms"]])
        return d

    def _write(self, d):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        storage.write_json(self.path, d)
        try:
            self._mtime = self.path.stat().st_mtime
        except OSError:
            pass

    def changed_outside(self):
        """L'appli complète a écrit ses farms depuis notre dernière lecture / écriture ?"""
        try:
            return self.path.stat().st_mtime != self._mtime
        except OSError:
            return False

    @staticmethod
    def _vals(mf):
        g = mf.get("grades")
        g = [int(x) for x in g][:6] if isinstance(g, list) and len(g) == 6 else None
        return {"count": int(mf.get("count", 0) or 0), "go_total": int(mf.get("go_total", 0) or 0),
                "since_go": int(mf.get("since_go", 0) or 0), "grades": g}

    @staticmethod
    def _lite_vals(f):
        return {"count": f["count"], "go_total": f["go_total"], "since_go": f["since_go"], "grades": list(f["grades"])}

    def _split(self, mk):
        if "@" in mk:
            sp, rid = mk.rsplit("@", 1)
            if rid.isdigit():
                return sp, int(rid)
        return mk, None

    def main_key(self, f):
        nom = self.to_main.get(gd.canon(f["species_en"]))
        if not nom:
            return None
        return nom if f.get("rid") is None else f"{nom}@{f['rid']}"

    # ------------------------------------------------------------------ copie de sécurité (1re liaison)
    def backup_once(self, lite_src):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for p in (self.path, lite_src):
            try:
                if p and p.exists():
                    b = p.with_name(f"{p.name}.avant-lien-lite-{stamp}")
                    if not any(x.name.startswith(f"{p.name}.avant-lien-lite") for x in p.parent.iterdir()):
                        shutil.copy2(p, b)
            except OSError:
                pass

    # ------------------------------------------------------------------ appli complète -> Lite
    def pull(self, farms):
        """Relit les farms de l'appli complète et met Lite à jour. -> True si Lite a changé."""
        d = self._read()
        try:
            self._mtime = self.path.stat().st_mtime
        except OSError:
            self._mtime = None
        changed, push_back = False, False
        linked = {f.get("lien"): k for k, f in farms.farms.items() if f.get("lien")}
        for mk in list(d["order"]):
            mf = d["farms"].get(mk)
            if not isinstance(mf, dict):
                continue
            nom, rid = self._split(mk)
            en = self.to_en.get(nom)
            if not en:
                continue                                    # bête sans nom connu : reste dans l'appli complète
            mv = self._vals(mf)
            lk = linked.get(mk) or next((k for k, f in farms.farms.items() if not f.get("lien")
                                         and gd.canon(f["species_en"]) == en and f.get("rid") == rid), None)
            if lk is None:                                  # farm créé dans l'appli complète : on l'ajoute
                sp = gd.species_by_en(en)
                key = farms.create(en, gd.fr_name(sp) if sp else en, rid,
                                   gd.reserve_short(rid) if rid is not None else "Toutes les réserves",
                                   count=mv["count"], since_go=mv["since_go"], go_total=mv["go_total"],
                                   grades=mv["grades"] or [0] * 6, last_go=self._last_go(mf), save=False,
                                   front=False)
                farms.farms[key].update({"lien": mk, "lien_vu": mv})
                changed = True
                continue
            f = farms.farms[lk]
            seen = f.get("lien_vu")
            if seen is None:                                # 1re liaison : le côté qui a le plus de kills gagne
                if f["count"] > mv["count"]:
                    push_back = True
                else:
                    self._apply(f, mv, mf)
                f["lien"] = mk
                f["lien_vu"] = self._lite_vals(f)
                changed = True
            elif not self._same(mv, seen):                  # changé dans l'appli complète : Lite reprend ses chiffres
                self._apply(f, mv, mf)
                f["lien_vu"] = self._lite_vals(f)
                changed = True
        for k, f in list(farms.farms.items()):              # supprimé dans l'appli complète
            if f.get("lien") and f["lien"] not in d["farms"] and f.get("lien_vu") is not None:
                farms.delete(k, save=False, propagate=False)
                changed = True
        if any(not f.get("lien") for f in farms.farms.values()):
            push_back = True                                # farms Lite pas encore dans l'appli complète
        if changed:
            farms.save(propagate=False)
        if push_back:
            self.push(farms)
            changed = True
        return changed

    @staticmethod
    def _same(mv, seen):
        return all(mv[k] == seen.get(k) for k in ("count", "go_total", "since_go")) and (
            mv["grades"] is None or mv["grades"] == seen.get("grades"))

    def _apply(self, f, mv, mf):
        f["count"], f["go_total"], f["since_go"] = mv["count"], mv["go_total"], mv["since_go"]
        if mv["grades"]:
            f["grades"] = list(mv["grades"])
        lg = self._last_go(mf)
        if lg:
            f["last_go"] = lg
        f["total"] = max(f.get("total", 0), f["count"])

    @staticmethod
    def _last_go(mf):
        if mf.get("last_go"):
            return int(mf["last_go"])
        log = mf.get("go_log") or []
        try:
            return int(log[-1]["apres"]) if log else None
        except (KeyError, TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ Lite -> appli complète
    def push(self, farms, deleted=()):
        """Écrit les farms de Lite dans l'appli complète (création, chiffres, grades, dernier GO, suppression)."""
        d = self._read()
        for mk in deleted:
            if mk in d["farms"]:
                del d["farms"][mk]
                d["order"] = [k for k in d["order"] if k != mk]
        for k in farms.order:
            f = farms.farms[k]
            mk = f.get("lien") or self.main_key(f)
            if not mk:
                continue
            mf = d["farms"].get(mk)
            if mf is None:
                mf = d["farms"][mk] = {"count": 0, "go_total": 0, "since_go": 0, "closed": False, "recent": [],
                                       "chosen": True}
                d["order"].append(mk)
            old_go = int(mf.get("go_total", 0) or 0)
            mf["count"], mf["go_total"], mf["since_go"] = f["count"], f["go_total"], f["since_go"]
            mf["grades"] = list(f["grades"])
            mf["chosen"] = True
            log = mf.setdefault("go_log", [])
            if f["go_total"] > old_go:                      # Great One compté dans Lite : il apparaît dans l'historique
                for i in range(f["go_total"] - old_go):
                    last = i == f["go_total"] - old_go - 1
                    log.append({"apres": f.get("last_go") if last else None, "kill_n": f["count"],
                                "date": time.strftime("%Y-%m-%d"), "heure": time.strftime("%H:%M"),
                                "source": "KillFarm Lite"})
            elif f["go_total"] < old_go:                    # GO annulé dans Lite
                del log[max(0, len(log) - (old_go - f["go_total"])):]
            if f.get("last_go"):
                mf["last_go"] = f["last_go"]
            else:
                mf.pop("last_go", None)
            f["lien"] = mk
            f["lien_vu"] = self._lite_vals(f)
        self._write(d)
