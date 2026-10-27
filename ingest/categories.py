"""The 24 top-level categories Dave approved, and the placement of Nave's topics under them.

    python3 -m ingest.categories              # create the categories and place every topic
    python3 -m ingest.categories --unplaced   # list topics the rules leave unplaced, for the AI pass

Placement, in order of precedence:
  1. ingest/data/category_placements.tsv: placements read and decided one by one (method 'ai',
     the confidence written on each row; or 'manual' for rows Dave adds or corrects). A topic listed
     there takes only the categories listed for it.
  2. Structural rules for named people and places (method 'structural'): Nave's own sub-topic lines
     ("Son of Shimhi", "A city of Italy") say whether a topic is a person, a people, or a place. People
     go to Old or New Testament People by where the topic's verses fall. Topics with no Nave's lines
     are left to the placement file (the --unplaced listing shows the dictionary article's opening).
A topic may sit under several categories.
"""

import collections
import csv
import os
import re
import sys

from library import db

DATA = os.path.join(db.ROOT, "ingest", "data")

PERSON = re.compile(
    r"\b(son|sons|daughter|wife|father|mother|brother|sister|grandson|descendant|descendants|husband|chief|"
    r"king|queen|prince|priest|high priest|levite|prophet|prophetess|apostle|disciple|man|woman|"
    r"gershonite|kohathite|merarite|benjamite|judge|governor|captain|servant|officer|ancestor|head of|"
    r"founder|leader|warrior|mighty men|scribe|singer|porter|gatekeeper|nethinim|exile|exiles|companion|"
    r"an? [a-z]+ite)\b")
PEOPLE = re.compile(r"\b(tribe|tribes|people|peoples|nation|race|inhabitants|clan|family of)\b")
PLACE = re.compile(
    r"\b(city|cities|town|village|mountain|mount|hill|river|brook|valley|station|stations|region|district|"
    r"country|land of|place|plain|well|desert|wilderness|island|sea|lake|province|fortress|stream|pool|"
    r"camping|encampment|border|territory|suburb|ford|spring|fountain|pass|cave|tower|field|road|gate)\b")
CONCEPT = re.compile(r"^(general scriptures|figurative|instances of|symbolical|unclassified|exhortation|"
                     r"promises|commandments|miscellany|illustrative|typified|described)")
SENSE = re.compile(r"^\(?\d+\.\s*|^-\d+\.\s*")


