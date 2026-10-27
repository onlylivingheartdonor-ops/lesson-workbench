"""Show the library material behind a lesson: what the commentaries say on a passage, and the
sermons, expositions and devotional works that treat it or its topic.

    python3 tools/lesson_sources.py "Matthew 18:21-35"                 # commentary on the passage
    python3 tools/lesson_sources.py "Matthew 18:21-35" --topic Forgiveness --words 220
    python3 tools/lesson_sources.py --entry 12345                      # one entry in full

Used when writing lessons: every commentator quote in a lesson is copied from an entry shown here,
and the lesson loader checks it word for word.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library import db  # noqa: E402
from library.scripture import format_ref, parse_free_refs  # noqa: E402

HIDDEN = "('rejected', 'ai_rejected', 'hidden_unreviewed', 'needs_review')"


def author_of(con, entry_id):
    rows = con.execute("""SELECT a.name FROM entry_authors ea JOIN authors a ON a.id = ea.author_id
                          WHERE ea.entry_id = ?""", (entry_id,)).fetchall()
    return " & ".join(r[0] for r in rows)


def show(con, rows, words):
    for eid, code, title, body in rows:
        text = " ".join(body.split())
        cut = " ".join(text.split()[:words])
        print(f"\n[{eid}] {code} | {author_of(con, eid)} | {title}\n    {cut}{' ...' if len(text.split()) > words else ''}")


def main(argv):
    con = db.connect()
    words = int(argv[argv.index("--words") + 1]) if "--words" in argv else 160
    if "--entry" in argv:
        eid = int(argv[argv.index("--entry") + 1])
        code, title, body = con.execute("""SELECT w.code, e.title, e.body FROM entries e JOIN works w ON w.id = e.work_id
                                           WHERE e.id = ?""", (eid,)).fetchone()
        print(f"[{eid}] {code} | {author_of(con, eid)} | {title}\n\n{body}")
        return 0
    refs = parse_free_refs(argv[0]) if argv and not argv[0].startswith("--") else []
    for start, end, _ in refs:
        print(f"===== Commentary on {format_ref(start, end)}")
        rows = con.execute("""
            SELECT DISTINCT e.id, w.code, e.title, e.body FROM entry_scripture es
            JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
            JOIN reference_types r ON r.id = w.reference_type_id
            WHERE es.relation = 'about' AND es.start_verse_id <= ? AND es.end_verse_id >= ?
              AND r.code IN ('commentary') AND e.entry_type != 'book_intro'
            ORDER BY w.code, e.sort_order""", (end, start)).fetchall()
        show(con, rows, words)
        print(f"\n===== Sermons, expositions and devotional works citing {format_ref(start, end)}")
        rows = con.execute("""
            SELECT e.id, w.code, e.title, e.body FROM entry_scripture es
            JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
            JOIN reference_types r ON r.id = w.reference_type_id
            WHERE es.start_verse_id <= ? AND es.end_verse_id >= ?
              AND r.code IN ('sermon', 'devotional', 'doctrinal')
            GROUP BY e.id ORDER BY COUNT(*) DESC LIMIT 12""", (end, start)).fetchall()
        show(con, rows, words)
    if "--topic" in argv:
        topic = argv[argv.index("--topic") + 1]
        print(f"\n===== Sermons and devotional entries tagged '{topic}'")
        rows = con.execute(f"""
            SELECT e.id, w.code, e.title, e.body FROM entry_subjects es
            JOIN subjects s ON s.id = es.subject_id JOIN entries e ON e.id = es.entry_id
            JOIN works w ON w.id = e.work_id JOIN reference_types r ON r.id = w.reference_type_id
            WHERE s.level = 'topic' AND s.name = ? AND es.review_status NOT IN {HIDDEN}
              AND r.code IN ('sermon', 'devotional', 'doctrinal')
            ORDER BY es.confidence DESC LIMIT 12""", (topic,)).fetchall()
        show(con, rows, words)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
