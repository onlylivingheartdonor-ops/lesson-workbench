"""Lutheran sources (public domain): catechisms, the Augsburg Confession, a lay
handbook of Lutheran teaching, and two of Luther's commentaries.

    python3 -m ingest.lutheran           # ingest
    python3 -m ingest.lutheran --list    # show how each book was divided

Project Gutenberg books are split at their headings (see split_headings) and
long sections into parts of about 1,500 words.  Luther on Galatians comes from
a scan (Philadelphia, 1891) and is filed verse by verse at its "CHAPTER I." /
"Verse 1." headings, with the OCR text cleaned (library/ocr.py).
"""

import re
import sys

from library import db
from library.fetch import fetch
from library.ocr import WordFixer, build_vocab, clean_marks, normalize_refs, paragraphs, strip_garble
from library.scripture import chapter_last_verse, format_ref, parse_free_refs, roman_to_int, vid
from ingest.devotional import PG, body_lines, kjv_shingles, norm, parts, quoted_verses, tidy_title

LUTHER = ("Martin Luther", "author", dict(sort_name="Luther, Martin", born="1483", died="1546",
          description="German reformer; professor at Wittenberg, whose teaching on justification by faith "
                      "began the Reformation and the Lutheran churches."))
AUTHORS = {
    "luther": LUTHER,
    "melanchthon": ("Philip Melanchthon", "author", dict(
        sort_name="Melanchthon, Philip", born="1497", died="1560",
        description="Luther's colleague at Wittenberg; wrote the Augsburg Confession (1530), the founding "
                    "statement of Lutheran teaching.")),
    "gerberding": ("G. H. Gerberding", "author", dict(
        sort_name="Gerberding, George Henry", born="1847", died="1927",
        description="American Lutheran pastor (Fargo, Dakota) and seminary professor; wrote The Way of "
                    "Salvation in the Lutheran Church 'for the common people'.")),
    "stump": ("Joseph Stump", "author", dict(
        sort_name="Stump, Joseph", born="1866", died="1935",
        description="American Lutheran pastor and seminary president (Northwestern Lutheran Theological "
                    "Seminary); his explanation of Luther's Small Catechism was a standard confirmation text.")),
    "bente": ("F. Bente", "translator", dict(sort_name="Bente, Friedrich", born="1858", died="1930",
              description="Lutheran (Missouri Synod) professor at Concordia Seminary, St. Louis; co-editor of the "
                          "Triglot Concordia (1921).")),
    "dau": ("W. H. T. Dau", "translator", dict(sort_name="Dau, William Herman Theodore", born="1864", died="1944",
            description="Lutheran (Missouri Synod) professor at Concordia Seminary, St. Louis; co-editor of the "
                        "Triglot Concordia (1921).")),
    "lenker": ("John Nicholas Lenker", "editor", dict(sort_name="Lenker, John Nicholas", born="1858", died="1929",
               description="American Lutheran pastor and editor of an English edition of Luther's works.")),
}

BOOKS = [
    dict(code="GERBERDING-WOS", n=16285, authors=["gerberding"], type="doctrinal",
         title="The Way of Salvation in the Lutheran Church", date="1887 (revised edition, Lutheran Publication "
         "Society, Philadelphia)", start=r"^PREFACE\.?$|^INTRODUCTION\.?$"),
    dict(code="LUTHER-LC", n=1722, authors=["luther", "bente", "dau"], type="doctrinal",
         title="The Large Catechism", date="1529; translation by F. Bente and W. H. T. Dau in the Triglot "
         "Concordia (St. Louis: Concordia, 1921)", start=r"^Preface$"),
    dict(code="STUMP-SC", n=9912, authors=["stump"], type="doctrinal",
         title="An Explanation of Luther's Small Catechism", date="1907 (this edition 1910)", start=r"^PREFACE$"),
    dict(code="AUGSBURG", n=275, authors=["melanchthon"], type="doctrinal", title="The Augsburg Confession",
         date="1530 (English translation as reprinted by Project Gutenberg from a public-domain edition)",
         start=r"^PREFACE TO THE EMPEROR CHARLES V\.?$"),
    dict(code="LUTHER-GEN", n=48193, authors=["luther", "lenker"], type="commentary",
         title="Luther on the Creation: A Critical and Devotional Commentary on Genesis [1-3]",
         date="1544 (lectures); English: Henry Cole's translation revised by J. N. Lenker (Minneapolis: Lutherans "
              "in All Lands, 1904)", start=r"^COMMENTARY ON GENESIS\.?$", book=1),
]

GALATIANS = dict(code="LUTHER-GAL", ident="cu31924029294141", book=48,
                 title="A Commentary on Saint Paul's Epistle to the Galatians",
                 date="1535 (Latin); English translation first published 1575, this printing Philadelphia: "
                      "John Highlands, 1891")

HEAD_WORD = re.compile(r"^(CHAPTER|PART|ARTICLE|Article|SECTION|LECTURE|The (First|Second|Third|Fourth|Fifth|"
                       r"Sixth|Seventh|Eighth|Ninth|Tenth) (Commandment|Article|Petition|Part))\b")