def rows(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.strip() and not line.startswith("#"):
            yield line.split("\t")



def first_match(rx, text):
    m = rx.search(text)
    return m.start() if m else None


def kind_of(text):
    """'person', 'people' or 'place' for one sense of a name, by whichever signal comes first. Only the
    opening words count: a person or place line says so at once ("Son of Shimhi", "A city of Italy"),
    while a subject line mentions people in passing ("Attached to the hem of the priest's robe")."""
    text = " ".join(text.replace("(", " ").replace(")", " ").split()[:5])
    hits = {k: first_match(rx, text) for k, rx in (("person", PERSON), ("people", PEOPLE), ("place", PLACE))}
    hits = {k: v for k, v in hits.items() if v is not None}
    return min(hits, key=hits.get) if hits else None


def dict_opening(con, name):
    row = con.execute("""SELECT substr(e.body, 1, 160) FROM entries e JOIN works w ON w.id = e.work_id
                         WHERE w.code IN ('EASTON', 'SMITH') AND lower(e.title) = lower(?) ORDER BY w.code""",
                      (name,)).fetchone()
    return " ".join(row[0].split()) if row else None


def structural(con):
    """topic id -> set of category codes, for the topics the person/place rules can decide."""
    subs = collections.defaultdict(list)
    for parent, name in con.execute("SELECT parent_id, name FROM subjects WHERE level='subtopic' ORDER BY id"):
        subs[parent].append(name.lower())
    testament = collections.defaultdict(lambda: [0, 0])
    for sid, v in con.execute("""SELECT COALESCE(s.parent_id, s.id), ss.start_verse_id FROM subject_scripture ss
                                 JOIN subjects s ON s.id = ss.subject_id"""):
        testament[sid][0 if v // 1000000 <= 39 else 1] += 1

    placed = {}
    for sid, name in con.execute("SELECT id, name FROM subjects WHERE level='topic'"):
        lines = subs.get(sid, [])
        if any(CONCEPT.match(SENSE.sub("", ln)) for ln in lines):
            continue  # a subject ("King", "Priest"), not one named person or place
        senses = [SENSE.sub("", ln) for ln in lines if SENSE.match(ln)]
        if senses:
            kinds = {kind_of(s) for s in senses} - {None}
        else:
            kinds = {kind_of(lines[0])} - {None} if lines else set()
        if not kinds:
            continue
        cats = set()
        if kinds & {"person", "people"}:
            ot, nt = testament[sid]
            cats.add("nt-people" if nt > ot else "ot-people")
        if "place" in kinds:
            cats.add("places")
        placed[sid] = cats
    return placed


def main(argv):
    con = db.connect()
    problems = []
    cat_id = {}
    for pos, (code, name, desc) in enumerate(rows("categories.tsv"), start=1):
        slug = f"category-{code}"
        row = con.execute("SELECT id FROM subjects WHERE slug=?", (slug,)).fetchone()
        if row:
            con.execute("UPDATE subjects SET name=?, description=?, level='category', source_key=? WHERE id=?",
                        (name, desc, str(pos), row[0]))
            cat_id[code] = row[0]
        else:
            cat_id[code] = con.execute("""INSERT INTO subjects(name, slug, level, source_key, description)
                                          VALUES (?,?,?,?,?)""", (name, slug, "category", str(pos), desc)).lastrowid
    con.execute(f"DELETE FROM subjects WHERE level='category' AND id NOT IN ({','.join('?' * len(cat_id))})",
                list(cat_id.values()))
    topic_name = dict(con.execute("SELECT id, name FROM subjects WHERE level='topic'"))
    ids_by_name = collections.defaultdict(list)
    for i, n in topic_name.items():
        ids_by_name[n].append(i)
    rules = structural(con)

    listed = {}
    for row in rows("category_placements.tsv"):
        topic, codes = row[0], row[1]
        conf = float(row[2]) if len(row) > 2 and row[2] else 0.9
        method = row[3] if len(row) > 3 and row[3] else "ai"
        if topic not in ids_by_name:
            problems.append(f"placement for unknown topic: {topic}")
            continue
        cats = [c.strip() for c in codes.split(",") if c.strip()]
        bad = [c for c in cats if c not in cat_id]
        if bad:
            problems.append(f"{topic}: unknown category code(s) {bad}")
        ids = ids_by_name[topic]
        if len(ids) > 1:
            # Two Nave's topics share this name (e.g. "Sin" and the Desert of Sin): a row placed by hand is
            # for the one the person/place rules do not cover.
            ids = [i for i in ids if i not in rules] or ids
        for i in ids:
            listed[i] = ([c for c in cats if c in cat_id], conf, method)
    if "--unplaced" in argv:
        unplaced = [i for i in topic_name if i not in listed and i not in rules]
        usage = dict(con.execute("SELECT subject_id, COUNT(*) FROM entry_subjects GROUP BY subject_id"))
        for i in sorted(unplaced, key=lambda i: (-usage.get(i, 0), topic_name[i])):
            subs = [r[0] for r in con.execute("SELECT name FROM subjects WHERE parent_id=? ORDER BY id LIMIT 4", (i,))]
            hint = "; ".join(subs)[:110] or "[dictionary] " + (dict_opening(con, topic_name[i]) or "")[:110]
            print(f"{topic_name[i]}\t{hint}")
        print(f"({len(unplaced)} unplaced)", file=sys.stderr)
        return 0

    con.execute("DELETE FROM category_topics")
    counts = collections.Counter()
    for tid in topic_name:
        if tid in listed:
            cats, conf, method = listed[tid]
        elif tid in rules:
            cats, conf, method = sorted(rules[tid]), 0.85, "structural"
        else:
            continue
        for c in cats:
            con.execute("INSERT INTO category_topics(category_id, topic_id, method, confidence) VALUES (?,?,?,?)",
                        (cat_id[c], tid, method, conf))
            counts[(c, method)] += 1
    con.commit()

    # Uncertain placements go to a review list for Dave.
    path = os.path.join(db.ROOT, "review", "category_review.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["topic", "categories", "confidence", "method", "nave_lines"])
        for name, cats, conf, method, tid in con.execute("""
                SELECT t.name, group_concat(c.name, '; '), MAX(ct.confidence), ct.method, t.id
                FROM category_topics ct JOIN subjects t ON t.id = ct.topic_id JOIN subjects c ON c.id = ct.category_id
                WHERE ct.confidence < 0.8 GROUP BY t.id ORDER BY t.name""").fetchall():
            lines = [r[0] for r in con.execute("SELECT name FROM subjects WHERE parent_id=? ORDER BY id LIMIT 4", (tid,))]
            out.writerow([name, cats, conf, method, "; ".join(lines)])

    placed = con.execute("SELECT COUNT(DISTINCT topic_id) FROM category_topics").fetchone()[0]
    print(f"categories: {len(cat_id)}; topics placed: {placed} of {len(topic_name)}")
    for code in cat_id:
        by = {m: counts[(code, m)] for m in ("structural", "ai", "manual") if counts[(code, m)]}
        print(f"  {code:18} {sum(by.values()):5}  {by}")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
