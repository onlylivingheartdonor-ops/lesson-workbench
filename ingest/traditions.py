"""Author tradition tags, the (proposed) filter traditions, and contested-topic flags.

    python3 -m ingest.traditions

Reads three hand-maintained files in ingest/data/:
  traditions.tsv          the filter traditions (status 'proposed' until Dave approves;
                          an 'approved' status already in the database is kept)
  author_traditions.tsv   a descriptive tag per author, plus the filter tradition(s) it counts toward
  contested_topics.tsv    Nave's topics where Christian traditions genuinely differ
Run after every other ingest step (build.py does this), because the other steps create the authors.
"""

import os
import sys

from library import db

DATA = os.path.join(db.ROOT, "ingest", "data")


def rows(name):
    for line in open(os.path.join(DATA, name), encoding="utf-8"):
        line = line.rstrip("\n")
        if line.strip() and not line.startswith("#"):
            yield line.split("\t")


def ensure_schema(con):
    """Bring a database built before these tables existed up to the current schema."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(authors)")}
    for col in ("tradition", "tradition_note"):
        if col not in cols:
            con.execute(f"ALTER TABLE authors ADD COLUMN {col} TEXT")
    if "contested" not in {r[1] for r in con.execute("PRAGMA table_info(subjects)")}:
        con.execute("ALTER TABLE subjects ADD COLUMN contested INTEGER NOT NULL DEFAULT 0")
    con.execute("""CREATE TABLE IF NOT EXISTS traditions (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE,
                   name TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'proposed', sort_order INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS author_traditions (author_id INTEGER NOT NULL REFERENCES authors(id),
                   tradition_id INTEGER NOT NULL REFERENCES traditions(id), note TEXT,
                   PRIMARY KEY (author_id, tradition_id))""")


def main():
    con = db.connect()
    ensure_schema(con)
    problems = []

    codes = []
    for pos, (code, name, desc) in enumerate(rows("traditions.tsv"), start=1):
        codes.append(code)
        con.execute("""INSERT INTO traditions(code, name, description, sort_order) VALUES (?,?,?,?)
                       ON CONFLICT(code) DO UPDATE SET name=excluded.name, description=excluded.description,
                       sort_order=excluded.sort_order""", (code, name, desc, pos))
    con.execute("DELETE FROM author_traditions")
    con.execute(f"DELETE FROM traditions WHERE code NOT IN ({','.join('?' * len(codes))})", codes)
    trad_id = dict(con.execute("SELECT code, id FROM traditions"))

    con.execute("UPDATE authors SET tradition=NULL, tradition_note=NULL")
    tagged = set()
    for name, tag, filt, note in rows("author_traditions.tsv"):
        row = con.execute("SELECT id FROM authors WHERE name=?", (name,)).fetchone()
        if not row:
            problems.append(f"author not in database: {name}")
            continue
        tagged.add(row[0])
        con.execute("UPDATE authors SET tradition=?, tradition_note=? WHERE id=?",
                    (None if tag == "-" else tag, note, row[0]))
        for code in ([] if filt == "-" else filt.split(",")):
            if code not in trad_id:
                problems.append(f"{name}: unknown tradition code {code}")
                continue
            con.execute("INSERT INTO author_traditions(author_id, tradition_id) VALUES (?,?)", (row[0], trad_id[code]))
    for aid, name in con.execute("SELECT id, name FROM authors"):
        if aid not in tagged:
            problems.append(f"author has no row in author_traditions.tsv: {name}")

    con.execute("UPDATE subjects SET contested=0")
    contested = 0
    for name, _why in rows("contested_topics.tsv"):
        n = con.execute("UPDATE subjects SET contested=1 WHERE level='topic' AND name=?", (name,)).rowcount
        if not n:
            problems.append(f"contested topic not found: {name}")
        contested += n
    con.commit()

    print(f"traditions: {len(codes)} ({', '.join(codes)}); authors tagged: {len(tagged)}; contested topics: {contested}")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
