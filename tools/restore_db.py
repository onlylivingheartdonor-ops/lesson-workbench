"""Rebuild library.db from the compressed parts in data/ (no downloads needed).

    python3 tools/restore_db.py
"""

import glob
import hashlib
import lzma
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "library.db")
DATA = os.path.join(ROOT, "data")


def main():
    parts = sorted(glob.glob(os.path.join(DATA, "library.db.xz.part-*")))
    if not parts:
        print("no data/library.db.xz.part-* files found")
        return 1
    dec = lzma.LZMADecompressor()
    h = hashlib.sha256()
    with open(DB + ".tmp", "wb") as out:
        for p in parts:
            with open(p, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    data = dec.decompress(block)
                    h.update(data)
                    out.write(data)
    expected = open(os.path.join(DATA, "library.db.sha256")).read().split()[0]
    if h.hexdigest() != expected:
        os.remove(DB + ".tmp")
        print("checksum mismatch: the parts are incomplete or damaged")
        return 1
    os.replace(DB + ".tmp", DB)
    print(f"restored {DB} ({os.path.getsize(DB) / 1e6:.0f} MB), checksum OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
