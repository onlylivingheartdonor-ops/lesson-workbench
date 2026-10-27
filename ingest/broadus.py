"""John A. Broadus, Commentary on the Gospel of Matthew (An American Commentary
on the New Testament, American Baptist Publication Society, 1886), from the
University of Toronto scan on archive.org, with the OCR text cleaned.

    python3 -m ingest.broadus

The verse-note parser is the one built for Barnes' Old Testament notes
(ingest/barnes_ot.py, class Volume): Broadus also begins each note with the
verse number and the opening words of the verse ("1. In those days."), and
each note is filed under the verse whose KJV wording those opening words
match.  Broadus's section headings ("Ch. 5: 1-12. THE BEATITUDES.") are turned
into chapter headings where a section starts a chapter; running page headers
("MATTHEW.", "[CH. III.") are dropped.
"""

import re
import sys

from library import db
from library.fetch import fetch
from library.ocr import KjvMatcher, WordFixer, build_vocab
from library.scripture import (BOOK_NAME, book_last_chapter, chapter_last_verse, format_ref, parse_free_refs, vid)
from ingest.barnes_ot import split_parts

CODE = "BROADUS"
BOOK = 40
IDENT = "commentonmatthew00broauoft"
URL = f"https://archive.org/download/{IDENT}/{IDENT}_djvu.txt"
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
         "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII"]


HEADER = re.compile(r"^\[?\s*CH(?:AP)?\.?\s*([IVXL]{1,7})\s*\.?\s*\]?$")
SECTION = re.compile(r"^Ch\.\s*(\d{1,2})\s*:\s*(\d{1,2})(?:\s*[-\u2013\u2014]\s*(?:(\d{1,2})\s*:\s*)?(\d{1,2}))?\.?")
NOTE = re.compile(r"^(\d{1,2})\s?\.\s+(?=[A-Z'\"(\u2018\u201c])")
SPLIT = re.compile(r"(?<=[.?!\"'\u201d)])\s+(?=\d{1,2}\s?\.\s+[A-Z'\"\u2018\u201c])")
BIBLE_LINE = re.compile(r"^\d{1,2}\s+[A-Z]")      # printed Bible text: verse number without a full stop
FOOT = re.compile(r"^(?:[a-z\u00b9\u00b2\u00b3*\u2020\u2021]|\d)\s?(?:The|This|So|Comp|See|Rev|Greek|Or|It|In|A|We)\b")
STOP = set("the and that for with this from have his him her they them their thee thou thy shall unto upon which "
           "what when who are was were not but all into then there these those also been its let may one said".split())


def roman(s):
    from library.scripture import roman_to_int
    return roman_to_int(s.lower())


def lemma_hit(lemma, words):
    short = re.split(r"\s[\u2014\u2013-]|[,;:.(\u2014]", lemma, maxsplit=1)[0]
    ws = [w for w in re.findall(r"[a-z]{3,}", short.lower()) if w not in STOP][:5]
    if not ws:
        return None
    return sum(1 for w in ws if w in words) / len(ws)


