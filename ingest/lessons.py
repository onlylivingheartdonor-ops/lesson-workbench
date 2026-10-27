"""Load the lessons written in lessons/source/*.txt into the database.

    python3 -m ingest.lessons            # load (or reload) every lesson file
    python3 -m ingest.lessons --check    # check every file without writing to the database

Each lesson is a plain-text file following the lesson template (see lessons/README.md for the
format). Loading checks that:
  * every scripture reference resolves;
  * every commentator quote appears word for word in the library entry it cites (spacing and
    curly/straight quote marks aside), and credits that entry's actual author;
  * the sections come in the template's order, with "Where Christians differ" only on lessons
    about a contested point.
A file that fails any check is reported and not loaded. Lessons load as 'draft' (AI-generated,
not yet reviewed) and 'private'; a reload keeps any status Dave has already set.
Perspective summaries for contested points come from ingest/data/perspectives.tsv.
"""

import glob
import os
import re
import sys

from library import db
from library.scripture import format_ref, parse_free_refs

SOURCE_DIR = os.path.join(db.ROOT, "lessons", "source")
DATA = os.path.join(db.ROOT, "ingest", "data")
ORDER = ["opening", "scripture", "background", "point", "differ", "questions", "application", "prayer"]
KIND = {"point": "teaching_point"}
TRANSLATIONS = {"KJV", "ASV", "WEB", "BBE"}
# How each work is named in a quote's credit line ("Matthew Henry, Commentary on the Whole Bible, on ...").
CREDIT_TITLE = {
    "MHC": "Commentary on the Whole Bible",
    "CLARKE": "Commentary on the Bible",
    "BARNES": "Notes on the New Testament",
    "BARNES-OT": "Notes on the Old Testament",
    "JFB": "Commentary Critical and Explanatory on the Whole Bible (Jamieson, Fausset and Brown)",
    "MACLAREN": "Expositions of Holy Scripture",
    "BROADUS": "Commentary on the Gospel of Matthew",
    "SPURGEON-SERMONS": "sermon",
}
SETTINGS = [
    ("rating_min_votes", "5", "Ratings are shown and acted on only after this many votes (Dave's decision)."),
    ("rating_low_threshold", "2", "An average at or below this many stars counts as low-rated (placeholder)."),
    ("rating_high_threshold", "4.5", "An average at or above this, on an unreviewed lesson, flags it for review first."),
]


def norm(s):
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "--").replace("–", "-")
    return " ".join(s.split())


