"""Compteur de kills du PROFIL joueur (thp_player_profile_adf > WeaponData[].TotalKills).

Chaque arme a son compteur de kills ; leur SOMME monte à chaque bête tuée, qu'elle soit ramassée ou non.
Comparée au nombre de bêtes RÉCOLTÉES (journal de chasse), la différence = bêtes tuées mais pas ramassées.
(tableau « inline » IA[...] : lu par adf.py)"""
import adf


def total_kills(path):
    arr = adf.Adf(adf.unpack_save(path)).read_member("WeaponData")
    ks = [int(w["TotalKills"]) for w in arr if isinstance(w, dict) and "TotalKills" in w]
    if not ks or any(k < 0 or k > 10_000_000 for k in ks):
        raise ValueError("compteurs de kills des armes incohérents (format de sauvegarde inattendu)")
    return sum(ks)
