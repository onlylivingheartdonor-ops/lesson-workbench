"""Database helpers shared by all ingest scripts."""

import datetime
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("LIBRARY_DB", os.path.join(ROOT, "library.db"))

REFERENCE_TYPES = [
    ("bible", "Bible", "A Bible translation"),
    ("commentary", "Commentary", "Verse-by-verse or passage notes"),
    ("dictionary", "Dictionary", "Bible dictionary articles"),
    ("encyclopedia", "Encyclopedia", "Bible encyclopedia articles"),
    ("topical_index", "Topical index", "Subjects mapped to verses (e.g. Nave's)"),
    ("cross_reference", "Cross-reference", "Verse-to-verse references (e.g. Treasury of Scripture Knowledge)"),
    ("lexicon", "Lexicon", "Hebrew and Greek word definitions (Strong's)"),
    ("sermon", "Sermon", "Preached sermons"),
    ("devotional", "Devotional", "Devotional and practical works"),
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = NORMAL")
    if not con.execute("SELECT name FROM sqlite_master WHERE name='works'").fetchone():
        con.executescript(open(os.path.join(ROOT, "schema.sql")).read())
        con.executemany("INSERT INTO reference_types(code, name, description) VALUES (?,?,?)", REFERENCE_TYPES)
        con.commit()
    return con


def ref_type_id(con, code):
    return con.execute("SELECT id FROM reference_types WHERE code=?", (code,)).fetchone()[0]


def author_id(con, name, sort_name=None, born=None, died=None, description=None):
    row = con.execute("SELECT id FROM authors WHERE name=?", (name,)).fetchone()
    if row:
        con.execute("UPDATE authors SET sort_name=?, born=?, died=?, description=? WHERE id=?",
                    (sort_name, born, died, description, row[0]))
        return row[0]
    return con.execute("INSERT INTO authors(name, sort_name, born, died, description) VALUES (?,?,?,?,?)",
                       (name, sort_name, born, died, description)).lastrowid


def clear_work(con, work_id):
    """Remove everything previously ingested for a work so a rerun starts clean."""
    entry_ids = "SELECT id FROM entries WHERE work_id=?"
    es_ids = f"SELECT id FROM entry_subjects WHERE entry_id IN ({entry_ids})"
    con.execute(f"DELETE FROM spot_checks WHERE entry_subject_id IN ({es_ids})", (work_id,))
    con.execute(f"DELETE FROM review_queue WHERE entry_subject_id IN ({es_ids})", (work_id,))
    con.execute(f"DELETE FROM link_reviews WHERE entry_subject_id IN ({es_ids})", (work_id,))
    con.execute(f"DELETE FROM entry_subjects WHERE entry_id IN ({entry_ids})", (work_id,))
    con.execute(f"DELETE FROM entry_scripture WHERE entry_id IN ({entry_ids})", (work_id,))
    con.execute("UPDATE strongs SET entry_id=NULL WHERE entry_id IN (SELECT id FROM entries WHERE work_id=?)", (work_id,))
    con.execute("UPDATE entries SET parent_id=NULL WHERE work_id=?", (work_id,))
    con.execute("DELETE FROM entries WHERE work_id=?", (work_id,))
    con.execute("DELETE FROM bible_text WHERE work_id=?", (work_id,))
    con.execute("DELETE FROM verse_words WHERE work_id=?", (work_id,))
    con.execute("DELETE FROM cross_references WHERE source_work_id=?", (work_id,))
    con.execute("DELETE FROM subject_scripture WHERE source_work_id=?", (work_id,))
    con.execute("DELETE FROM provenance WHERE work_id=?", (work_id,))
    con.execute("DELETE FROM work_authors WHERE work_id=?", (work_id,))


# Works whose digital edition descends from CCEL's texts.  Dave's decision
# (2026-10-27): keep them for now, but replace them before launch.
REPLACE_BEFORE_LAUNCH = {
    "MHC": "CrossWire edition prepared from CCEL's text. Candidate independent sources: archive.org scans of the "
           "printed Exposition, e.g. the Duke Divinity School set expositionofoldn11henr ... expositionofoldn61henr "
           "(early 18th-century printing; long-s type makes OCR harder) or a 19th-century American edition.",
    "JFB": "CrossWire edition prepared from CCEL's text (ccel.org/ccel/j/jamieson/jfb). Candidate independent source: "
           "the one-volume Commentary Critical and Explanatory, Princeton Theological Seminary scan "
           "commentarycritic00jami (1873, marked NOT_IN_COPYRIGHT).",
    "NAVE": "CrossWire edition prepared from CCEL's XML (ccel.org/ccel/n/nave/bible.xml). Candidate independent "
            "sources: Princeton scan navestopicalbibl00nave or University of Toronto scan "
            "topicalbibledige00naveuoft (both 1903, marked NOT_IN_COPYRIGHT).",
    "EASTON": "CrossWire edition prepared from CCEL's text. Candidate independent source: Library of Congress scan "
              "illustratedbible00east (1893 edition; LoC 'unaware of any copyright restrictions'); the 1897 third "
              "edition would need a further search.",
}


def upsert_work(con, code, title, ref_type, authors, license_status, **fields):
    """Create or reset a work. `authors` is a list of (name, role, author-fields dict)."""
    if code in REPLACE_BEFORE_LAUNCH:
        fields.setdefault("launch_status", "replace before launch")
        fields.setdefault("launch_note", REPLACE_BEFORE_LAUNCH[code])
    rt = ref_type_id(con, ref_type)
    cols = ["title", "reference_type_id", "license_status", "date_ingested"] + list(fields)
    vals = [title, rt, license_status, now()] + list(fields.values())
    row = con.execute("SELECT id FROM works WHERE code=?", (code,)).fetchone()
    if row:
        wid = row[0]
        clear_work(con, wid)
        # reset optional columns too so stale values do not linger
        for c in ("short_title", "original_date", "edition", "source_name", "source_url", "license_evidence",
                  "attribution_text", "coverage", "known_issues", "launch_status", "launch_note", "ingest_script"):
            con.execute(f"UPDATE works SET {c}=NULL WHERE id=?", (wid,))
        con.execute(f"UPDATE works SET {', '.join(c + '=?' for c in cols)} WHERE id=?", vals + [wid])
    else:
        wid = con.execute(f"INSERT INTO works(code, {', '.join(cols)}) VALUES (?{',?' * len(cols)})",
                          [code] + vals).lastrowid
    for pos, (name, role, extra) in enumerate(authors, start=1):
        aid = author_id(con, name, **(extra or {}))
        con.execute("INSERT OR IGNORE INTO work_authors(work_id, author_id, role, position) VALUES (?,?,?,?)",
                    (wid, aid, role, pos))
    return wid


def add_provenance(con, work_id, fetched, notes=None):
    """`fetched` is the dict returned by library.fetch.fetch()."""
    con.execute("INSERT INTO provenance(work_id, file_name, source_url, retrieved_at, sha256, bytes, notes) "
                "VALUES (?,?,?,?,?,?,?)",
                (work_id, fetched["file_name"], fetched["url"], fetched["retrieved_at"], fetched["sha256"],
                 fetched["bytes"], notes))


def log_ingest(con, script, work_code, started, stats):
    con.execute("INSERT INTO ingest_log(script, work_code, started_at, finished_at, stats) VALUES (?,?,?,?,?)",
                (script, work_code, started, now(), json.dumps(stats)))


def slugify(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "x"


class EntryWriter:
    """Batches entry + scripture inserts for speed."""

    def __init__(self, con, work_id):
        self.con = con
        self.work_id = work_id
        self.order = 0
        self.n_entries = 0
        self.n_refs = 0
        row = con.execute("SELECT COALESCE(MAX(id), 0) FROM entries").fetchone()
        self.next_id = row[0] + 1
        self._entries = []
        self._refs = []

    def add(self, entry_type, key, title, body, refs=(), parent_id=None):
        """refs: iterable of (start_vid, end_vid, relation, method, ref_text)."""
        eid = self.next_id
        self.next_id += 1
        self.order += 1
        self._entries.append((eid, self.work_id, entry_type, key, title, body, len(body.split()), self.order, parent_id))
        seen = set()
        for s, e, rel, method, txt in refs:
            k = (s, e, rel)
            if k in seen:
                continue
            seen.add(k)
            self._refs.append((eid, s, e, rel, method, txt))
        self.n_entries += 1
        if len(self._entries) >= 2000:
            self.flush()
        return eid

    def flush(self):
        self.con.executemany("INSERT INTO entries(id, work_id, entry_type, entry_key, title, body, word_count, "
                             "sort_order, parent_id) VALUES (?,?,?,?,?,?,?,?,?)", self._entries)
        self.con.executemany("INSERT INTO entry_scripture(entry_id, start_verse_id, end_verse_id, relation, method, "
                             "ref_text) VALUES (?,?,?,?,?,?)", self._refs)
        self.n_refs += len(self._refs)
        self._entries, self._refs = [], []
