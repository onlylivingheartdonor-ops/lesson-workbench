"""Ingest Bible dictionaries and the encyclopedia from CrossWire modules:
Easton's Bible Dictionary, Smith's Bible Dictionary, and the International
Standard Bible Encyclopedia (1915).

    python3 -m ingest.dictionaries              # all
    python3 -m ingest.dictionaries EASTON       # one

Each article becomes an 'article' entry with 'cites' links for every
scripture reference.  Short "See OTHER" articles become 'redirect' entries
so alternate names still find the right article.
"""

import re
import sys

from library import db
from library.crosswire import MODULE_PAGE, edition, get_module, license_evidence
from library.markup import RefStats, extract_refs, nice_name, to_text

WORKS = {
    "EASTON": dict(
        module="Easton", ref_type="dictionary", title="Easton's Bible Dictionary", short="Easton's",
        original_date="1897 (3rd edition)",
        authors=[("Matthew George Easton", "author", dict(sort_name="Easton, Matthew George", born="1823",
                  died="1894", description="Scottish Presbyterian minister and scholar; his Illustrated Bible "
                                           "Dictionary was published posthumously (3rd ed. 1897)."))],
        coverage="About 4,000 articles",
        issues="The CrossWire edition's markup links many follow-on references to the wrong book (e.g. the "
               "'11' in 'Rev. 1:8, 11' is tagged as Genesis 1:11). References are re-read from their visible "
               "text; the number corrected is in the ingest log. Illustrations are not included."),
    "SMITH": dict(
        module="Smith", ref_type="dictionary", title="Smith's Bible Dictionary", short="Smith's",
        original_date="1863; this edition 1884",
        authors=[("William Smith", "author", dict(sort_name="Smith, William", born="1813", died="1893",
                  description="English lexicographer and classical scholar; editor of the Dictionary of the "
                              "Bible (1860-1863), here in its later one-volume form."))],
        coverage="About 4,500 articles",
        issues="Older edition: some spellings and scholarly views are dated."),
    "ISBE": dict(
        module="ISBE", ref_type="encyclopedia", title="International Standard Bible Encyclopedia (1915)",
        short="ISBE", original_date="1915",
        authors=[("James Orr", "general editor", dict(sort_name="Orr, James", born="1844", died="1913",
                  description="Scottish Presbyterian theologian; general editor of the ISBE (1915)."))],
        coverage="About 9,000 articles",
        issues="Transliterated Hebrew/Greek in plain ASCII as in the source edition; some OCR-style typos "
               "remain (e.g. 'Jet 41:3' for 'Jer 41:3')."),
}


def headword(key, body):
    m = re.search(r'<entryFree n="([^"]+)"', body)
    raw = m.group(1) if m else key
    raw = raw.strip()
    # Easton's gives proper case in n=""; the others are upper case.
    return nice_name(raw) if raw.isupper() else raw


def ingest(con, code, cfg, started):
    fetched, conf, reader = get_module(cfg["module"])
    wid = db.upsert_work(con, code, cfg["title"], cfg["ref_type"], cfg["authors"], "Public Domain",
                         short_title=cfg["short"], original_date=cfg["original_date"],
                         edition=edition(cfg["module"], conf), source_name="CrossWire Bible Society",
                         source_url=MODULE_PAGE + cfg["module"], license_evidence=license_evidence(cfg["module"], conf),
                         coverage=cfg["coverage"], known_issues=cfg["issues"], ingest_script="ingest/dictionaries.py")
    db.add_provenance(con, wid, fetched)
    w = db.EntryWriter(con, wid)
    stats = RefStats()
    kinds = dict(article=0, redirect=0, empty=0)
    for key, body in reader():
        title = headword(key, body)
        # Drop the repeated headword title inside the article.
        markup = re.sub(r"<title>.*?</title>", "", body, count=1, flags=re.S)
        text = to_text(markup)
        if not re.sub(r"\W", "", text):
            kinds["empty"] += 1
            continue
        kind = "redirect" if (len(text.split()) <= 12 and re.search(r"\bSee\b", text)) else "article"
        refs = extract_refs(markup, stats=stats)
        w.add(kind, key.strip(), title, text, [(s, e, "cites", m, t) for s, e, m, t in refs])
        kinds[kind] += 1
    w.flush()
    out = dict(entries=w.n_entries, **kinds, scripture_links=w.n_refs, **stats.as_dict(),
               correction_examples=[(a, b) for a, b, _ in stats.examples[:5]])
    db.log_ingest(con, "ingest/dictionaries.py", code, started, out)
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