def parse(raw, fixer, matcher, verse_words):
    """Items (kind, chapter, verse_from, verse_to, text) from the OCR text of Broadus's Matthew."""
    from library.ocr import clean_marks, normalize_refs, paragraphs, strip_garble
    blocks = paragraphs(raw)
    items, chapter, verse = [], 0, 0
    started = False
    dropped = dict(page=0, header=0, bible_text=0, footnote=0)

    def clean(t):
        return strip_garble(clean_marks(normalize_refs(fixer.fix_text(t))))

    def add(kind, ch, v1, v2, text):
        if items and items[-1][:4] == (kind, ch, v1, v2):
            items[-1] = items[-1][:4] + (items[-1][4] + "\n\n" + text,)
        else:
            items.append((kind, ch, v1, v2, text))

    for b in blocks:
        t = b.strip()
        if re.fullmatch(r"[\divxlcIVXLC]{1,5}\.?|MATTHEW\.?", t):
            dropped["page"] += 1
            continue
        m = HEADER.match(t)
        if m:
            n = roman(m.group(1))
            if n and chapter <= n <= chapter + 1:   # a page header can confirm or advance the chapter
                if n == chapter + 1 and started:
                    chapter, verse = n, 0
            dropped["header"] += 1
            continue
        if BIBLE_LINE.match(t) or (len(t.split()) >= 8 and chapter and matcher.share(t, BOOK, chapter) >= 0.6):
            dropped["bible_text"] += 1
            continue
        if len(t.split()) <= 40 and FOOT.match(t):
            dropped["footnote"] += 1
            continue
        sm = SECTION.match(t)
        if sm:
            c1 = int(sm.group(1))
            if 1 <= c1 <= 28 and c1 >= chapter:
                started = True
                v1 = int(sm.group(2))
                c2 = int(sm.group(3) or c1)
                v2 = int(sm.group(4) or v1)
                if c1 != chapter:
                    chapter, verse = c1, 0
                if v2 >= v1 or c2 > c1:
                    kind = "section" if not re.match(r"^Ch\.[^.]*\.\s+[A-Z][a-z]", t[sm.end() - 1:] if False else "") else "section"
                    add("section", c1, v1, v2 if c2 == c1 else chapter_last_verse(BOOK, c1), clean(t))
                    verse = max(verse, v1 - 1)
                    continue
        if not started:
            add("book_intro", 0, 0, 0, clean(t))
            continue
        for piece in SPLIT.split(t):
            piece = piece.strip()
            if not piece:
                continue
            nm = NOTE.match(piece)
            if nm:
                n = int(nm.group(1))
                lemma = piece[nm.end():][:120]
                cands = []
                for c in (chapter, chapter + 1):
                    if 1 <= c <= 28 and n <= chapter_last_verse(BOOK, c):
                        score = lemma_hit(lemma, verse_words.get(vid(BOOK, c, n), ()))
                        cands.append((c, score))
                target = None
                for c, score in cands:
                    if c == chapter and (verse < n <= verse + 3 or
                                         (verse + 3 < n <= verse + 8 and (score is None or score >= 0.34))):
                        target = c
                        break
                    if c == chapter + 1 and n <= 3 and verse >= 0.5 * chapter_last_verse(BOOK, chapter or 1) \
                            and score is not None and score >= 0.5:
                        target = c
                        break
                if target is None:
                    for c, score in cands:
                        if c == chapter and n > verse and score is not None and score >= 0.67:
                            target = c
                            break
                if target is not None:
                    if target != chapter:
                        chapter = target
                    verse = n
                    add("note", chapter, n, n, clean(piece))
                    continue
            if verse == 0:
                add("section", chapter, 0, 0, clean(piece)) if items and items[-1][0] == "section" else \
                    add("chapter_intro", chapter, 0, 0, clean(piece))
            else:
                add("note", chapter, verse, verse, clean(piece))
    return items, dropped


