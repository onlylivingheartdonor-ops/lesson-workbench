"""Command-line search test for the library.

    python3 search.py forgiveness            # subject search
    python3 search.py --verse "Matthew 6:14"  # everything linked to a verse
    python3 search.py prayer --more           # longer lists

A subject search shows: the matching Nave's subject(s), linked verses (KJV
text), commentary from each author, dictionary and encyclopedia articles,
sermons and devotional works, the original-language words most typical of the subject's verses, and
related subjects.
"""

import argparse
import math
import os
import re
import sqlite3
import sys
import textwrap

from library.db import DB_PATH
from library.scripture import format_ref, parse_free_refs, split_vid

WIDTH = 100


def wrap(text, indent="      ", width=WIDTH):
    return textwrap.fill(" ".join(text.split()), width=width, initial_indent=indent, subsequent_indent=indent)


def snippet(body, n=40):
    words = body.split()
    return " ".join(words[:n]) + (" ..." if len(words) > n else "")


def header(title):
    print()
    print(title)
    print("-" * len(title))


def find_subjects(con, query):
    q = query.strip().lower()
    rows = con.execute("SELECT id, name, level, parent_id FROM subjects WHERE level IN ('topic', 'category') AND "
                       "lower(name) = ?", (q,)).fetchall()
    others = con.execute("SELECT id, name, level, parent_id FROM subjects WHERE level IN ('topic', 'category') AND "
                         "(lower(name) LIKE ? OR lower(name) LIKE ? OR lower(name) LIKE ?) AND lower(name) != ? "
                         "ORDER BY length(name) LIMIT 12",
                         (q + "%", "%, " + q + "%", "% " + q + "%", q)).fetchall()
    if not rows and others:
        rows, others = others[:1], others[1:]
    return rows, others


def topic_verse_rows(con, tid):
    return con.execute("""SELECT ss.start_verse_id, ss.end_verse_id, ss.note, s.name, s.level
                          FROM subject_scripture ss JOIN subjects s ON s.id = ss.subject_id
                          WHERE s.id = ? OR s.parent_id = ? ORDER BY s.level DESC, s.id, ss.position""",
                       (tid, tid)).fetchall()


def kjv(con, s, e):
    rows = con.execute("SELECT b.text FROM bible_text b JOIN works w ON w.id = b.work_id WHERE w.code='KJV' "
                       "AND b.verse_id BETWEEN ? AND ? ORDER BY b.verse_id LIMIT 4", (s, e)).fetchall()
    t = " ".join(r[0] for r in rows)
    return t if len(rows) < 4 else t + " ..."


