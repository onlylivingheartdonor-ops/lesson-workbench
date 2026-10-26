"""Compress library.db into data/library.db.xz.part-NN files for version control.

GitHub refuses files over 100 MB, so the compressed database is split into
parts of at most 45 MB.  data/library.db.sha256 records the checksum of the
uncompressed file so tools/restore_db.py can verify it.

    python3 tools/package_db.py
"""

import glob
import hashlib
import lzma
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "library.db")
DATA = os.path.join(ROOT, "data")
PART = 45 * 1024 * 1024


def main():
    if not os.path.exists(DB):
        print("library.db not found; run python3 build.py first")
        return 1
    os.makedirs(DATA, exist_ok=True)
    for old in glob.glob(os.path.join(DATA, "library.db.xz.part-*")):
        os.remove(old)
    h = hashlib.sha256()
    comp = lzma.LZMACompressor(preset=9 | lzma.PRESET_EXTREME)
    n, buf, written = 0, b"", 0

    def flush(data, final=False):
        nonlocal n, buf, written
        buf += data
        while len(buf) >= PART or (final and buf):
            chunk, buf = buf[:PART], buf[PART:]
            with open(os.path.join(DATA, f"library.db.xz.part-{n:02d}"), "wb") as f:
                f.write(chunk)
            written += len(chunk)
            n += 1

    with open(DB, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
            flush(comp.compress(block))
    flush(comp.flush(), final=True)
    with open(os.path.join(DATA, "library.db.sha256"), "w") as f:
        f.write(f"{h.hexdigest()}  library.db\n")
    print(f"{os.path.getsize(DB) / 1e6:.0f} MB -> {written / 1e6:.0f} MB in {n} part(s) under data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