def main(argv):
    started = db.now()
    con = db.connect()
    fixer = WordFixer(build_vocab(con))
    matcher = KjvMatcher(con)
    verse_words = {}
    for v, text in con.execute("SELECT b.verse_id, b.text FROM bible_text b JOIN works w ON w.id=b.work_id "
                               "WHERE w.code='KJV' AND b.verse_id BETWEEN 40000000 AND 40999999"):
        verse_words[v] = sorted(set(re.findall(r"[a-z]+", text.lower())))
    fetched = fetch(URL, "archive", f"{IDENT}_djvu.txt")
    wid = db.upsert_work(
        con, CODE, "Commentary on the Gospel of Matthew", "commentary",
        [("John A. Broadus", "author", dict(
            sort_name="Broadus, John Albert", born="1827", died="1895",
            description="Southern Baptist preacher and scholar; a founder and later president of the Southern "
                        "Baptist Theological Seminary."))],
        "Public Domain", short_title="John A. Broadus", original_date="1886",
        edition="An American Commentary on the New Testament, ed. Alvah Hovey (Philadelphia: American Baptist "
                "Publication Society, c1886); University of Toronto (Robarts Library) scan, OCR text cleaned by "
                "ingest/broadus.py",
        source_name="Internet Archive (University of Toronto scan)",
        source_url=f"https://archive.org/details/{IDENT}",
        license_evidence="Published 1886 in the US; the archive.org record marks the scan NOT_IN_COPYRIGHT. Not a "
                         "Google-digitized copy.",
        coverage="Matthew, verse notes and section introductions",
        known_issues="Text comes from OCR and was cleaned automatically: expect occasional misspelt words, Greek "
                     "words replaced by '[...]', footnotes mixed into the notes, and some notes filed under a "
                     "neighbouring verse where the scan misread a verse number.",
        ingest_script="ingest/broadus.py")
    db.add_provenance(con, wid, fetched, notes="Broadus, Commentary on Matthew, 1886 (University of Toronto)")
    items, dropped = parse(open(fetched["path"], encoding="utf-8", errors="replace").read(), fixer, matcher,
                           verse_words)
    writer = db.EntryWriter(con, wid)
    note_verses = sorted({(ch, v1) for kind, ch, v1, v2, text in items if kind == "note"})
    next_note = {a: b[1] for a, b in zip(note_verses, note_verses[1:]) if a[0] == b[0]}
    notes = intros = sections = 0
    verses = set()
    for kind, ch, v1, v2, text in items:
        if len(text.split()) < 4:
            continue
        refs = [(s, e, "cites", "text_parse", t) for s, e, t in parse_free_refs(text, default_book=BOOK)]
        if kind == "book_intro":
            last = book_last_chapter(BOOK)
            for k, part in enumerate(split_parts(text), 1):
                writer.add("book_intro", f"{BOOK}000000-intro#{k}", f"John A. Broadus: Introduction to Matthew (part {k})",
                           part, [(vid(BOOK, 1, 1), vid(BOOK, last, chapter_last_verse(BOOK, last)), "about",
                                   "verse_key", None)] + [(s, e, "cites", "text_parse", t)
                                                          for s, e, t in parse_free_refs(part, default_book=BOOK)])
            continue
        if kind in ("chapter_intro", "section"):
            if kind == "section" and v1:
                s, e = vid(BOOK, ch, v1), vid(BOOK, ch, max(v1, v2))
                key, title = f"{s}-{e}-section", f"John A. Broadus on {format_ref(s, e)} (section)"
                sections += 1
            else:
                s, e = vid(BOOK, ch, 1), vid(BOOK, ch, chapter_last_verse(BOOK, ch))
                key, title = f"{vid(BOOK, ch, 0)}-intro", f"John A. Broadus: Matthew {ch} (introduction)"
                intros += 1
            for k, part in enumerate(split_parts(text), 1):
                writer.add("chapter_intro", f"{key}#{k}", title, part, [(s, e, "about", "verse_key", None)] + refs)
            continue
        # A note covers its verse and any following verses Broadus discusses without a numbered note.
        s = vid(BOOK, ch, v1)
        nxt = next_note.get((ch, v1))
        e = vid(BOOK, ch, (nxt - 1) if nxt and nxt - 1 >= v1 else (v1 if nxt else chapter_last_verse(BOOK, ch)))
        e = min(e, vid(BOOK, ch, v1 + 6))
        for k, part in enumerate(split_parts(text), 1):
            writer.add("commentary_note", f"{s}-{s}#{k}", f"John A. Broadus on {format_ref(s, e)}", part,
                       [(s, e, "about", "verse_key", None)] + refs)
        notes += 1
        verses.add(s)
    writer.flush()
    total = sum(chapter_last_verse(BOOK, c) for c in range(1, 29))
    out = dict(entries=writer.n_entries, verse_notes=notes, chapter_intros=intros, sections=sections, verses_with_a_note=len(verses),
               verses_in_book=total, coverage=round(len(verses) / total, 3), dropped_blocks=dropped,
               ocr_words_fixed=fixer.fixed)
    db.log_ingest(con, "ingest/broadus.py", CODE, started, out)
    con.commit()
    print(CODE, out)
    chapters = {}
    for s in verses:
        chapters[(s // 1000) % 1000] = chapters.get((s // 1000) % 1000, 0) + 1
    print("verses with a note, per chapter:", {c: f"{chapters.get(c, 0)}/{chapter_last_verse(BOOK, c)}"
                                               for c in range(1, 29)})
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
