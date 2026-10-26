"""Ingest the Treasury of Scripture Knowledge (CrossWire 'TSK' module) as
verse-to-verse cross-references.

Each TSK verse note is a series of key words from the verse ("without.",
"Spirit.") each followed by a list of references.  Lists use TSK's
shorthand: a reference with no book name ("8:22") is in the same book as
the verse being annotated, and bare verse numbers ("8,13,19") are in the
same chapter.  The chapter outlines that open each chapter (which point
only at verses of the same chapter) are not cross-references and are
skipped.

Run:  python3 -m ingest.tsk
"""

import html
import re

from library import db
from library.crosswire import MODULE_PAGE, edition, get_module, license_evidence
from library.markup import parse_ref_list
from library.scripture import split_vid

MOD = "TSK"
CODE = "TSK"
_PIECE = re.compile(r"<scripRef(\s[^>]*)?>(.*?)</scripRef>|<br\s*/>|([^<]+)", re.S)


def main():
    started = db.now()
    fetched, conf, module = get_module(MOD)
    con = db.connect()
    wid = db.upsert_work(
        con, CODE, "The Treasury of Scripture Knowledge", "cross_reference",
        [("R. A. Torrey", "editor", dict(sort_name="Torrey, Reuben Archer", born="1856", died="1928",
          description="American evangelist and Bible teacher; edited the expanded edition of the Treasury "
                      "with an introduction (c. 1880s-1890s).")),
         ("John Canne", "contributor", dict(sort_name="Canne, John", born="c. 1590", died="1667",
          description="English Puritan whose marginal references form the core of the Treasury."))],
        "Public Domain", short_title="TSK", original_date="c. 1830s (Bagster); expanded c. 1880s",
        edition=edition(MOD, conf), source_name="CrossWire Bible Society", source_url=MODULE_PAGE + MOD,
        license_evidence=license_evidence(MOD, conf), coverage="Whole Bible; about 500,000 references",
        known_issues="Torrey/Canne credited as principal compilers; the module itself credits 'Canne, Browne, "
                     "Blayney, Scott, and others'.",
        ingest_script="ingest/tsk.py")
    db.add_provenance(con, wid, fetched)

    rows, pos = [], 0
    notes = 0
    unparsed = 0
    for start, end, raw in module.iter_entries():
        b, c, v = split_vid(start)
        if v == 0:
            continue
        notes += 1
        text = raw.decode("utf-8", errors="replace")
        keyword = None
        for m in _PIECE.finditer(text):
            attrs, inner, plain = m.group(1), m.group(2), m.group(3)
            if plain is not None:
                p = html.unescape(plain).strip()
                if p:
                    keyword = p.rstrip(".").strip()[:120]
                continue
            if inner is None:
                continue
            if attrs and "passage=" in attrs:
                continue  # chapter outline entry
            refs, _, _ = parse_ref_list(html.unescape(re.sub(r"<[^>]+>", "", inner)), b, c)
            if not refs:
                unparsed += 1
            for s, e in refs:
                if s == start and e == start:
                    continue
                pos += 1
                rows.append((start, s, e, keyword, wid, pos))
        if len(rows) > 50000:
            con.executemany("INSERT INTO cross_references(from_verse_id, to_start_verse_id, to_end_verse_id, "
                            "keyword, source_work_id, position) VALUES (?,?,?,?,?,?)", rows)
            rows = []
    con.executemany("INSERT INTO cross_references(from_verse_id, to_start_verse_id, to_end_verse_id, keyword, "
                    "source_work_id, position) VALUES (?,?,?,?,?,?)", rows)
    total = con.execute("SELECT COUNT(*) FROM cross_references WHERE source_work_id=?", (wid,)).fetchone()[0]
    verses = con.execute("SELECT COUNT(DISTINCT from_verse_id) FROM cross_references WHERE source_work_id=?",
                         (wid,)).fetchone()[0]
    out = dict(verse_notes=notes, cross_references=total, verses_with_references=verses,
               reference_lists_unparsed=unparsed)
    db.log_ingest(con, "ingest/tsk.py", CODE, started, out)
    con.commit()
    print(out)
    return out


if __name__ == "__main__":
    main()