def subject_search(con, query, more):
    main, others = find_subjects(con, query)
    if not main:
        print(f"No subject named '{query}'. Trying a text search of entry titles instead.")
        for r in con.execute("SELECT w.short_title, e.title FROM entries e JOIN works w ON w.id=e.work_id "
                             "WHERE lower(e.title) LIKE ? LIMIT 20", ("%" + query.lower() + "%",)):
            print("  ", r[0], "-", r[1])
        return 1
    tid, name, level, _ = main[0]
    print("=" * WIDTH)
    print(f"SUBJECT: {name}   (Nave's topic; id {tid})")
    subs = [r[0] for r in con.execute("SELECT name FROM subjects WHERE parent_id=? ORDER BY id", (tid,))]
    if subs:
        print(wrap("Sub-headings: " + "; ".join(subs), indent="  "))
    if others:
        print(wrap("Other matching subjects: " + "; ".join(o[1] for o in others), indent="  "))
    print("=" * WIDTH)

    # Verses
    vrows = topic_verse_rows(con, tid)
    header(f"Linked verses (Nave's) - {len(vrows)} references")
    shown_notes = set()
    for s, e, note, sname, lvl in vrows[: (40 if more else 12)]:
        label = f"[{sname}] " if lvl == "subtopic" else ""
        if note and note not in shown_notes and note.lower() != sname.lower():
            label += f"{note} "
            shown_notes.add(note)
        print(f"  {format_ref(s, e):<26} {label}")
        print(wrap(kjv(con, s, e), indent="      "))

    # Commentary
    rows = con.execute("""SELECT w.code, w.short_title, e.title, e.body, es.method, es.confidence, es.review_status
                          FROM entry_subjects es JOIN entries e ON e.id = es.entry_id
                          JOIN works w ON w.id = e.work_id JOIN reference_types rt ON rt.id = w.reference_type_id
                          WHERE es.subject_id = ? AND rt.code = 'commentary' AND es.review_status NOT IN ('rejected', 'ai_rejected')
                          ORDER BY es.confidence DESC, e.word_count""", (tid,)).fetchall()
    per = {}
    for r in rows:
        per.setdefault(r[0], []).append(r)
    header(f"Commentary - {len(rows)} linked notes from {len(per)} authors")
    for code, lst in per.items():
        print(f"  {lst[0][1]}  ({len(lst)} notes)")
        for _, _, title, body, method, conf, status in lst[: (4 if more else 2)]:
            flag = {"needs_review": "; awaiting review", "ai_accepted": "; AI-reviewed"}.get(status, "")
            print(f"    - {title}   [{method}, confidence {conf:.2f}{flag}]")
            print(wrap(snippet(body), indent="        "))

    # Dictionaries / encyclopedia
    rows = con.execute("""SELECT w.short_title, e.title, e.body, es.method, es.confidence, es.review_status
                          FROM entry_subjects es JOIN entries e ON e.id = es.entry_id
                          JOIN works w ON w.id = e.work_id JOIN reference_types rt ON rt.id = w.reference_type_id
                          WHERE es.subject_id = ? AND rt.code IN ('dictionary', 'encyclopedia')
                          AND es.review_status NOT IN ('rejected', 'ai_rejected')
                          ORDER BY es.confidence DESC LIMIT ?""", (tid, 20 if more else 8)).fetchall()
    header(f"Dictionary and encyclopedia articles - {len(rows)} shown")
    for wt, title, body, method, conf, status in rows:
        flag = {"needs_review": "; low confidence, awaiting review", "ai_accepted": "; AI-reviewed"}.get(status, "")
        print(f"  {wt}: {title}   [{method}, confidence {conf:.2f}{flag}]")
        print(wrap(snippet(body, 30), indent="      "))

    # Sermons and devotional works
    rows = con.execute("""SELECT w.short_title, e.title, e.body, es.method, es.confidence, es.review_status
                          FROM entry_subjects es JOIN entries e ON e.id = es.entry_id
                          JOIN works w ON w.id = e.work_id JOIN reference_types rt ON rt.id = w.reference_type_id
                          WHERE es.subject_id = ? AND rt.code IN ('sermon', 'devotional')
                          AND es.review_status NOT IN ('rejected', 'ai_rejected')
                          ORDER BY es.confidence DESC LIMIT ?""", (tid, 20 if more else 8)).fetchall()
    header(f"Sermons and devotional works - {len(rows)} shown")
    for wt, title, body, method, conf, status in rows:
        flag = {"needs_review": "; low confidence, awaiting review", "ai_accepted": "; AI-reviewed"}.get(status, "")
        print(f"  {wt}: {title}   [{method}, confidence {conf:.2f}{flag}]")
        print(wrap(snippet(body, 30), indent="      "))

    # Original-language words
    verse_ids = set()
    for s, e, *_ in vrows:
        if e - s < 50:
            verse_ids.update(range(s, e + 1))
    if verse_ids:
        con.execute("CREATE TEMP TABLE IF NOT EXISTS tv(v INTEGER PRIMARY KEY)")
        con.execute("DELETE FROM tv")
        con.executemany("INSERT OR IGNORE INTO tv VALUES (?)", [(v,) for v in verse_ids])
        total = con.execute("SELECT COUNT(DISTINCT verse_id) FROM verse_words").fetchone()[0]
        rows = con.execute("""SELECT vw.strongs, COUNT(DISTINCT vw.verse_id) AS n,
                                     (SELECT COUNT(DISTINCT verse_id) FROM verse_words x WHERE x.strongs = vw.strongs) AS df,
                                     st.transliteration, st.lemma, st.kjv_usage
                              FROM verse_words vw JOIN tv ON tv.v = vw.verse_id
                              LEFT JOIN strongs st ON st.number = vw.strongs
                              GROUP BY vw.strongs HAVING n >= 2""").fetchall()
        # Weight by how distinctive the word is, so "and"/"he" do not crowd out "forgive".
        scored = sorted(rows, key=lambda r: -(r[1] * math.log(total / r[2]) ** 2))[: (10 if more else 6)]
        header("Original-language words typical of these verses (Strong's)")
        for num, n, df, tr, lemma, usage in scored:
            print(f"  {num:<7} {tr or '':<14} {lemma or '':<12} in {n} of these verses; KJV: {(usage or '')[:60]}")

    # Related subjects
    rows = con.execute("""SELECT r.relation, s.name, r.score, r.evidence_count FROM subject_relations r
                          JOIN subjects s ON s.id = r.related_subject_id WHERE r.subject_id = ?
                          ORDER BY CASE r.relation WHEN 'see_also' THEN 0 WHEN 'co_occurrence' THEN 1 ELSE 2 END,
                                   r.score DESC""", (tid,)).fetchall()
    header("Related subjects")
    labels = {"see_also": "Nave's 'See also'", "co_occurrence": "Discussed together in commentaries/dictionaries",
              "shared_verses": "Share many verses"}
    for rel in ("see_also", "co_occurrence", "shared_verses"):
        names = [f"{r[1]} ({r[3]})" if rel != "see_also" else r[1] for r in rows if r[0] == rel][: (12 if more else 8)]
        if names:
            print(wrap(f"{labels[rel]}: " + "; ".join(names), indent="  "))
    print()
    return 0


