"""Rebuild the whole library database from the original sources.

    python3 build.py            # update library.db in place (each script replaces its own works)
    python3 build.py --fresh    # delete library.db first and build from nothing

Raw source files are downloaded into raw/ on first use and reused after
that.  Order matters: the Bibles define the verse scheme; Nave's defines the
subjects; tagging and spot checks run last.
"""

import os
import sys
import time

from library import db

STEPS = [
    ("Bibles (KJV, ASV, BBE, WEB) + KJV Strong's word links", "ingest.bibles"),
    ("Strong's Hebrew and Greek dictionaries", "ingest.strongs"),
    ("Thayer's Greek Lexicon supplement (31 missing Strong's numbers)", "ingest.thayer"),
    ("Nave's Topical Bible", "ingest.naves"),
    ("Treasury of Scripture Knowledge", "ingest.tsk"),
    ("Commentaries (Henry, Clarke, Barnes, JFB)", "ingest.commentaries"),
    ("Dictionaries and encyclopedia (Easton, Smith, ISBE)", "ingest.dictionaries"),
    ("Barnes' Old Testament notes (archive.org scans)", "ingest.barnes_ot"),
    ("Sermons and devotional works (Project Gutenberg)", "ingest.devotional"),
    ("Spurgeon's sermons, selection (archive.org scans)", "ingest.spurgeon"),
    ("Maclaren's Expositions of Holy Scripture (Project Gutenberg)", "ingest.maclaren"),
    ("Broadus on Matthew (archive.org scan)", "ingest.broadus"),
    ("Lutheran sources (Project Gutenberg; Luther on Galatians from archive.org)", "ingest.lutheran"),
    ("Early Pentecostal writings, before 1931 (archive.org scans)", "ingest.pentecostal"),
    ("Author tradition tags, approved traditions, contested topics", "ingest.traditions"),
    ("Top-level categories and the placement of Nave's topics under them", "ingest.categories"),
    ("Subject tagging and related subjects", "ingest.tagging"),
    ("Review-list decisions (AI reviewer)", "ingest.ai_review"),
    ("Spot-check results", "ingest.spot_checks"),
]


def main(argv):
    if "--fresh" in argv:
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(db.DB_PATH + suffix):
                os.remove(db.DB_PATH + suffix)
    for label, module in STEPS:
        t = time.time()
        print(f"\n### {label}")
        mod = __import__(module, fromlist=["main"])
        if module == "ingest.spot_checks":
            mod.main(["import"])
        elif module == "ingest.ai_review":
            mod.main(["apply"])
        elif module in ("ingest.commentaries", "ingest.dictionaries", "ingest.devotional", "ingest.barnes_ot",
                        "ingest.spurgeon", "ingest.maclaren", "ingest.broadus", "ingest.lutheran", "ingest.pentecostal",
                        "ingest.categories"):
            mod.main([])
        else:
            mod.main()
        print(f"    ({time.time() - t:.0f}s)")
    con = db.connect()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.execute("VACUUM")
    con.close()
    print(f"\nDone: {db.DB_PATH} ({os.path.getsize(db.DB_PATH) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main(sys.argv[1:])
