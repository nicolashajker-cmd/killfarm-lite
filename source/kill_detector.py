"""Détecte les bêtes RÉCOLTÉES : une récolte = une nouvelle entrée dans le journal de chasse
(hunting_log_adf, liste des 20 dernières récoltes). Rien d'autre ne l'alimente.

Puis lit les détails de tir (distance, organes, arme, munition...) dans trophy_lodges_adf > LastHarvest,
qui ne contient que la DERNIÈRE bête : on la rattache à la bonne ligne par score + heure. Si elle n'apparaît
pas dans le délai (trophy_wait_seconds), la récolte est comptée quand même, sans détails de tir."""
import threading
import time
from pathlib import Path

import hunting_log
import last_harvest
import profile_stats
import save_locator as sl


class KillDetector(threading.Thread):
    def __init__(self, cfg, saves_dir, out_queue):
        super().__init__(daemon=True)
        self.cfg, self.saves, self.out = cfg, Path(saves_dir), out_queue
        self.log_path = self.saves / "hunting_log_adf"
        self.trophy_path = self.saves / "trophy_lodges_adf"
        self.profile_path = self.saves / "thp_player_profile_adf"
        self._prof_stat, self._prof_total, self._prof_err = None, None, None
        self.trophy_wait = float(cfg.get("trophy_wait_seconds", 20))
        self.seen = set()
        self.pending = []                                  # [(entry, heure de détection)]
        self._lh_stat, self._lh = None, None
        self.map_id = None
        self._halt = threading.Event()

    def stop(self):
        self._halt.set()

    def _stat(self):
        try:
            st = self.log_path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _check(self, baseline=False):
        try:
            entries = hunting_log.read_harvests(self.log_path)
        except Exception:
            return False                                   # fichier en cours d'écriture : on réessaie
        new = [e for e in entries if hunting_log.key(e) not in self.seen]
        self.seen |= {hunting_log.key(e) for e in entries}
        if not baseline:
            now = time.time()
            self.pending += [(e, now) for e in sorted(new, key=lambda e: e["Timestamp"])]
            self._flush_pending()
        return True

    def _last_harvest(self):
        """LastHarvest du fichier trophées (relu seulement s'il a changé) ; None si illisible."""
        try:
            st = self.trophy_path.stat()
            stat = (st.st_mtime_ns, st.st_size)
        except OSError:
            return None
        if stat != self._lh_stat:
            try:
                self._lh = last_harvest.read_last(self.trophy_path)
            except Exception:
                return self._lh if self._lh_stat is not None else None   # en cours d'écriture : on réessaie
            self._lh_stat = stat
        return self._lh

    def _flush_pending(self):
        """Émet les récoltes dont on a trouvé les détails de tir, ou dont le délai est dépassé."""
        if not self.pending:
            return
        lh, now, keep = self._last_harvest(), time.time(), []
        for e, t0 in self.pending:
            if lh and last_harvest.matches(e, lh):
                self.out.put({"type": "kill", "map_id": self.map_id, "entry": e,
                              "last": last_harvest.digest(lh)})
            elif now - t0 >= self.trophy_wait:
                self.out.put({"type": "kill", "map_id": self.map_id, "entry": e, "last": None})
            else:
                keep.append((e, t0))
        self.pending = keep

    def _check_profile(self, baseline=False):
        """Somme des kills des armes (profil joueur) : émise au démarrage (baseline) puis à chaque changement.
        Sert au compteur « bêtes tuées non ramassées » (kills du profil - bêtes récoltées)."""
        try:
            st = self.profile_path.stat()
            stat = (st.st_mtime_ns, st.st_size)
        except OSError:
            return
        if stat == self._prof_stat:
            return
        try:
            total = profile_stats.total_kills(self.profile_path)
        except Exception as exc:                           # écriture en cours, ou format inattendu
            msg = f"{type(exc).__name__}: {exc}"[:160]
            if msg != self._prof_err:                      # une seule alerte par message (pas de spam)
                self._prof_err = msg
                self.out.put({"type": "kills_error", "text": msg, "baseline": baseline})
            return
        self._prof_stat, self._prof_err = stat, None
        if baseline or total != self._prof_total:
            self._prof_total = total
            self.out.put({"type": "kills_total", "total": total, "baseline": baseline})

    def _update_map(self, snap, changed):
        pops = sorted((snap[n][0], n) for n in changed if n.startswith("animal_population_"))
        if pops:
            mid = sl.map_id_from_name(pops[-1][1])
            if mid != self.map_id:
                self.map_id = mid
                self.out.put({"type": "map", "map_id": mid})

    def run(self):
        self.map_id = sl.latest_map_id(self.saves)
        if self.map_id is not None:
            self.out.put({"type": "map", "map_id": self.map_id})
        for _ in range(20):                                # baseline : harvests déjà présentes
            if self._check(baseline=True) or self._halt.wait(0.5):
                break
        for _ in range(6):                                 # baseline des kills du profil (réessaie si écriture en cours)
            self._check_profile(baseline=True)
            if self._prof_total is not None or self._halt.wait(0.5):
                break
        last_stat, snap = self._stat(), sl.snapshot(self.saves)
        pending, last_change, tries = False, 0.0, 0
        poll, settle = float(self.cfg["poll_seconds"]), float(self.cfg["settle_seconds"])
        while not self._halt.wait(poll):
            now = time.time()
            st = self._stat()
            if st != last_stat:
                last_stat, pending, last_change, tries = st, True, now, 0
            new_snap = sl.snapshot(self.saves)
            self._update_map(new_snap, [n for n, v in new_snap.items() if snap.get(n) != v])
            snap = new_snap
            if self.pending:
                self._flush_pending()
            self._check_profile()
            if pending and now - last_change >= settle:
                tries += 1
                if self._check() or tries > 20:
                    pending = False
