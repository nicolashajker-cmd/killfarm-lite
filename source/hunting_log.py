"""Journal de chasse : liste des 20 dernières récoltes (la plus récente en premier)."""
import adf


def read_harvests(path):
    """-> [{SpeciesName, Score, TrophyScore, VariationName, Timestamp, RegionName}, ...]"""
    return adf.Adf(adf.unpack_save(path)).root()["HarvestHistory"]


def key(e):
    return (e["Timestamp"], e["SpeciesName"], e["VariationName"])
