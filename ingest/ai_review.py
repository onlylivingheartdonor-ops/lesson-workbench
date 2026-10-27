"""Review of low-confidence subject links (the review list), in batches.

    python3 -m ingest.ai_review status            # how much of the review list is done
    python3 -m ingest.ai_review next 120          # print the next batch to review (most-used topics first)
    python3 -m ingest.ai_review record FILE       # record decisions from FILE (lines "<id> A|R|F <topic name>")
    python3 -m ingest.ai_review apply             # re-apply every recorded decision (run by build.py)
    python3 -m ingest.ai_review verify            # check that every recorded decision is in effect

Decisions are kept in review/ai_reviews.csv by stable keys (work code, entry
key, subject slug), so they survive rebuilds of the database.  In the
database:
  * accept  -> the link's review_status becomes 'ai_accepted'
  * reject  -> 'ai_rejected' (search no longer shows the link)
  * fix     -> the link is 'ai_rejected' and a corrected link to the right
               topic is added (method 'ai', method_detail 'ai_review_fix',
               review_status 'ai_accepted')
Links on the review list that have no recorded decision are set to
'hidden_unreviewed' (search does not show them); `next` still lists them,
most-used topics first, for a later review pass.
Every decision is also a row in link_reviews.  The reviewer is recorded as
"Claude (AI reviewer)": these are an AI model's judgements, not a person's.
"""

import csv
import os
import re
import sys
from collections import Counter

from library import db

CSV_PATH = os.path.join(db.ROOT, "review", "ai_reviews.csv")
FIELDS = ["work", "entry_key", "subject_slug", "decision", "fix_subject_slug", "reviewer", "reviewed_at", "batch",
          "notes", "entry_fingerprint"]
RESTORED = "ai_review_restored"
REVIEWER = "Claude (AI reviewer)"


def load():
    if not os.path.exists(CSV_PATH):
        return []
    return list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))


def save(rows):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def queue(con):
    """Links still waiting for review, most-used topics first."""
    usage = dict(con.execute("SELECT subject_id, COUNT(*) FROM entry_subjects GROUP BY subject_id"))
    rows = con.execute("""
        SELECT es.id, w.code, e.entry_key, s.slug, s.name, s.id, es.method, es.confidence, e.title, e.body,
               es.evidence, e.entry_type
        FROM review_queue rq JOIN entry_subjects es ON es.id = rq.entry_subject_id
        JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id JOIN subjects s ON s.id = es.subject_id
        WHERE es.review_status IN ('needs_review', 'hidden_unreviewed')""").fetchall()
    rows.sort(key=lambda r: (-usage.get(r[5], 0), r[4], -r[7]))
    return rows


def snippet(body, n):
    return " ".join(body.split()[:n])


def cmd_next(con, n):
    rows = queue(con)[:n]
    last_topic = None
    for r in rows:
        es_id, code, key, slug, sname, sid, method, conf, title, body, ev, etype = r
        if sname != last_topic:
            subs = [x[0] for x in con.execute("SELECT name FROM subjects WHERE parent_id=? ORDER BY id LIMIT 10", (sid,))]
            print(f"\n=== TOPIC: {sname}  [{'; '.join(subs)[:160]}]")
            last_topic = sname
        n_words = 26 if etype in ("commentary_note",) else 34
        print(f"{es_id} | {title[:70]} | {snippet(body, n_words)}")
    print(f"\n({len(rows)} shown; {len(queue(con))} waiting)")


