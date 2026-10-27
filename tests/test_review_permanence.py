"""Reviewed link decisions are permanent: re-running the tagger must never overwrite or remove them.

    python3 -m unittest tests.test_review_permanence -v

Works on a copy of library.db (the real database is never touched) and runs the real tagger, so it
takes a few minutes. It proves two things:

1. Re-running tagging leaves every reviewed link (accepted, rejected or corrected, by the review list
   or by a spot check) exactly as it was: same link, same status, same confidence.
2. If a reviewed link does disappear (as happens when a work is re-ingested and its entries are
   rebuilt), re-applying the recorded decisions brings it back, and every recorded decision is again
   in effect.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from library import db  # noqa: E402

REVIEWED_ROWS = f"""SELECT es.entry_id, es.subject_id, es.review_status, es.method_detail, es.confidence
                    FROM entry_subjects es WHERE {db.REVIEWED}"""


def run(module_code, db_path):
    """Run a snippet of the ingest code against the copy (LIBRARY_DB points db.connect at it)."""
    env = dict(os.environ, LIBRARY_DB=db_path)
    out = subprocess.run([sys.executable, "-c", module_code], cwd=ROOT, env=env, capture_output=True, text=True)
    if out.returncode not in (0, None):
        raise AssertionError(f"{module_code} failed:\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}")
    return out.stdout


class ReviewPermanence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(db.DB_PATH):
            raise unittest.SkipTest("library.db not present (run tools/restore_db.py first)")
        cls.tmp = tempfile.mkdtemp(prefix="review-permanence-")
        cls.path = os.path.join(cls.tmp, "library.db")
        src = sqlite3.connect(db.DB_PATH)
        dst = sqlite3.connect(cls.path)
        src.backup(dst)          # a consistent copy, including anything still in the WAL
        dst.close()
        src.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_tagging_rerun_never_touches_reviewed_links_and_apply_restores_removed_ones(self):
        con = sqlite3.connect(self.path)
        before = set(con.execute(REVIEWED_ROWS))
        self.assertGreater(len(before), 1000, "expected the copy to hold the recorded review decisions")

        # Simulate what a work re-ingest does: some reviewed links vanish. Take a spread of accepted,
        # rejected and spot-checked links, and remember them. (Nave's "entry is the topic itself" links are
        # accepted by construction, not by a reviewer, and are rebuilt by the Nave's ingest, so they are left out.)
        victims = con.execute(f"""SELECT es.id, es.entry_id, es.subject_id, es.review_status FROM entry_subjects es
                                  WHERE {db.REVIEWED} AND method_detail NOT IN ('ai_review_fix', 'nave_topic_entry')
                                  ORDER BY (es.id * 7919) % 1000003 LIMIT 300""").fetchall()
        self.assertTrue({v[3] for v in victims} >= {"ai_accepted", "ai_rejected", "accepted"})
        con.executemany("DELETE FROM link_reviews WHERE entry_subject_id=?", [(v[0],) for v in victims])
        con.executemany("DELETE FROM spot_checks WHERE entry_subject_id=?", [(v[0],) for v in victims])
        con.executemany("DELETE FROM review_queue WHERE entry_subject_id=?", [(v[0],) for v in victims])
        con.executemany("DELETE FROM entry_subjects WHERE id=?", [(v[0],) for v in victims])
        con.commit()
        survivors = set(con.execute(REVIEWED_ROWS))
        con.close()

        # 1. A full re-run of the tagger leaves every surviving reviewed link exactly as it was.
        run("from ingest import tagging; tagging.main()", self.path)
        con = sqlite3.connect(self.path)
        after_tagging = set(con.execute(REVIEWED_ROWS))
        self.assertEqual(survivors - after_tagging, set(),
                         "tagging removed or changed reviewed links")
        con.close()

        # 2. Re-applying the decisions (as build.py does) re-creates the removed reviewed links...
        run("from ingest import ai_review, spot_checks; ai_review.main(['apply']); spot_checks.main(['import'])",
            self.path)
        con = sqlite3.connect(self.path)
        for _, entry_id, subject_id, status in victims:
            row = con.execute("SELECT review_status FROM entry_subjects WHERE entry_id=? AND subject_id=?",
                              (entry_id, subject_id)).fetchone()
            self.assertIsNotNone(row, f"reviewed link {entry_id}->{subject_id} was not restored")
            self.assertEqual(row[0], status, f"reviewed link {entry_id}->{subject_id} came back as {row[0]}")

        # ... and every recorded decision is in effect.
        sys.path.insert(0, ROOT)
        os.environ["LIBRARY_DB"] = self.path
        from ingest import ai_review
        self.assertEqual(ai_review.verify(con), [])
        con.close()


if __name__ == "__main__":
    unittest.main()