def verse_search(con, ref, more):
    refs = parse_free_refs(ref)
    if not refs:
        print(f"Could not read '{ref}' as a scripture reference.")
        return 1
    s, e, _ = refs[0]
    if split_vid(s)[2] == 0:
        s += 1
    print("=" * WIDTH)
    print(f"PASSAGE: {format_ref(s, e)}")
    print("=" * WIDTH)
    for code, text in con.execute("SELECT w.code, group_concat(b.text, ' ') FROM bible_text b JOIN works w "
                                  "ON w.id = b.work_id WHERE b.verse_id BETWEEN ? AND ? GROUP BY w.code "
                                  "ORDER BY w.id", (s, e)):
        print(f"  {code}:")
        print(wrap(text))
    header("Commentary on this passage")
    for wt, title, body in con.execute("""SELECT w.short_title, e.title, e.body FROM entry_scripture es
            JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
            WHERE es.relation = 'about' AND es.start_verse_id <= ? AND es.end_verse_id >= ?
            AND e.entry_type = 'commentary_note' ORDER BY w.id""", (e, s)):
        print(f"  {title}")
        print(wrap(snippet(body, 45), indent="      "))
    header("Cross-references (Treasury of Scripture Knowledge)")
    rows = con.execute("SELECT keyword, to_start_verse_id, to_end_verse_id FROM cross_references "
                       "WHERE from_verse_id BETWEEN ? AND ? ORDER BY position", (s, e)).fetchall()
    print(wrap("; ".join(format_ref(a, b) + (f" ({k})" if k else "") for k, a, b in rows[: (60 if more else 25)]),
               indent="  "))
    header("Original words (KJV with Strong's numbers)")
    for v, word, num, tr, usage in con.execute("""SELECT vw.verse_id, vw.word, vw.strongs, st.transliteration, st.definition
            FROM verse_words vw LEFT JOIN strongs st ON st.number = vw.strongs
            WHERE vw.verse_id BETWEEN ? AND ? ORDER BY vw.verse_id, vw.position""", (s, e)):
        print(f"  {word:<14} {num:<7} {tr or '':<14} {(usage or '')[:60]}")
    header("Subjects that list this passage (Nave's)")
    names = [r[0] for r in con.execute("""SELECT DISTINCT COALESCE(p.name || ' > ' || s.name, s.name)
            FROM subject_scripture ss JOIN subjects s ON s.id = ss.subject_id LEFT JOIN subjects p ON p.id = s.parent_id
            WHERE ss.start_verse_id <= ? AND ss.end_verse_id >= ?""", (e, s))]
    print(wrap("; ".join(names), indent="  "))
    print()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="subject to search for, e.g. forgiveness")
    ap.add_argument("--verse", help="look up a passage instead, e.g. 'John 3:16'")
    ap.add_argument("--more", action="store_true", help="show longer lists")
    ap.add_argument("--db", default=DB_PATH)
    args = ap.parse_args(argv)
    if not os.path.exists(args.db):
        print(f"Database not found at {args.db}. Run: python3 tools/restore_db.py  (or python3 build.py)")
        return 2
    con = sqlite3.connect(args.db)
    if args.verse:
        return verse_search(con, args.verse, args.more)
    if not args.query:
        ap.print_help()
        return 2
    return subject_search(con, args.query, args.more)


if __name__ == "__main__":
    sys.exit(main())
