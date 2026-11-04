"""Lecteur des sauvegardes COTW : conteneur SAVE (zlib) + format ADF typé (décodé sur tes vrais fichiers)."""
import struct
import zlib

PRIM = {0x580D0A62: "<b", 0x0CA2821D: "<B", 0xD13FCF93: "<h", 0x86D152BD: "<H", 0x192FE633: "<i",
        0x075E4E4F: "<I", 0xAF41354F: "<q", 0xA139E01F: "<Q", 0x7515A207: "<f", 0xC609F663: "<d"}
STRING = 0x8955583E


def unpack_save(path):
    """Fichier .adf du jeu -> octets ADF décompressés (vérifie la taille annoncée)."""
    with open(path, "rb") as f:
        d = f.read()
    if d[:4] != b"SAVE":
        raise ValueError("pas un fichier SAVE")
    out = zlib.decompressobj().decompress(d[32:])
    if struct.unpack_from("<I", d, 8)[0] != len(out):
        raise ValueError("fichier incomplet (écriture en cours ?)")
    return out


class Adf:
    def __init__(self, raw):
        base = raw.find(b" FDA")
        if base < 0:
            raise ValueError("en-tête ADF introuvable")
        self.a = a = raw[base:]
        (_, _, ic, io, tc, to, _, _, nc, no, _) = struct.unpack_from("<11I", a, 0)
        self.names, p = [], no + nc
        for ln in a[no:no + nc]:
            self.names.append(a[p:p + ln].decode("latin-1"))
            p += ln + 1
        self.types, p = {}, to
        for _ in range(tc):
            kind, size, _, h, ni, _, elem, elen = struct.unpack_from("<IIIIQIII", a, p)
            (n,) = struct.unpack_from("<I", a, p + 36)
            p += 40
            td = {"kind": kind, "size": size, "name": self.names[ni], "elem": elem, "count": elen, "members": []}
            if kind == 1:
                for _ in range(n):
                    mni, mth, _, moff, _, _ = struct.unpack_from("<QIIIIQ", a, p)
                    p += 32
                    td["members"].append((self.names[mni], mth, moff & 0xFFFFFF))
            elif kind == 8:
                p += 12 * n
            self.types[h] = td
        self.instances = []
        for i in range(ic):
            nh, th, off, size, _ = struct.unpack_from("<IIIIQ", a, io + 24 * i)
            self.instances.append((th, off))

    def _size(self, th):
        return struct.calcsize(PRIM[th]) if th in PRIM else 8 if th == STRING else self.types[th]["size"]

    def read(self, th, off, ib):
        """Lit une valeur ; ib = début de l'instance (les tableaux y sont relatifs)."""
        if th in PRIM:
            return struct.unpack_from(PRIM[th], self.a, off)[0]
        if th == STRING:
            o = struct.unpack_from("<Q", self.a, off)[0]
            return self.a[o:self.a.index(b"\0", o)].decode("utf-8", "replace")
        td = self.types[th]
        if td["kind"] == 1:
            return {n: self.read(t, off + mo, ib) for n, t, mo in td["members"]}
        if td["kind"] == 4:                            # tableau INLINE (« IA[...] ») : les éléments sont stockés sur place
            sz = self._size(td["elem"])
            c = td["count"] or (td["size"] // sz if sz else 0)
            return [self.read(td["elem"], off + i * sz, ib) for i in range(min(c, 200000))]
        if td["kind"] == 3:                            # tableau : u32 offset, u32 ?, u64 nombre
            o, c = struct.unpack_from("<IxxxxQ", self.a, off)
            sz = self._size(td["elem"])
            return [self.read(td["elem"], ib + o + i * sz, ib) for i in range(min(c, 200000))]
        return struct.unpack_from("<I", self.a, off)[0]

    def root(self):
        th, off = self.instances[0]
        return self.read(th, off, off)

    def read_member(self, *names):
        """Lit seulement un sous-champ de la racine (ex. read_member("TrophyAnimals", "LastHarvest"))."""
        th, off = self.instances[0]
        ib = off
        for n in names:
            td = self.types[th]
            if td["kind"] != 1:
                raise KeyError(n)
            for mn, mth, mo in td["members"]:
                if mn == n:
                    th, off = mth, off + mo
                    break
            else:
                raise KeyError(n)
        return self.read(th, off, ib)
