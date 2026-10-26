"""Ingest verse-keyed commentaries from CrossWire SWORD modules.

    python3 -m ingest.commentaries            # all of them
    python3 -m ingest.commentaries MHC JFB    # selected works

Each module note becomes one entry, linked 'about' the verse or passage it
is filed under (method 'verse_key'), plus 'cites' links for every scripture
reference inside it.  Chapter and book introductions become separate
'chapter_intro' / 'book_intro' entries covering the whole chapter or book.
"""

import re
import sys

from library import db
from library.crosswire import MODULE_PAGE, edition, get_module, license_evidence
from library.markup import RefStats, extract_refs, to_text
from library.scripture import (BOOK_NAME, book_last_chapter, chapter_last_verse, format_ref, split_vid, vid)

WORKS = {
    "MHC": dict(
        module="MHC", title="Matthew Henry's Commentary on the Whole Bible (Complete)", short="Matthew Henry",
        original_date="1708-1710 (completed by others after Henry's death in 1714)",
        authors=[("Matthew Henry", "author", dict(sort_name="Henry, Matthew", born="1662", died="1714",
                  description="English Nonconformist (Presbyterian) minister; his devotional, practical "
                              "Exposition of the Old and New Testaments is the best-known English commentary."))],
        coverage="Whole Bible (Acts-Revelation completed from Henry's notes by other ministers)",
        issues="Each section begins with the KJV text of the passage, as in the printed edition."),
    "CLARKE": dict(
        module="Clarke", title="Adam Clarke's Commentary and Critical Notes on the Bible", short="Adam Clarke",
        original_date="1810-1826",
        authors=[("Adam Clarke", "author", dict(sort_name="Clarke, Adam", born="c. 1760", died="1832",
                  description="British Methodist preacher and scholar; his commentary took about 40 years and "
                              "was a standard Methodist reference for a century."))],
        coverage="Whole Bible", issues=None),
    "BARNES": dict(
        module="Barnes", title="Barnes' Notes on the New Testament", short="Albert Barnes",
        original_date="1832-1853",
        authors=[("Albert Barnes", "author", dict(sort_name="Barnes, Albert", born="1798", died="1870",
                  description="American Presbyterian pastor (Philadelphia); his popular Notes were written for "
                              "Sunday School teachers and families."))],
        coverage="New Testament only",
        issues="The CrossWire edition covers the New Testament only; Barnes' Old Testament notes (Job, Psalms, "
               "Isaiah, Daniel) are not included. Placeholder notes ('No specific Barnes text on this verse') "
               "were skipped. The introduction to Revelation is missing from this edition (it points to a "
               "location that does not exist in the module)."),
    "JFB": dict(
        module="JFB", title="Commentary Critical and Explanatory on the Whole Bible (Jamieson, Fausset & Brown)",
        short="Jamieson-Fausset-Brown", original_date="1871",
        authors=[("Robert Jamieson", "author", dict(sort_name="Jamieson, Robert", born="1802", died="1880",
                  description="Scottish minister (Church of Scotland); wrote Genesis-Esther.")),
                 ("Andrew Robert Fausset", "author", dict(sort_name="Fausset, Andrew Robert", born="1821",
                  died="1910", description="Anglican clergyman; wrote Job-Malachi.")),
                 ("David Brown", "author", dict(sort_name="Brown, David", born="1803", died="1897",
                  description="Scottish Free Church minister and principal of Aberdeen Free Church College; "
                              "wrote the New Testament volumes."))],
        coverage="Whole Bible", issues="This is the 1871 one-volume 'Commentary Critical and Explanatory'."),
}

BARNES_PLACEHOLDER = re.compile(r"No specific Barnes text on this verse", re.I)


def whole_chapter(b, c):
    return vid(b, c, 1), vid(b, c, chapter_last_verse(b, c))


def whole_book(b):
    last = book_last_chapter(b)
    return vid(b, 1, 1), vid(b, last, chapter_last_verse(b, last))


def split_barnes_heading(markup):
    """Barnes puts the chapter heading (and, for chapter 1, the book's preface and
    introduction; for some chapters an analysis) in the verse-1 slot, ahead of
    "Verse 1.".  Return (intro_markup or None, note_markup)."""
    m = re.search(r"\bVer(?:se|\.)\s*1\b", markup)
    if not m or m.start() == 0:
        return None, markup
    intro = markup[:m.start()]
    if len(to_text(intro).split()) < 40:  # just a heading such as "MATTHEW Chapter 2"
        return None, markup[m.start():]
    return intro, markup[m.start():]


def ingest(con, code, cfg, started):
    fetched, conf, module = get_module(cfg["module"])
    wid = db.upsert_work(con, code, cfg["title"], "commentary", cfg["authors"], "Public Domain",
                         short_title=cfg["short"], original_date=cfg["original_date"],
                         edition=edition(cfg["module"], conf), source_name="CrossWire Bible Society",
                         source_url=MODULE_PAGE + cfg["module"], license_evidence=license_evidence(cfg["module"], conf),
                         coverage=cfg["coverage"], known_issues=cfg["issues"], ingest_script="ingest/commentaries.py")
    db.add_provenance(con, wid, fetched)
    w = db.EntryWriter(con, wid)
    stats = RefStats()
    skipped = dict(empty=0, placeholder=0)
    counts = dict(commentary_note=0, chapter_intro=0, book_intro=0)

    def add(kind, s, e, markup, key_suffix=""):
        text = to_text(markup)
        if len(re.sub(r"\W", "", text)) < 3:
            skipped["empty"] += 1
            return
        b, c, v = split_vid(s)
        refs = extract_refs(markup, book=b, chapter=c if c else None, stats=stats)
        if kind == "book_intro":
            about = whole_book(b)
            title = f"{cfg['short']}: Introduction to {BOOK_NAME[b]}"
        elif kind == "chapter_intro":
            about = whole_chapter(b, c)
            title = f"{cfg['short']}: {BOOK_NAME[b]} {c} (chapter introduction)"
        else:
            about = (s, e)
            title = f"{cfg['short']} on {format_ref(s, e)}"
        all_refs = [(about[0], about[1], "about", "verse_key", None)]
        all_refs += [(rs, re_, "cites", m, t) for rs, re_, m, t in refs]
        w.add(kind, f"{s}-{e}{key_suffix}", title, text, all_refs)
        counts[kind] += 1

    for s, e, raw in module.iter_entries():
        markup = raw.decode("utf-8", errors="replace")
        b, c, v = split_vid(s)
        if code == "BARNES":
            if BARNES_PLACEHOLDER.search(markup):
                skipped["placeholder"] += 1
                continue
            if v == 1:
                intro, markup = split_barnes_heading(markup)
                if intro and c == 1:
                    add("book_intro", vid(b, 0, 0), vid(b, 0, 0), intro, "-intro")
                elif intro:
                    add("chapter_intro", vid(b, c, 0), vid(b, c, 0), intro, "-intro")
        if c == 0:
            add("book_intro", s, s, markup)
        elif v == 0:
            add("chapter_intro", s, s, markup)
        else:
            add("commentary_note", s, e, markup)
    w.flush()
    out = dict(entries=w.n_entries, **counts, scripture_links=w.n_refs, skipped=skipped, **stats.as_dict())
    db.log_ingest(con, "ingest/commentaries.py", code, started, out)
    return out


def main(argv):
    started = db.now()
    codes = [a.upper() for a in argv] or list(WORKS)
    con = db.connect()
    results = {}
    for code in codes:
        results[code] = ingest(con, code, WORKS[code], started)
        con.commit()
        print(code, results[code])
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