def parse(path):
    """A lesson file -> (header dict, [section dicts])."""
    head, sections, cur = {}, [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("#"):
            continue
        m = re.match(r"^== (\w+)(?:\s*\|\s*(\d+))?(?:\s*\|\s*(.+))?$", line)
        if m:
            cur = dict(kind=m.group(1), minutes=int(m.group(2)) if m.group(2) else None,
                       heading=(m.group(3) or "").strip(), text=[], note=[], verses=[], quotes=[], blanks=[],
                       questions=[], views=[], hidden=False)
            sections.append(cur)
            continue
        if cur is None:
            if ":" in line:
                k, v = line.split(":", 1)
                head[k.strip()] = v.strip()
            continue
        m = re.match(r"^(note|verses|quote|blank|q|view|hidden):\s*(.*)$", line)
        if m:
            key, val = m.groups()
            if key == "note":
                cur["note"].append(val)
            elif key == "verses":
                cur["verses"].append(val)
            elif key == "quote":
                eid, _, text = val.partition("|")
                cur["quotes"].append((int(eid.strip()), text.strip()))
            elif key == "blank":
                sent, _, ans = val.partition("|")
                cur["blanks"].append((sent.strip(), ans.strip()))
            elif key == "q":
                q, _, a = val.partition("|")
                cur["questions"].append((q.strip(), a.strip()))
            elif key == "view":
                cur["views"].append(val.strip())
            elif key == "hidden":
                cur["hidden"] = val.strip().lower() in ("yes", "true", "1")
            continue
        cur["text"].append(line)
    for s in sections:
        s["body"] = re.sub(r"\n{3,}", "\n\n", "\n".join(s["text"]).strip())
        s["teacher_note"] = " ".join(s["note"]).strip() or None
    return head, sections


def refs_of(text, problems, where):
    out = []
    for part in [p for p in re.split(r";", text) if p.strip()]:
        found = parse_free_refs(part.strip())
        if not found:
            problems.append(f"{where}: reference not understood: {part.strip()}")
        out += found
    return out


def tidy_entry_title(t):
    """Clean scanning marks out of a chapter title for a credit line."""
    t = re.sub(r" [(]part \d+ of \d+[)]", "", t)
    t = re.sub(r"\b(The|A|An)\. ", r"\1 ", t)                      # "The. Promise" (OCR)
    t = re.sub(r"\b[IVXLC][ivxlc]+\b", lambda m: m.group(0).upper(), t)   # "Xxxiii" -> "XXXIII"
    return t.strip(" —-:")


def credit_for(con, entry_id):
    row = con.execute("""SELECT w.title, w.code, e.title, r.code FROM entries e JOIN works w ON w.id = e.work_id
                         JOIN reference_types r ON r.id = w.reference_type_id WHERE e.id = ?""", (entry_id,)).fetchone()
    wtitle, wcode, etitle, rtype = row
    roles = dict(con.execute("""SELECT wa.author_id, wa.role FROM work_authors wa JOIN entries e ON e.work_id = wa.work_id
                                WHERE e.id = ?""", (entry_id,)))
    everyone = con.execute("""SELECT a.id, a.name FROM entry_authors ea JOIN authors a ON a.id = ea.author_id
                              WHERE ea.entry_id = ? ORDER BY a.id""", (entry_id,)).fetchall()
    # Translators are credited after the title ("tr. ..."), not as authors.
    authors = [a for a in everyone if roles.get(a[0]) != "translator"] or everyone
    translators = [a[1] for a in everyone if roles.get(a[0]) == "translator" and a not in authors]
    about = con.execute("""SELECT MIN(start_verse_id), MAX(end_verse_id) FROM entry_scripture
                           WHERE entry_id = ? AND relation = 'about'""", (entry_id,)).fetchone()
    names = " and ".join(a[1] for a in authors)
    wtitle = CREDIT_TITLE.get(wcode, wtitle)
    if translators:
        wtitle += f" (tr. {' and '.join(translators)})"
    if rtype == "commentary" and about[0]:
        where = "on " + re.sub(r"^Psalms (\d+)(?!-\d+$)", r"Psalm \1", format_ref(about[0], about[1]))
    else:
        where = f"“{tidy_entry_title(etitle)}”"
    credit = f"{names}, sermon {where}" if wtitle == "sermon" else f"{names}, {wtitle}, {where}"
    return (authors[0][0] if len(authors) == 1 else None), credit


def load_perspectives(con, problems):
    path = os.path.join(DATA, "perspectives.tsv")
    if not os.path.exists(path):
        return
    con.execute("DELETE FROM perspective_summaries WHERE status = 'draft'")
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        issue, trad, key_texts, summary, headline = (line.split("\t") + [""])[:5]
        iid = con.execute("SELECT id FROM contested_issues WHERE code = ?", (issue,)).fetchone()
        tid = con.execute("SELECT id FROM traditions WHERE code = ?", (trad,)).fetchone()
        if not iid or not tid:
            problems.append(f"perspectives.tsv: unknown issue or tradition: {issue} {trad}")
            continue
        con.execute("""INSERT INTO perspective_summaries(issue_id, tradition_id, summary, headline, key_texts)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(issue_id, tradition_id) DO UPDATE SET summary = excluded.summary,
                       headline = excluded.headline, key_texts = excluded.key_texts
                       WHERE perspective_summaries.status = 'draft'""",
                    (iid[0], tid[0], summary, headline or None, key_texts))


def check_and_build(con, path):
    """Validate one file; return (problems, plan) where plan holds everything to insert."""
    problems = []
    name = os.path.basename(path)
    head, sections = parse(path)
    for key in ("code", "title", "big_idea", "topic", "audience", "minutes", "passage", "version"):
        if not head.get(key):
            problems.append(f"{name}: missing '{key}:'")
    if problems:
        return problems, None
    topic = con.execute("SELECT id FROM subjects WHERE level = 'topic' AND name = ?", (head["topic"],)).fetchone()
    if not topic:
        problems.append(f"{name}: unknown Nave's topic {head['topic']!r}")
    also = []
    for t in [x.strip() for x in head.get("also", "").split(";") if x.strip()]:
        row = con.execute("SELECT id FROM subjects WHERE level = 'topic' AND name = ?", (t,)).fetchone()
        if row:
            also.append(row[0])
        else:
            problems.append(f"{name}: unknown Nave's topic in also: {t!r}")
    translation = head.get("translation", "KJV")
    if translation not in TRANSLATIONS:
        problems.append(f"{name}: unknown translation {translation}")
    tr_id = con.execute("SELECT id FROM works WHERE code = ?", (translation,)).fetchone()
    version = head["version"]
    tradition_id = issue_id = None
    if version.startswith("tradition:"):
        kind = "tradition"
        row = con.execute("SELECT id FROM traditions WHERE code = ? AND status = 'approved'",
                          (version.split(":", 1)[1],)).fetchone()
        if not row:
            problems.append(f"{name}: unknown or unapproved tradition in {version}")
        else:
            tradition_id = row[0]
    elif version in ("single", "all_views"):
        kind = version
    else:
        kind = None
        problems.append(f"{name}: version must be single, all_views or tradition:<code>")
    if head.get("issue"):
        row = con.execute("SELECT id FROM contested_issues WHERE code = ?", (head["issue"],)).fetchone()
        if not row:
            problems.append(f"{name}: unknown contested issue {head['issue']}")
        else:
            issue_id = row[0]
    if kind in ("all_views", "tradition") and not issue_id:
        problems.append(f"{name}: a {kind} version needs 'issue:'")
    if kind == "single" and topic and con.execute("SELECT contested FROM subjects WHERE id = ?", (topic[0],)).fetchone()[0]:
        problems.append(f"{name}: topic {head['topic']} is contested, so it needs all-views and tradition versions")

    main_refs = refs_of(head["passage"], problems, f"{name} passage")
    # Template order, and "Where Christians differ" only on contested lessons.
    seen = [s["kind"] for s in sections]
    for k in seen:
        if k not in ORDER:
            problems.append(f"{name}: unknown section '== {k}'")
    idx = [ORDER.index(k) for k in seen if k in ORDER]
    if idx != sorted(idx):
        problems.append(f"{name}: sections are out of the template's order: {seen}")
    for req in ("opening", "scripture", "background", "point", "questions", "application", "prayer"):
        if req not in seen:
            problems.append(f"{name}: missing section '== {req}'")
    if ("differ" in seen) != bool(issue_id):
        problems.append(f"{name}: 'Where Christians differ' must appear exactly when the lesson is on a contested point")
    if kind == "tradition":
        for s in sections:
            if s["kind"] == "differ":
                s["hidden"] = True   # hidden unless the user turns it on

    built = []
    for s in sections:
        verses = []
        for v in s["verses"]:
            verses += refs_of(v, problems, f"{name} {s['kind']} verses")
        quotes = []
        for eid, text in s["quotes"]:
            row = con.execute("SELECT body FROM entries WHERE id = ?", (eid,)).fetchone()
            if not row:
                problems.append(f"{name}: quote cites missing entry {eid}")
                continue
            if norm(text) not in norm(row[0]):
                problems.append(f"{name}: quote not found word for word in entry {eid}: {text[:70]!r}")
                continue
            author_id, credit = credit_for(con, eid)
            quotes.append((eid, author_id, text, credit))
        for sent, ans in s["blanks"]:
            if "____" not in sent or not ans:
                problems.append(f"{name}: a blank needs '____' and an answer: {sent[:60]!r}")
        if s["kind"] == "point" and not s["quotes"]:
            problems.append(f"{name}: teaching point '{s['heading']}' has no commentator quote")
        if s["kind"] == "point" and not s["verses"]:
            problems.append(f"{name}: teaching point '{s['heading']}' has no supporting verses")
        body = s["body"]
        if s["kind"] == "differ" and s["views"]:
            body = (body + "\n\n" if body else "") + "\n\n".join(f"@view:{v}" for v in s["views"])
        built.append(dict(s, body=body, verse_refs=verses, quote_rows=quotes))
    total = sum(s["minutes"] or 0 for s in sections)
    if head.get("minutes", "").isdigit() and total != int(head["minutes"]):
        problems.append(f"{name}: section timings add up to {total} minutes, not {head['minutes']}")
    n_points = seen.count("point")
    if not 2 <= n_points <= 4:
        problems.append(f"{name}: has {n_points} teaching points (the template expects about three)")
    plan = dict(head=head, kind=kind, tradition_id=tradition_id, issue_id=issue_id, topic_id=topic and topic[0],
                also=also, tr_id=tr_id and tr_id[0], main_refs=main_refs, sections=built,
                source=os.path.relpath(path, db.ROOT))
    return problems, plan


def insert(con, plan):
    h = plan["head"]
    now = db.now()
    old = con.execute("SELECT id, status, visibility, reviewed_at, review_note, created_at FROM lessons WHERE code = ?",
                      (h["code"],)).fetchone()
    status, visibility, reviewed_at, review_note, created = ("draft", "private", None, None, now)
    if old:
        status, visibility, reviewed_at, review_note, created = old[1:]
        for t in ("lesson_quotes", "lesson_blanks", "lesson_scripture", "lesson_questions", "lesson_topics"):
            con.execute(f"DELETE FROM {t} WHERE lesson_id = ?", (old[0],))
        con.execute("DELETE FROM lesson_sections WHERE lesson_id = ?", (old[0],))
        con.execute("DELETE FROM lessons WHERE id = ?", (old[0],))
    lid = con.execute("""INSERT INTO lessons(id, code, family_code, version_kind, tradition_id, contested_issue_id,
                         title, big_idea, topic_subject_id, audience, length_minutes, translation_work_id, status,
                         visibility, origin, generated_by, source_file, created_at, updated_at, reviewed_at,
                         review_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (old[0] if old else None, h["code"], h.get("family", h["code"]), plan["kind"],
                       plan["tradition_id"], plan["issue_id"], h["title"], h["big_idea"], plan["topic_id"],
                       h["audience"], int(h["minutes"]), plan["tr_id"], status, visibility, "batch", "ai",
                       plan["source"], created, now, reviewed_at, review_note)).lastrowid
    for sid in [plan["topic_id"]] + plan["also"]:
        con.execute("INSERT OR IGNORE INTO lesson_topics(lesson_id, subject_id) VALUES (?,?)", (lid, sid))
    for start, end, text in plan["main_refs"]:
        con.execute("""INSERT INTO lesson_scripture(lesson_id, role, start_verse_id, end_verse_id, ref_text)
                       VALUES (?,?,?,?,?)""", (lid, "main", start, end, format_ref(start, end)))
    q_pos = b_pos = 0
    for pos, s in enumerate(plan["sections"], start=1):
        sec = con.execute("""INSERT INTO lesson_sections(lesson_id, kind, position, heading, body, minutes,
                             teacher_note, default_hidden) VALUES (?,?,?,?,?,?,?,?)""",
                          (lid, KIND.get(s["kind"], s["kind"]), pos, s["heading"] or None, s["body"], s["minutes"],
                           s["teacher_note"], 1 if s["hidden"] else 0)).lastrowid
        for start, end, text in s["verse_refs"]:
            con.execute("""INSERT INTO lesson_scripture(lesson_id, section_id, role, start_verse_id, end_verse_id,
                           ref_text) VALUES (?,?,?,?,?,?)""", (lid, sec, "supporting", start, end, format_ref(start, end)))
        for eid, author_id, text, credit in s["quote_rows"]:
            con.execute("""INSERT INTO lesson_quotes(lesson_id, section_id, entry_id, author_id, quote_text, credit)
                           VALUES (?,?,?,?,?,?)""", (lid, sec, eid, author_id, text, credit))
        for sent, ans in s["blanks"]:
            b_pos += 1
            con.execute("INSERT INTO lesson_blanks(lesson_id, section_id, position, sentence, answer) VALUES (?,?,?,?,?)",
                        (lid, sec, b_pos, sent, ans))
        for q, a in s["questions"]:
            q_pos += 1
            con.execute("INSERT INTO lesson_questions(lesson_id, position, question, answer) VALUES (?,?,?,?)",
                        (lid, q_pos, q, a or None))
    return lid


def ensure_schema(con):
    existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    schema = open(os.path.join(db.ROOT, "schema.sql"), encoding="utf-8").read()
    for name in ("perspective_summaries", "lessons", "lesson_topics", "lesson_sections", "lesson_scripture",
                 "lesson_quotes", "lesson_blanks", "lesson_questions", "lesson_ratings", "lesson_fix_cycle",
                 "app_settings"):
        if name not in existing:
            start = schema.index(f"CREATE TABLE {name} ")
            con.execute(schema[start:schema.index("\n);", start) + 3])
    if "headline" not in {r[1] for r in con.execute("PRAGMA table_info(perspective_summaries)")}:
        con.execute("ALTER TABLE perspective_summaries ADD COLUMN headline TEXT")
    for m in re.finditer(r"CREATE INDEX (ix_lesson\w*) ON [^;]+;", schema):
        if m.group(1) not in existing:
            con.execute(m.group(0))


def main(argv):
    con = db.connect()
    ensure_schema(con)
    problems = []
    load_perspectives(con, problems)
    for key, value, note in SETTINGS:
        con.execute("INSERT INTO app_settings(key, value, note) VALUES (?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, note = excluded.note", (key, value, note))
    files = sorted(glob.glob(os.path.join(SOURCE_DIR, "*.txt")))
    loaded = 0
    codes = set()
    for path in files:
        p, plan = check_and_build(con, path)
        if plan and plan["head"]["code"] in codes:
            p.append(f"{os.path.basename(path)}: duplicate lesson code {plan['head']['code']}")
        if p:
            problems += p
            continue
        codes.add(plan["head"]["code"])
        if "--check" not in argv:
            insert(con, plan)
            loaded += 1
    if "--check" not in argv:
        con.commit()
    n = con.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    print(f"lesson files: {len(files)}; loaded: {loaded}; lessons in database: {n}; problems: {len(problems)}")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
