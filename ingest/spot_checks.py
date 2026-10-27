"""Tagging spot checks.

    python3 -m ingest.spot_checks sample [seed]  # write review/spot_check_sample.csv (blank verdicts)
    python3 -m ingest.spot_checks import   # load review/spot_checks.csv, record verdicts, report accuracy
    python3 -m ingest.spot_checks queue    # export the low-confidence review list to review/review_queue.csv

The sample is stratified: for every work and linking method it takes links
from both above and below the review threshold, so the measured accuracy
says something about each confidence band.  Verdicts are stored in
review/spot_checks.csv by stable keys (work code, entry key, subject slug)
so they survive rebuilds of the database.

Verdicts: 'correct'  - a teacher looking up this subject would want this entry
          'partly'   - related but marginal (counted as half right)
          'wrong'    - not about this subject
"""

import csv
import json
import os
import random
import sys
from collections import defaultdict

from library import db

REVIEW_DIR = os.path.join(db.ROOT, "review")
SAMPLE_CSV = os.path.join(REVIEW_DIR, "spot_check_sample.csv")
VERDICTS_CSV = os.path.join(REVIEW_DIR, "spot_checks.csv")
QUEUE_CSV = os.path.join(REVIEW_DIR, "review_queue.csv")
REF_SAMPLE_CSV = os.path.join(REVIEW_DIR, "scripture_link_sample.csv")
REF_VERDICTS_CSV = os.path.join(REVIEW_DIR, "scripture_link_checks.csv")
FIELDS = ["work", "entry_key", "subject_slug", "method", "confidence", "band", "entry_title", "entry_text",
          "subject", "subject_detail", "evidence", "verdict", "notes"]

LINK_QUERY = """
SELECT es.id, w.code, e.entry_key, s.slug, es.method, es.confidence, e.title, e.body, s.name, es.evidence,
       rt.code, e.entry_type, s.id
FROM entry_subjects es JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
JOIN reference_types rt ON rt.id = w.reference_type_id JOIN subjects s ON s.id = es.subject_id
WHERE es.method_detail != 'nave_topic_entry'
"""


def group_of(code, rtype):
    if rtype in ("sermon", "devotional"):
        return code.split("-")[0]           # one group per author (BOUNDS, RYLE, MOODY, SPURGEON)
    return code


def sample(con, seed=20261026):
    rnd = random.Random(seed)
    buckets = defaultdict(list)
    for row in con.execute(LINK_QUERY):
        _id, code, key, slug, method, conf, title, body, sname, ev, rtype, etype, sid = row
        threshold = 0.55 if method == "ai" else 0.45
        band = "high" if conf >= max(threshold, 0.6) else "low"
        buckets[(group_of(code, rtype), method, band)].append(row)
    plan = {}
    for (grp, method, band) in buckets:
        n = 6 if method == "structural" else 5
        if grp in ("BOUNDS", "RYLE", "MOODY", "SPURGEON"):
            n = 4
        plan[(grp, method, band)] = n
    out = []
    for k in sorted(buckets):
        rows = buckets[k]
        for row in rnd.sample(rows, min(plan[k], len(rows))):
            _id, code, key, slug, method, conf, title, body, sname, ev, rtype, etype, sid = row
            subs = [r[0] for r in con.execute("SELECT name FROM subjects WHERE parent_id=? ORDER BY id LIMIT 8", (sid,))]
            out.append(dict(work=code, entry_key=key, subject_slug=slug, method=method, confidence=conf, band=k[2],
                            entry_title=title, entry_text=" ".join(body.split()[:90]), subject=sname,
                            subject_detail="; ".join(subs), evidence=ev, verdict="", notes=""))
    os.makedirs(REVIEW_DIR, exist_ok=True)
    with open(SAMPLE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} links to {SAMPLE_CSV}")

    # Scripture-link sample: references found in plain text and by quotation matching.
    refs = []
    for method in ("text_parse", "quotation_match"):
        rows = con.execute("""SELECT w.code, e.entry_key, es.start_verse_id, es.end_verse_id, es.ref_text, e.body
                              FROM entry_scripture es JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
                              WHERE es.method = ?""", (method,)).fetchall()
        for code, key, s, e, txt, body in rnd.sample(rows, min(25, len(rows))):
            verse = " ".join(r[0] for r in con.execute(
                "SELECT b.text FROM bible_text b JOIN works w ON w.id=b.work_id WHERE w.code='KJV' AND "
                "b.verse_id BETWEEN ? AND ? LIMIT 2", (s, e)))
            pos = body.find((txt or "").replace("quotes: ", "").split(" ...")[0][:20])
            from library.scripture import format_ref
            refs.append(dict(method=method, work=code, entry_key=key, reference=format_ref(s, e), found_text=txt,
                             context=" ".join(body[max(0, pos - 150):pos + 150].split()) if pos >= 0 else "",
                             kjv_text=verse[:300], verdict="", notes=""))
    with open(REF_SAMPLE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(refs[0].keys()))
        w.writeheader()
        w.writerows(refs)
    print(f"wrote {len(refs)} scripture links to {REF_SAMPLE_CSV}")


