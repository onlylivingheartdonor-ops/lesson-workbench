"""Download raw source files into raw/ (kept out of version control).

Files already present are reused, so ingest scripts can be rerun offline.
Delete a file under raw/ (or pass refresh=True) to force a fresh download.
"""

import datetime
import hashlib
import os
import time
import urllib.request

from library.db import ROOT

RAW_DIR = os.path.join(ROOT, "raw")
USER_AGENT = "LessonWorkbench-LibraryBuilder/1.0 (public-domain library assembly)"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, subdir, file_name=None, refresh=False, retries=4):
    file_name = file_name or url.rstrip("/").rsplit("/", 1)[-1]
    dest_dir = os.path.join(RAW_DIR, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, file_name)
    stamp = dest + ".retrieved"
    if refresh or not os.path.exists(dest):
        delay = 2
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as out:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                os.replace(dest + ".part", dest)
                break
            except Exception:
                if attempt == retries:
                    raise
                time.sleep(delay)
                delay *= 2
        with open(stamp, "w") as f:
            f.write(datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat())
    retrieved = open(stamp).read().strip() if os.path.exists(stamp) else \
        datetime.datetime.fromtimestamp(os.path.getmtime(dest), datetime.timezone.utc).replace(microsecond=0).isoformat()
    return {"path": dest, "file_name": file_name, "url": url, "retrieved_at": retrieved,
            "sha256": _sha256(dest), "bytes": os.path.getsize(dest)}
