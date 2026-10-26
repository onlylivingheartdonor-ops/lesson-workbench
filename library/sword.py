"""Minimal reader for CrossWire SWORD modules (no external dependencies).

Supports the drivers used by the works in this library:
  * zText / zCom / zCom4   - compressed verse-keyed Bibles and commentaries
  * RawLD / RawLD4         - uncompressed dictionaries (Smith, Strong's Hebrew)
  * zLD                    - compressed dictionaries (Nave, Easton, ISBE, Strong's Greek)

Format notes (from the SWORD engine source, verified against these files):
  zCom   .bzs/.czs: blocks   = (uint32 offset, uint32 compressed size, uint32 raw size)
         .bzv/.czv: verses   = (uint32 block, uint32 offset in block, uint16 size)   [zCom4: uint32 size]
         .bzz/.czz: zlib-compressed blocks
  RawLD  .idx: (uint32 offset, uint16 size) [RawLD4: uint32 size]; .dat: "KEY\\n" + text
  zLD    .idx: (uint32 offset, uint32 size); .dat: "KEY\\n" + (uint32 block, uint32 entry)
         .zdx: (uint32 offset, uint32 size) into .zdt; each zlib block =
               uint32 count, count x (uint32 offset, uint32 size), then data
"""

import configparser
import glob
import os
import struct
import zlib

from library.scripture import sword_index_map


def read_conf(path):
    """Parse a SWORD .conf file into (section name, dict of lists)."""
    raw = open(path, "rb").read().decode("utf-8", errors="replace")
    section, data = None, {}
    for line in raw.splitlines():
        line = line.rstrip()
        if line.startswith("[") and line.endswith("]") and section is None:
            section = line[1:-1]
            continue
        if "=" in line and not line.startswith((" ", "\t")):
            k, v = line.split("=", 1)
            data.setdefault(k.strip(), []).append(v.strip())
    return section, data


