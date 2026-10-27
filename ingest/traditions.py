"""Author tradition tags, the approved filter traditions, section authors, and contested points.

    python3 -m ingest.traditions

Reads hand-maintained files in ingest/data/:
  traditions.tsv          the filter traditions and their status (all five approved by Dave)
  author_traditions.tsv   a descriptive tag per author, plus the filter tradition(s) it counts toward
  section_authors.tsv     which author wrote which Bible books of a multi-author work (JFB)
  contested_topics.tsv    points where traditions genuinely differ, and the Nave's topics each touches
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
    existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    schema = open(os.path.join(db.ROOT, "schema.sql"), encoding="utf-8").read()
    for name in ("traditions", "author_traditions", "section_authors", "contested_issues",
                 "contested_issue_topics", "entry_authors"):
        if name in existing:
            continue
        kind = "VIEW" if name == "entry_authors" else "TABLE"
        start = schema.index(f"CREATE {kind} {name} ")
        con.execute(schema[start:schema.index(";", start)])


def main():
    con = db.connect()
    ensure_schema(con)
    problems = []

    codes = []
    for pos, (code, name, status, desc) in enumerate(rows("traditions.tsv"), start=1):
        codes.append(code)
        con.execute("""INSERT INTO traditions(code, name, description, status, sort_order) VALUES (?,?,?,?,?)
                       ON CONFLICT(code) DO UPDATE SET name=excluded.name, description=excluded.description,
                       status=excluded.status, sort_order=excluded.sort_order""", (code, name, desc, status, pos))
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

    con.execute("DELETE FROM section_authors")
    sections = 0
    for code, name, b1, b2, source in rows("section_authors.tsv"):
        work = con.execute("SELECT id FROM works WHERE code=?", (code,)).fetchone()
        author = con.execute("SELECT id FROM authors WHERE name=?", (name,)).fetchone()
        if not work or not author:
            problems.append(f"section author row not matched: {code} {name}")
            continue
        con.execute("INSERT INTO section_authors(work_id, author_id, book_from, book_to, source) VALUES (?,?,?,?,?)",
                    (work[0], author[0], int(b1), int(b2), source))
        sections += 1

    con.execute("UPDATE subjects SET contested=0")
    con.execute("DELETE FROM contested_issue_topics")
    con.execute("DELETE FROM contested_issues")
    issues = whole = part = 0
    for code, name, desc, topics in rows("contested_topics.tsv"):
        iid = con.execute("INSERT INTO contested_issues(code, name, description) VALUES (?,?,?)",
                          (code, name, desc)).lastrowid
        issues += 1
        for item in topics.split(";"):
            topic, scope = item.rsplit(":", 1)
            sid = con.execute("SELECT id FROM subjects WHERE level='topic' AND name=?", (topic,)).fetchone()
            if not sid:
                problems.append(f"{code}: Nave's topic not found: {topic}")
                continue
            con.execute("INSERT INTO contested_issue_topics(issue_id, subject_id, scope) VALUES (?,?,?)",
                        (iid, sid[0], scope))
            if scope == "whole":
                con.execute("UPDATE subjects SET contested=1 WHERE id=?", (sid[0],))
                whole += 1
            else:
                part += 1
    con.commit()

    print(f"traditions: {', '.join(codes)}; authors tagged: {len(tagged)}; JFB sections: {sections}; "
          f"contested points: {issues} ({whole} whole topics, {part} partly contested topics)")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