def is_heading(lines, i):
    s = lines[i].strip()
    if not s or len(s) > 80 or len(s.split()) > 12:
        return False
    if (i and lines[i - 1].strip()) or (i + 1 < len(lines) and lines[i + 1].strip()):
        return False
    if HEAD_WORD.match(s):
        return True
    if s.endswith((",", ";")) or re.fullmatch(r"[\W\d_]+", s):
        return False
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) >= 0.8 * len(letters)


def chapter_titles(lines):
    """Roman numeral -> chapter title from a contents page laid out as "CHAPTER II." / "Title ..... 19"."""
    out = {}
    for i, ln in enumerate(lines[:-3]):
        m = re.fullmatch(r"\s*CHAPTER ([IVXL]+)\.?\s*", ln)
        if not m:
            continue
        for nxt in lines[i + 1:i + 4]:
            t = re.match(r"^\s*(\S.*?)\s*\.{3,}\s*\d+\s*$", nxt)
            if t:
                out.setdefault(m.group(1), t.group(1))
                break
    return out


def split_headings(lines, start_pat, nth=1):
    hits = [i for i, ln in enumerate(lines) if re.match(start_pat, ln.strip())]
    start = hits[nth - 1] if len(hits) >= nth else 0
    named = chapter_titles(lines[:start]) if start else {}
    heads = [i for i in range(start, len(lines)) if i == start or is_heading(lines, i)]
    sections, pending = [], None
    for k, i in enumerate(heads):
        stop = heads[k + 1] if k + 1 < len(heads) else len(lines)
        paras, cur = [], []
        for ln in lines[i + 1:stop]:
            if ln.strip():
                cur.append(ln.strip())
            elif cur:
                paras.append(" ".join(cur))
                cur = []
        if cur:
            paras.append(" ".join(cur))
        title = tidy_title(lines[i].strip())
        m = re.fullmatch(r"CHAPTER ([IVXL]+)\.?", lines[i].strip())
        if m and m.group(1) in named:
            title = f"Chapter {m.group(1)}: {named[m.group(1)]}"
        if pending:   # a heading with almost no text of its own is joined to the next section
            if title.lower() in pending[0].lower():
                title = pending[0]
            else:
                title = f"{pending[0]}: {title}" if len(pending[0]) + len(title) < 90 else pending[0]
            paras = pending[1] + paras
            pending = None
        if sum(len(p.split()) for p in paras) < 40:
            pending = (title, paras)
            continue
        sections.append((title, paras))
    if pending and sections:
        sections[-1] = (sections[-1][0], sections[-1][1] + pending[1])
    return sections


def galatians_items(raw, fixer):
    """(chapter, verse, text) items from the OCR text of Luther's Galatians."""
    def clean(t):
        return strip_garble(clean_marks(normalize_refs(fixer.fix_text(t))))
    items, chapter, verse, started = [], 0, 0, False
    for b in paragraphs(raw):
        t = b.strip()
        m = re.match(r"^CHAPTER\s+([IVXL]{1,4})\.?\s*$", t)
        if m:
            n = roman_to_int(m.group(1).lower())
            if n == chapter + 1:
                chapter, verse, started = n, 0, True
            continue
        if not started or re.fullmatch(r"[\divxlcIVXLC]{1,5}\.?", t) or re.fullmatch(r"[A-Z .,']{3,40}", t):
            continue   # front matter, page numbers, running headers
        m = re.match(r"^Verse\s+(\d{1,2})\.?\s*", t)
        if m and verse <= int(m.group(1)) <= chapter_last_verse(GALATIANS["book"], chapter):
            verse = int(m.group(1))
            t = t[m.end():]
            items.append([chapter, verse, clean(t)])
            continue
        if items and items[-1][0] == chapter and items[-1][1] == verse:
            items[-1][2] += "\n\n" + clean(t)
        else:
            items.append([chapter, verse, clean(t)])
        if chapter == 6 and re.match(r"^(THE END|INDEX)\b", t):
            break
    return items


