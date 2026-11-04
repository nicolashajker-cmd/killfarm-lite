"""Dernier prélèvement : trophy_lodges_adf > TrophyAnimals.LastHarvest.

Le jeu n'y garde QUE la dernière bête récoltée (écrasée à chaque récolte) : il faut la lire juste après
la récolte. On la relie à la ligne du journal de chasse par le score et l'heure.
Contenu (vérifié sur une vraie sauvegarde) : poids, sexe, réserve, position, et pour CHAQUE tir :
distance, organes touchés, part de dégâts, hash d'arme / de munition / de lunette, catégorie d'arme."""
import adf


def read_last(path):
    """-> dict brut du LastHarvest (lève une exception si le fichier est en cours d'écriture)."""
    return adf.Adf(adf.unpack_save(path)).read_member("TrophyAnimals", "LastHarvest")


def matches(entry, lh, tol_s=180):
    """Ce LastHarvest est-il bien la bête de cette ligne du journal ? (score identique + heure proche)"""
    try:
        return (abs(int(lh["HarvestedAt"]) - int(entry["Timestamp"])) <= tol_s
                and abs(float(lh["TrophyScore"]) - float(entry["Score"])) < 0.05)
    except (KeyError, TypeError, ValueError):
        return False


def digest(lh):
    """Version compacte et sérialisable (hashs en texte, comme species_hash dans l'historique)."""
    shots = []
    for s in lh.get("ProjectileHitInfo") or []:
        shots.append({
            "dist": round(float(s["ShotDistance"]), 1),
            "dmg": round(float(s["ShotDamageFraction"]), 3),
            "weapon": str(s["WeaponHash"]), "ammo": str(s["AmmoHash"]), "scope": str(s["ScopeHash"]),
            "cat": int(s["WeaponCategory"]),
            "organs": [str(o) for o in s.get("OrgansHit") or []],
        })
    try:
        flags = int((lh.get("FeatureModifiers") or {}).get("Flags", 0))
    except (TypeError, ValueError, AttributeError):
        flags = 0
    # GRAND ANIMAL, lu dans la sauvegarde (vérifié sur 4 Grands animaux réels) : ScoreRank = 5 et FeatureModifiers.Flags = 1
    feat = 0
    for f in lh.get("Features") or []:                     # marqueur aussi possible sur les bois / cornes
        try:
            feat |= int(((f.get("ModelVariationID") or {}).get("FeatureModifiers") or {}).get("Flags", 0))
        except (TypeError, ValueError, AttributeError):
            pass
    great = lh.get("ScoreRank") == 5 or bool(flags & 1) or bool(feat & 1)
    return {"weight": round(float(lh["Weight"]), 1), "male": bool(lh["IsMale"]),
            "reserve": int(lh["HarvestReserve"]), "shots": shots,
            "rank": int(lh["ScoreRank"]) if "ScoreRank" in lh else None,   # rang du jeu : 0 Diamant .. 3 Bronze, 5 = Grand animal
            "flags": flags, "feat_flags": feat, "variation": lh.get("VariationIndex"),
            "difficulty": lh.get("Difficulty"),
            "great": great}