class VerseModule:
    """A verse-keyed module (Bible or commentary) in zText/zCom format."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.maps = sword_index_map()

    def _files(self, testament):
        for prefix in ("b", "c", "v"):  # BOOK, CHAPTER or VERSE blocking
            s = os.path.join(self.data_dir, f"{testament}.{prefix}zs")
            if os.path.exists(s):
                return s, os.path.join(self.data_dir, f"{testament}.{prefix}zv"), os.path.join(self.data_dir, f"{testament}.{prefix}zz")
        return None

    def iter_raw(self):
        """Yield (verse_id, block, offset, size, text_bytes) in canonical order.

        Linked verses (one note covering a range) share the same
        (block, offset, size); callers group them into ranges.
        """
        for testament in ("ot", "nt"):
            files = self._files(testament)
            if not files:
                continue
            bzs, bzv, bzz = files
            blocks_raw = open(bzs, "rb").read()
            blocks = [struct.unpack_from("<III", blocks_raw, i) for i in range(0, len(blocks_raw), 12)]
            vraw = open(bzv, "rb").read()
            nslots = len(self.maps[testament]) + 2
            if len(vraw) == nslots * 10:
                fmt, width = "<IIH", 10
            elif len(vraw) == nslots * 12:
                fmt, width = "<III", 12
            else:
                raise ValueError(f"{bzv}: unexpected index size {len(vraw)} for {nslots} slots")
            zfile = open(bzz, "rb")
            cache = {}
            for idx in range(2, nslots):
                block, off, size = struct.unpack_from(fmt, vraw, idx * width)
                if size == 0 or block >= len(blocks):
                    continue
                if block not in cache:
                    cache.clear()
                    boff, bsize, _ = blocks[block]
                    zfile.seek(boff)
                    cache[block] = zlib.decompress(zfile.read(bsize))
                text = cache[block][off:off + size]
                yield self.maps[testament][idx], block, off, size, text
            zfile.close()

    def iter_entries(self):
        """Yield (start_vid, end_vid, text) grouping linked consecutive verses."""
        cur = None
        for v, block, off, size, text in self.iter_raw():
            key = (block, off, size)
            if cur and cur[3] == key:
                cur[1] = v
                continue
            if cur:
                yield cur[0], cur[1], cur[2]
            cur = [v, v, text, key]
        if cur:
            yield cur[0], cur[1], cur[2]


def _decode(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")


def _split_key(raw):
    nl = raw.find(b"\n")
    if nl < 0:
        return raw.rstrip(b"\r\x00"), b""
    return raw[:nl].rstrip(b"\r"), raw[nl + 1:]


def iter_rawld(path_prefix):
    """Yield (key, text) from a RawLD/RawLD4 dictionary."""
    idx = open(path_prefix + ".idx", "rb").read()
    dat = open(path_prefix + ".dat", "rb").read()
    # RawLD uses 6-byte index records, RawLD4 8-byte; detect by plausibility.
    width = 6
    if len(idx) % 6 != 0 or (len(idx) % 8 == 0 and _plausible(idx, dat, 8) and not _plausible(idx, dat, 6)):
        width = 8
    fmt = "<IH" if width == 6 else "<II"
    for i in range(0, len(idx) - width + 1, width):
        off, size = struct.unpack_from(fmt, idx, i)
        raw = dat[off:off + size]
        key, body = _split_key(raw)
        if body.startswith(b"@LINK"):
            continue
        yield _decode(key), _decode(body)


def _plausible(idx, dat, width):
    fmt = "<IH" if width == 6 else "<II"
    try:
        for i in range(0, min(len(idx), width * 50), width):
            off, size = struct.unpack_from(fmt, idx, i)
            if off + size > len(dat):
                return False
        return True
    except struct.error:
        return False


def iter_zld(path_prefix):
    """Yield (key, text) from a zLD dictionary."""
    idx = open(path_prefix + ".idx", "rb").read()
    dat = open(path_prefix + ".dat", "rb").read()
    zdx = open(path_prefix + ".zdx", "rb").read()
    zdt = open(path_prefix + ".zdt", "rb")
    blocks = [struct.unpack_from("<II", zdx, i) for i in range(0, len(zdx), 8)]
    cache = {}

    def block_entries(bn):
        if bn not in cache:
            cache.clear()
            off, size = blocks[bn]
            zdt.seek(off)
            raw = zlib.decompress(zdt.read(size))
            count = struct.unpack_from("<I", raw, 0)[0]
            ents = []
            for j in range(count):
                eo, es = struct.unpack_from("<II", raw, 4 + j * 8)
                ents.append(raw[eo:eo + es].rstrip(b"\x00"))
            cache[bn] = ents
        return cache[bn]

    for i in range(0, len(idx), 8):
        off, size = struct.unpack_from("<II", idx, i)
        raw = dat[off:off + size]
        key, rest = _split_key(raw)
        if len(rest) < 8:
            continue
        bn, en = struct.unpack_from("<II", rest, 0)
        if bn >= len(blocks):
            continue
        ents = block_entries(bn)
        if en >= len(ents):
            continue
        body = ents[en]
        if body.startswith(b"@LINK"):
            continue
        yield _decode(key), _decode(body)
    zdt.close()


def open_module(module_root, conf_name):
    """Return (conf dict, reader) for an extracted module directory."""
    conf_path = os.path.join(module_root, "mods.d", conf_name)
    section, conf = read_conf(conf_path)
    data_path = conf["DataPath"][0].lstrip("./")
    driver = conf["ModDrv"][0].lower()
    full = os.path.join(module_root, data_path)
    if driver in ("ztext", "zcom", "zcom4", "ztext4"):
        return section, conf, VerseModule(full)
    if driver in ("rawld", "rawld4"):
        return section, conf, (lambda: iter_rawld(full))
    if driver == "zld":
        return section, conf, (lambda: iter_zld(full))
    raise ValueError(f"unsupported driver {driver}")


def find_module_dir(base):
    """Locate the extracted module root (the folder containing mods.d)."""
    hits = glob.glob(os.path.join(base, "**", "mods.d"), recursive=True)
    return os.path.dirname(hits[0]) if hits else None