def cmd_record(con, path):
    rows = load()
    done = {(r["work"], r["entry_key"], r["subject_slug"]) for r in rows}
    names = {}
    for name, slug in con.execute("SELECT name, slug FROM subjects WHERE level='topic'"):
        names.setdefault(name.lower(), slug)
    batch = os.path.basename(path)
    added, errors = 0, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s+([ARF])\b\s*(.*)$", line)
        if not m:
            errors.append(f"unreadable: {line}")
            continue
        es_id, dec, rest = int(m.group(1)), m.group(2), m.group(3).strip()
        row = con.execute("""SELECT w.code, e.entry_key, s.slug, e.body FROM entry_subjects es
                             JOIN entries e ON e.id=es.entry_id JOIN works w ON w.id=e.work_id
                             JOIN subjects s ON s.id=es.subject_id WHERE es.id=?""", (es_id,)).fetchone()
        if not row:
            errors.append(f"no link {es_id}")
            continue
        fix_slug = ""
        if dec == "F":
            fix_slug = names.get(rest.lower())
            if not fix_slug:
                errors.append(f"{es_id}: unknown topic '{rest}'")
                continue
        key = tuple(row[:3])
        if key in done:
            continue
        rows.append(dict(work=row[0], entry_key=row[1], subject_slug=row[2],
                         decision={"A": "accept", "R": "reject", "F": "fix"}[dec], fix_subject_slug=fix_slug,
                         reviewer=REVIEWER, reviewed_at=db.now(), batch=batch, notes="",
                         entry_fingerprint=db.entry_fingerprint(row[3])))
        done.add(key)
        added += 1
    save(rows)
    print(f"recorded {added} decisions from {batch}; {len(errors)} problems")
    for e in errors[:20]:
        print("  ", e)
    apply(con)


class EntryIndex:
    """Finds the entry a recorded decision is about. Usually its key is enough; but some works have
    several entries with the same key (a long introduction split into parts), and a re-ingest can rename
    an entry. The fingerprint (the entry's opening words, stored with the decision) settles both."""

    def __init__(self, con):
        self.by_key, self.by_print = {}, {}
        for eid, code, key, body in con.execute("SELECT e.id, w.code, e.entry_key, e.body FROM entries e "
                                                 "JOIN works w ON w.id=e.work_id"):
            fp = db.entry_fingerprint(body)
            self.by_key.setdefault((code, key), []).append((eid, fp))
            self.by_print.setdefault((code, fp), eid)

    def resolve(self, r):
        fp = r.get("entry_fingerprint")
        candidates = self.by_key.get((r["work"], r["entry_key"]), [])
        if len(candidates) == 1:
            return candidates[0][0]
        if candidates:
            same = [eid for eid, cfp in candidates if cfp == fp]
            # Shared key: the fingerprint picks the entry; without one, the last entry (as before).
            return same[0] if same else candidates[-1][0]
        return self.by_print.get((r["work"], fp)) if fp else None   # renamed by a re-ingest