def score(verdicts):
    pts = {"correct": 1.0, "partly": 0.5, "wrong": 0.0}
    vals = [pts[v] for v in verdicts if v in pts]
    return (round(sum(vals) / len(vals), 3), len(vals)) if vals else (None, 0)


def do_import(con):
    if not os.path.exists(VERDICTS_CSV):
        print(f"no verdicts file yet ({VERDICTS_CSV}); nothing imported")
        return {}
    con.execute("DELETE FROM spot_checks")
    index = {}
    for row in con.execute("""SELECT es.id, w.code, e.entry_key, s.slug FROM entry_subjects es
                              JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
                              JOIN subjects s ON s.id = es.subject_id"""):
        index[(row[1], row[2], row[3])] = row[0]
    groups = defaultdict(list)
    missing = restored = 0
    checker = "Claude (AI reviewer), 2026-10-26"
    for r in csv.DictReader(open(VERDICTS_CSV, encoding="utf-8")):
        v = r["verdict"].strip().lower()
        if v not in ("correct", "partly", "wrong"):
            continue
        es_id = index.get((r["work"], r["entry_key"], r["subject_slug"]))
        rtype = con.execute("SELECT rt.code FROM works w JOIN reference_types rt ON rt.id=w.reference_type_id "
                            "WHERE w.code=?", (r["work"],)).fetchone()
        grp = group_of(r["work"], rtype[0] if rtype else "")
        groups[(grp, r["method"], r["band"])].append(v)
        groups[(grp, r["method"], "all")].append(v)
        groups[("ALL", r["method"], r["band"])].append(v)
        groups[("ALL", r["method"], "all")].append(v)
        if es_id is None:
            # Spot-check verdicts are permanent: re-create a checked link that a re-run or re-ingest removed.
            entry = con.execute("SELECT e.id FROM entries e JOIN works w ON w.id=e.work_id "
                                "WHERE w.code=? AND e.entry_key=?", (r["work"], r["entry_key"])).fetchone()
            subject = con.execute("SELECT id FROM subjects WHERE slug=?", (r["subject_slug"],)).fetchone()
            if not entry or not subject:
                missing += 1
                continue
            es_id = con.execute(
                "INSERT INTO entry_subjects(entry_id, subject_id, method, method_detail, confidence, evidence, "
                "review_status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (entry[0], subject[0], r["method"], "spot_check_restored", float(r["confidence"] or 0),
                 "Re-created from a spot-check verdict", "rejected" if v == "wrong" else "accepted",
                 db.now())).lastrowid
            restored += 1
        con.execute("INSERT INTO spot_checks(entry_subject_id, verdict, checker, checked_at, notes) VALUES (?,?,?,?,?)",
                    (es_id, v, r.get("checker") or checker, db.now(), r.get("notes")))
        # A checked link is no longer waiting for review.
        con.execute("UPDATE entry_subjects SET review_status=? WHERE id=?",
                    ("rejected" if v == "wrong" else "accepted", es_id))
        con.execute("DELETE FROM review_queue WHERE entry_subject_id=?", (es_id,))
    acc = {f"{g}|{m}|{b}": dict(zip(("accuracy", "n"), score(vs))) for (g, m, b), vs in sorted(groups.items())}
    ref_acc = {}
    if os.path.exists(REF_VERDICTS_CSV):
        byref = defaultdict(list)
        for r in csv.DictReader(open(REF_VERDICTS_CSV, encoding="utf-8")):
            byref[r["method"]].append(r["verdict"].strip().lower())
        ref_acc = {m: dict(zip(("accuracy", "n"), score(vs))) for m, vs in byref.items()}
    out = dict(link_accuracy=acc, scripture_link_accuracy=ref_acc, verdicts_not_matched_to_current_links=missing,
               checked_links_recreated=restored)
    db.log_ingest(con, "ingest/spot_checks.py", None, db.now(), out)
    con.commit()
    with open(os.path.join(REVIEW_DIR, "accuracy.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return out


def export_queue(con):
    os.makedirs(REVIEW_DIR, exist_ok=True)
    rows = con.execute("""SELECT w.code, e.title, s.name, es.method, es.confidence, es.evidence, rq.reason
                          FROM review_queue rq JOIN entry_subjects es ON es.id = rq.entry_subject_id
                          JOIN entries e ON e.id = es.entry_id JOIN works w ON w.id = e.work_id
                          JOIN subjects s ON s.id = es.subject_id ORDER BY w.code, es.confidence""").fetchall()
    with open(QUEUE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["work", "entry", "subject", "method", "confidence", "evidence", "reason"])
        w.writerows(rows)
    print(f"wrote {len(rows)} unreviewed (hidden) low-confidence links to {QUEUE_CSV}")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    con = db.connect()
    cmd = argv[0] if argv else "import"
    if cmd == "sample":
        sample(con, seed=int(argv[1]) if len(argv) > 1 else 20261026)
    elif cmd == "queue":
        export_queue(con)
    else:
        out = do_import(con)
        export_queue(con)
        return out


if __name__ == "__main__":
    main()