def main(argv):
    started = db.now()
    listing = "--list" in argv
    con = None if listing else db.connect()
    if con and not con.execute("SELECT 1 FROM reference_types WHERE code='doctrinal'").fetchone():
        con.execute("INSERT INTO reference_types(code, name, description) VALUES (?,?,?)",
                    ("doctrinal", "Doctrinal work", "Catechisms, confessions of faith and doctrinal handbooks"))
    index = kjv_shingles(con) if con else None
    results = {}
    for book in BOOKS:
        fetched = fetch(PG.format(n=book["n"]), "gutenberg", f"pg{book['n']}.txt")
        sections = split_headings(body_lines(fetched["path"]), book["start"], book.get("nth", 1))
        if listing:
            print(f"== {book['code']} {book['title']}: {len(sections)} sections")
            for t, p in sections:
                print(f"     {sum(len(x.split()) for x in p):>6} words  {t}")
            continue
        wid = db.upsert_work(
            con, book["code"], book["title"], book["type"], [AUTHORS[a] for a in book["authors"]],
            "Public Domain (USA)", short_title=f"{AUTHORS[book['authors'][0]][0]}, {book['title'].split(':')[0]}",
            original_date=book["date"], edition=f"Project Gutenberg eBook #{book['n']} (plain text, UTF-8)",
            source_name="Project Gutenberg", source_url=f"https://www.gutenberg.org/ebooks/{book['n']}",
            license_evidence="Published before 1931 (see original date). Project Gutenberg: 'This eBook is for the "
                             "use of anyone anywhere in the United States and most other parts of the world at no "
                             "cost and with almost no restrictions whatsoever.' Project Gutenberg header, footer and "
                             "trademark removed.",
            coverage=f"Complete book ({len(sections)} sections)",
            known_issues="Public domain in the USA; status in other countries not checked.",
            ingest_script="ingest/lutheran.py")
        db.add_provenance(con, wid, fetched)
        w = db.EntryWriter(con, wid)
        cur_ch = 0
        for title, paras in sections:
            m = re.search(r"\bChapter ([IVXL]+)\b", title)
            if book.get("book") and m:
                cur_ch = roman_to_int(m.group(1).lower())
            about = []
            if book.get("book") and cur_ch:
                b = book["book"]
                about = [(vid(b, cur_ch, 1), vid(b, cur_ch, chapter_last_verse(b, cur_ch)), "about", "verse_key",
                          f"Genesis {cur_ch}")]
            chunks = parts(paras)
            for k, chunk in enumerate(chunks, 1):
                body = "\n\n".join(chunk)
                t = title if len(chunks) == 1 else f"{title} (part {k} of {len(chunks)})"
                refs = about + [(s, e, "cites", "text_parse", txt[:120]) for s, e, txt in parse_free_refs(body)]
                refs += [(v, v, "cites", "quotation_match", f"quotes: {q} ...")
                         for v, q in quoted_verses(body, index).items()]
                w.add("commentary_note" if about else "section", f"{norm(title)[:80]}#{k}", t, body, refs)
        w.flush()
        results[book["code"]] = dict(sections=len(sections), entries=w.n_entries, scripture_links=w.n_refs)
        db.log_ingest(con, "ingest/lutheran.py", book["code"], started, results[book["code"]])
        con.commit()
        print(book["code"], results[book["code"]])
    if listing:
        return
    # Luther on Galatians (scan)
    g = GALATIANS
    fetched = fetch(f"https://archive.org/download/{g['ident']}/{g['ident']}_djvu.txt", "archive",
                    f"{g['ident']}_djvu.txt")
    fixer = WordFixer(build_vocab(con))
    items = galatians_items(open(fetched["path"], encoding="utf-8", errors="replace").read(), fixer)
    wid = db.upsert_work(
        con, g["code"], g["title"], "commentary", [LUTHER], "Public Domain",
        short_title="Martin Luther, Galatians", original_date=g["date"],
        edition="Philadelphia: John Highlands, 1891 (Cornell University Library scan, archive.org "
                f"{g['ident']}); OCR text cleaned by ingest/lutheran.py",
        source_name="Internet Archive (Cornell University Library scan)",
        source_url=f"https://archive.org/details/{g['ident']}",
        license_evidence="Printed 1891 in the US from the 16th-century English translation; the scan's title page "
                         "states 'There are no known copyright restrictions in the United States on the use of the "
                         "text.' Not a Google-digitized copy. (Project Gutenberg's version, Theodore Graebner's "
                         "1939 translation, was not used because its copyright status is unclear.)",
        coverage="Galatians 1-6, filed under the verse headings Luther's text uses",
        known_issues="Text comes from OCR and was cleaned automatically: expect occasional misspelt words.",
        ingest_script="ingest/lutheran.py")
    db.add_provenance(con, wid, fetched, notes="Luther, Galatians, Philadelphia 1891 (Cornell)")
    w = db.EntryWriter(con, wid)
    verses = set()
    for ch, v, text in items:
        if len(text.split()) < 8:
            continue
        refs = [(s, e, "cites", "text_parse", t) for s, e, t in parse_free_refs(text, default_book=g["book"])]
        if v == 0:
            s, e = vid(g["book"], ch, 1), vid(g["book"], ch, chapter_last_verse(g["book"], ch))
            key, title, etype = f"{vid(g['book'], ch, 0)}-intro", f"Martin Luther: Galatians {ch} (opening)", "chapter_intro"
        else:
            s = e = vid(g["book"], ch, v)
            key, title, etype = f"{s}-{s}", f"Martin Luther on {format_ref(s)}", "commentary_note"
            verses.add(s)
        for k, part in enumerate(parts(text.split("\n\n")), 1):
            w.add(etype, f"{key}#{k}", title, "\n\n".join(part), [(s, e, "about", "verse_key", None)] + refs)
    w.flush()
    total = sum(chapter_last_verse(g["book"], c) for c in range(1, 7))
    results[g["code"]] = dict(entries=w.n_entries, verses_with_a_note=len(verses), verses_in_book=total,
                              scripture_links=w.n_refs, ocr_words_fixed=fixer.fixed)
    db.log_ingest(con, "ingest/lutheran.py", g["code"], started, results[g["code"]])
    con.commit()
    print(g["code"], results[g["code"]])
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