def apply(con):
    """Put every recorded decision into effect. Decisions are permanent: if a re-ingest or re-run removed
    the link a decision was about, the link is re-created (accepted, or kept as rejected so the tagger can
    never bring it back as an unreviewed link)."""
    con.execute("CREATE TABLE IF NOT EXISTS link_reviews (id INTEGER PRIMARY KEY, entry_subject_id INTEGER NOT NULL "
                "REFERENCES entry_subjects(id), decision TEXT NOT NULL, new_subject_id INTEGER REFERENCES subjects(id), "
                "reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL, notes TEXT)")
    rows = load()
    entries = EntryIndex(con)
    slug_id = dict(con.execute("SELECT slug, id FROM subjects"))
    link_id = {(e, sub): i for i, e, sub in con.execute("SELECT id, entry_id, subject_id FROM entry_subjects")}
    con.execute("DELETE FROM entry_subjects WHERE method_detail='ai_review_fix'")
    con.execute("DELETE FROM link_reviews")
    orphaned, restored, fingerprints_added = 0, Counter(), 0
    counts = Counter()
    for r in rows:
        dec = r["decision"]
        entry_id = entries.resolve(r)
        es_id = link_id.get((entry_id, slug_id.get(r["subject_slug"])))
        subject_id = slug_id.get(r["subject_slug"])
        if es_id is None:
            if entry_id is None or subject_id is None:
                orphaned += 1          # the entry or topic itself no longer exists
                continue
            es_id = con.execute(
                "INSERT INTO entry_subjects(entry_id, subject_id, method, method_detail, confidence, evidence, "
                "review_status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (entry_id, subject_id, "ai", RESTORED, 0.9 if dec == "accept" else 0.0,
                 f"Re-created from {r['reviewer']}'s decision ({dec}) of {r['reviewed_at'][:10]}",
                 "ai_accepted" if dec == "accept" else "ai_rejected", r["reviewed_at"])).lastrowid
            restored[dec] += 1
        if not r.get("entry_fingerprint"):
            body = con.execute("SELECT e.body FROM entry_subjects es JOIN entries e ON e.id=es.entry_id "
                               "WHERE es.id=?", (es_id,)).fetchone()[0]
            r["entry_fingerprint"] = db.entry_fingerprint(body)
            fingerprints_added += 1
        new_sid = slug_id.get(r["fix_subject_slug"]) if dec == "fix" else None
        con.execute("UPDATE entry_subjects SET review_status=? WHERE id=?",
                    ("ai_accepted" if dec == "accept" else "ai_rejected", es_id))
        con.execute("DELETE FROM review_queue WHERE entry_subject_id=?", (es_id,))
        con.execute("INSERT INTO link_reviews(entry_subject_id, decision, new_subject_id, reviewer, reviewed_at, notes) "
                    "VALUES (?,?,?,?,?,?)", (es_id, dec, new_sid, r["reviewer"], r["reviewed_at"], r.get("notes")))
        if dec == "fix" and new_sid:
            entry_id = con.execute("SELECT entry_id FROM entry_subjects WHERE id=?", (es_id,)).fetchone()[0]
            con.execute("DELETE FROM entry_subjects WHERE entry_id=? AND subject_id=? AND NOT " + db.REVIEWED,
                        (entry_id, new_sid))
            con.execute("INSERT OR IGNORE INTO entry_subjects(entry_id, subject_id, method, method_detail, confidence, "
                        "evidence, review_status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (entry_id, new_sid, "ai", "ai_review_fix", 0.9,
                         f"Corrected by {r['reviewer']} from '{r['subject_slug']}'", "ai_accepted", r["reviewed_at"]))
        counts[dec] += 1
    if fingerprints_added:
        save(rows)
    # Dave's decision (second report): the review covers the most-used topics only; every
    # low-confidence link still unreviewed is hidden from search, kept for a later pass.
    hidden = con.execute("UPDATE entry_subjects SET review_status='hidden_unreviewed' "
                         "WHERE review_status='needs_review'").rowcount
    con.commit()
    print(f"applied {sum(counts.values())} review decisions {dict(counts)}; re-created {sum(restored.values())} "
          f"links that a re-run or re-ingest had removed {dict(restored)}; {orphaned} decisions whose entry no "
          f"longer exists; {hidden} unreviewed low-confidence links hidden")
    return dict(counts=dict(counts), restored=dict(restored), orphaned=orphaned, hidden=hidden)


def verify(con):
    """Check that every recorded decision is in effect. Returns a list of problems (empty = all good)."""
    problems = []
    entries = EntryIndex(con)
    slug_id = dict(con.execute("SELECT slug, id FROM subjects"))
    status = {(e, sub): st for e, sub, st in con.execute("SELECT entry_id, subject_id, review_status "
                                                          "FROM entry_subjects")}
    for r in load():
        entry_id = entries.resolve(r)
        if entry_id is None:
            continue               # orphaned: the entry itself is gone (reported by apply)
        k = (r["work"], r["entry_key"], r["subject_slug"])
        want = "ai_accepted" if r["decision"] == "accept" else "ai_rejected"
        have = status.get((entry_id, slug_id.get(r["subject_slug"])), "missing")
        if have != want:
            problems.append(f"{k}: decision {r['decision']} but link is {have}")
        if r["decision"] == "fix" and status.get((entry_id, slug_id.get(r["fix_subject_slug"]))) != "ai_accepted":
            problems.append(f"{k}: corrected link to {r['fix_subject_slug']} is missing")
    return problems


def status(con):
    rows = load()
    c = Counter(r["decision"] for r in rows)
    print(f"reviewed {len(rows)} ({dict(c)}); still waiting {len(queue(con))}")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    con = db.connect()
    cmd = argv[0] if argv else "status"
    if cmd == "next":
        cmd_next(con, int(argv[1]) if len(argv) > 1 else 100)
    elif cmd == "record":
        cmd_record(con, argv[1])
    elif cmd == "apply":
        return apply(con)
    elif cmd == "verify":
        problems = verify(con)
        print(f"{len(problems)} decisions not in effect")
        for p in problems[:20]:
            print("  ", p)
        return 1 if problems else 0
    else:
        status(con)


if __name__ == "__main__":
    main()
