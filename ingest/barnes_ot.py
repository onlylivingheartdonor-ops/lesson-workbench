"""Ingest Albert Barnes' Old Testament notes (Job, Psalms, Isaiah, Daniel) from
public-domain scans on archive.org, cleaning the OCR text.

    python3 -m ingest.barnes_ot            # build
    python3 -m ingest.barnes_ot --report   # also print per-chapter coverage

How a scanned volume is turned into verse notes
-----------------------------------------------
1. The OCR text is split into blocks and each block is cleaned
   (hyphenation, OCR letter confusions, damaged references, unreadable
   Greek/Hebrew replaced by "[...]") - see library/ocr.py.
2. Page numbers and running page headers are dropped.  A chapter heading
   ("CHAPTER V.", "PSALM XXIII.") counts as a real chapter start only when it
   is not next to a page number and is the next chapter in sequence.
3. The KJV text printed at the top of each page is recognised by comparing
   it with our KJV and dropped, as are the translators' marginal footnotes.
4. Barnes begins each verse note with its number ("2. For wrath killeth...").
   Text is filed under the most recent verse number; a run of numbers that
   starts again at 1-3 after the chapter's later verses means a new chapter
   even when the heading was not readable.
5. Text after a chapter heading and before its first verse note is the
   chapter introduction ("Analysis of the chapter"); text before the first
   chapter of a book is the book introduction.
"""

import difflib
import re
import sys

from library import db
from library.fetch import fetch
from library.markup import RefStats, extract_refs
from library.ocr import KjvMatcher, WordFixer, build_vocab, clean_marks, normalize_refs, paragraphs, strip_garble
from library.scripture import BOOK_NAME, book_last_chapter, chapter_last_verse, format_ref, roman_to_int, vid

CODE = "BARNES-OT"
DL = "https://archive.org/download/{id}/{file}"

# (book, heading word, [(archive.org identifier, djvu text file name, description)])
BOOKS = [
    (18, "CHAPTER", [
        ("notescriticalill01barn", "notescriticalill01barn_djvu.txt", "Job vol. 1, New York: Leavitt, 1849 (Princeton Theological Seminary Library)"),
        ("notescriticalill02barn", "notescriticalill02barn_djvu.txt", "Job vol. 2, New York: Leavitt, 1849 (Princeton Theological Seminary Library)")]),
    (19, "PSALM", [
        ("notescriticalexp187101barn", "notescriticalexp187101barn_djvu.txt", "Psalms vol. 1, New York: Harper, 1871 (Princeton Theological Seminary Library)"),
        ("notescriticalexp187102barn", "notescriticalexp187102barn_djvu.txt", "Psalms vol. 2, New York: Harper, 1871 (Princeton Theological Seminary Library)"),
        ("notescriticalexp03barnuoft", "notescriticalexp03barnuoft_djvu.txt", "Psalms vol. 3, Edinburgh: Gall and Inglis, 1864 (University of Toronto)")]),
    (23, "CHAPTER", [
        ("notescriticalexp18471barn", "notescriticalexp18471barn_djvu.txt", "Isaiah vol. 1, New York: Leavitt & Allen, 1847 (Harold B. Lee Library, Brigham Young University)"),
        ("notescriticalexp18472barn", "notescriticalexp18472barn_djvu.txt", "Isaiah vol. 2, New York: Leavitt & Allen, 1847 (Harold B. Lee Library, Brigham Young University)")]),
    (27, "CHAPTER", [
        ("notescriticalill00barn", "notescriticalill00barn_djvu.txt", "Daniel, New York: Leavitt & Allen, 1861 (Princeton Theological Seminary Library)")]),
]

PART_WORDS = 1500
LEMMA_STOP = set("the and that for with this from have his him her they them their thee thou thy shall unto upon "
                 "which what when who whom are was were not but all our out into then there these those also "
                 "been him its let may one said say saith".split())


def heading_value(text, word):
    m = re.fullmatch(word + r"\s+([IVXLC1l]{1,9})\s*[.,]?\s*([IL])?\.?", text.strip())
    if not m:
        return []
    r = m.group(1).replace("1", "I").replace("l", "I")
    vals = []
    for cand in (r, r + (m.group(2) or ""), re.sub(r"L$", "I", r), r[:-1] + "I" if r.endswith("L") else None):
        if cand:
            n = roman_to_int(cand.lower())
            if n:
                vals.append(n)
    return list(dict.fromkeys(vals))


FOOTNOTE = re.compile(r"^(?:[a-z*'\"†‡]|\d{1,2})\s+(?:Or|or|Heb|Marg|Chald|Syr|Sept|[A-Z][a-z]{0,4}\.\s?[ivxlcIVXL\d])")
NOTE_START = re.compile(r"^(\d{1,3})\s?[.,]\s+(?=[^\d\s])")
SPLIT_NOTES = re.compile(r"(?<=[.?!\"'”])\s+(?=\d{1,3}\s?\.\s+[A-Z¶'\"])")


class Volume:
    def __init__(self, book, word, matcher, fixer, verse_words):
        self.book, self.word, self.kjv, self.fix = book, word, matcher, fixer
        self.verse_words = verse_words
        self.last_ch = book_last_chapter(book)
        self.items = []         # [kind, chapter, verse, text] kind in book_intro/chapter_intro/note
        self.force_new = False
        self.dropped = dict(kjv=0, footnote=0, page=0, header=0, unmatched_numbers=0)

    def clean(self, t):
        return strip_garble(clean_marks(normalize_refs(self.fix.fix_text(t))))

    def lemma_score(self, lemma, ch, v):
        """How well the opening words of a note match KJV verse ch:v (0-1)."""
        target = self.verse_words.get(vid(self.book, ch, v))
        if not target:
            return 0.0, 0
        lemma = re.sub(r"^(?:\u00b6|[HVIT]{1,2}|\W)+\s*", "", lemma)
        words = [w for w in re.findall(r"[a-z]+", lemma.lower()) if len(w) >= 3 and w not in LEMMA_STOP][:8]
        if not words:
            return 0.0, 0
        hit = 0
        for w in words:
            if w in target or difflib.get_close_matches(w, target, n=1, cutoff=0.75):
                hit += 1
        return hit / len(words), len(words)

    def emit(self, kind, ch, v, text):
        if self.items and tuple(self.items[-1][:3]) == (kind, ch, v) and not self.force_new:
            self.items[-1][3] += "\n\n" + text
        else:
            self.items.append([kind, ch, v, text])
        self.force_new = False

    def run(self, raw, chapter, first_volume):
        # A heading printed directly above its first paragraph is a block of its own.
        raw = re.sub(r"(?m)^([ \t]*" + self.word + r"[ \t]+[IVXLC1l]{1,9}[ \t]*[.,]?[ \t]*[IL]?\.?[ \t]*)$",
                     r"\n\1\n", raw)
        blocks = paragraphs(raw)
        is_page = [bool(re.fullmatch(r"[\divxlcIVXLC]{1,5}\.?", b.strip())) for b in blocks]
        verse = 0
        intro_seen = False
        heading_mark = None      # (chapter value(s), index into items) of the latest real-looking heading
        chapter_start = 0        # index into items where the current chapter's notes began
        for i, b in enumerate(blocks):
            t = b.strip()
            if is_page[i]:
                self.dropped["page"] += 1
                continue
            vals = heading_value(t, self.word)
            if vals:
                near_page = any(0 <= j < len(blocks) and is_page[j] for j in (i - 2, i - 1, i + 1, i + 2))
                if chapter == self.last_ch and verse > 3 and any(v < chapter - 1 for v in vals) and not near_page:
                    break  # an appendix after the last chapter (e.g. Job's new translation)
                if not near_page and any(chapter < v <= chapter + 2 for v in vals):
                    heading_mark = (vals, len(self.items))
                    self.force_new = True   # text after a heading must not merge into the previous note
                else:
                    self.dropped["header"] += 1
                continue
            if chapter == self.last_ch and verse > 3 and re.match(r"^(INDEX|GENERAL INDEX|INDEX OF)\b", t):
                break
            for piece in SPLIT_NOTES.split(t):
                piece = piece.strip()
                if not piece:
                    continue
                cleaned = self.clean(piece)
                words = cleaned.split()
                if len(words) <= 18 and FOOTNOTE.match(piece):
                    self.dropped["footnote"] += 1
                    continue
                if chapter >= 1 and len(words) >= 8 and self.kjv.share(cleaned, self.book, chapter) >= 0.6:
                    self.dropped["kjv"] += 1      # printed Bible text, even if it starts with "3."
                    continue
                m = NOTE_START.match(cleaned)
                if m:
                    n = int(m.group(1))
                    lemma = re.split(r"(?<=[a-z])[.?!]\s", cleaned[m.end():], maxsplit=1)[0]
                    target = None
                    # Restart: the chapter's analysis quoted verses with numbers, so a few "notes" were
                    # taken too early; a strong verse 1-2 match soon after means the real notes begin here.
                    if (chapter >= 1 and n <= 2 and n < verse
                            and len(self.items) - chapter_start <= 4):
                        score, nwords = self.lemma_score(lemma, chapter, n)
                        if nwords >= 2 and score >= 0.6:
                            early = self.items[chapter_start:]
                            del self.items[chapter_start:]
                            for it in early:
                                self.emit("chapter_intro", chapter, 0, it[3])
                            verse = n
                            self.emit("note", chapter, verse, cleaned)
                            self.dropped["restarts"] = self.dropped.get("restarts", 0) + 1
                            continue
                    if chapter == 0 and first_volume and not heading_mark:
                        candidates = ()   # still in the book's introduction
                    else:
                        candidates = (chapter, chapter + 1, chapter + 2)
                    best = None
                    for c in candidates:
                        if c < 1 or c > self.last_ch or n > chapter_last_verse(self.book, c):
                            continue
                        if c == chapter and n < verse:
                            continue
                        score, nwords = self.lemma_score(lemma, c, n)
                        if c == chapter:
                            sequential = verse < n <= verse + 3
                            ok = (nwords >= 2 and score >= 0.6) or (sequential and nwords >= 1 and score >= 0.5)
                        else:
                            mostly_done = chapter == 0 or verse >= 0.6 * chapter_last_verse(self.book, chapter)
                            confirmed = heading_mark and c in heading_mark[0]
                            if mostly_done and c == chapter + 1:
                                ok = (nwords >= 2 and score >= 0.6) or (n <= 2 and nwords == 1 and score == 1.0
                                                                       and confirmed)
                            elif mostly_done:   # skipping a whole chapter needs stronger evidence
                                ok = (confirmed and nwords >= 2 and score >= 0.6) or (nwords >= 3 and score >= 0.8)
                            else:
                                ok = n <= 2 and ((confirmed and nwords >= 1 and score >= 0.6)
                                                 or (nwords >= 3 and score >= 0.8))
                        if ok and (best is None or score > best[0] + 0.15):
                            best = (score, c)
                    target = best[1] if best else None
                    if target is None and candidates:
                        # Lost our place (a stretch of unreadable scan): accept a strong match further ahead.
                        for c in range(chapter + 3, min(self.last_ch, chapter + 6) + 1):
                            if n > chapter_last_verse(self.book, c):
                                continue
                            score, nwords = self.lemma_score(lemma, c, n)
                            if nwords >= 4 and score >= 0.85:
                                target = c
                                self.dropped["resyncs"] = self.dropped.get("resyncs", 0) + 1
                                break
                    if target is not None:
                        if target != chapter:
                            # Text since the new chapter's heading is that chapter's introduction.
                            if heading_mark and target in heading_mark[0]:
                                moved = self.items[heading_mark[1]:]
                                del self.items[heading_mark[1]:]
                                for it in moved:
                                    if it[0] == "book_intro" and first_volume and chapter == 0:
                                        self.items.append(it)
                                        continue
                                    self.emit("chapter_intro", target, 0, it[3])
                            heading_mark = None
                            chapter = target
                            chapter_start = len(self.items)
                        verse = n
                        self.emit("note", chapter, verse, cleaned)
                        continue
                    self.dropped["unmatched_numbers"] += 1
                if chapter == 0:
                    if first_volume and (intro_seen or re.match(r"^(PREFACE|INTRODUCTION|ADVERTISEMENT)\b", t)):
                        intro_seen = True
                        self.emit("book_intro", 0, 0, cleaned)
                    continue
                if self.kjv.share(cleaned, self.book, chapter) >= 0.45:
                    self.dropped["kjv"] += 1
                    continue
                if len(words) < 3:
                    continue
                self.emit("chapter_intro" if verse == 0 else "note", chapter, verse, cleaned)
        return chapter


def split_parts(text):
    paras, out, cur, n = text.split("\n\n"), [], [], 0
    for p in paras:
        cur.append(p)
        n += len(p.split())
        if n >= PART_WORDS:
            out.append("\n\n".join(cur))
            cur, n = [], 0
    if cur:
        out.append("\n\n".join(cur))
    return out


def main(argv):
    started = db.now()
    con = db.connect()
    fixer = WordFixer(build_vocab(con))
    matcher = KjvMatcher(con)
    verse_words = {}
    for v, text in con.execute("SELECT b.verse_id, b.text FROM bible_text b JOIN works w ON w.id=b.work_id "
                               "WHERE w.code='KJV' AND b.verse_id BETWEEN 18000000 AND 27999999"):
        verse_words[v] = sorted(set(re.findall(r"[a-z]+", text.lower())))
    wid = db.upsert_work(
        con, CODE, "Barnes' Notes on the Old Testament (Job, Psalms, Isaiah, Daniel)", "commentary",
        [("Albert Barnes", "author", dict(sort_name="Barnes, Albert", born="1798", died="1870",
          description="American Presbyterian pastor (Philadelphia); his popular Notes were written for "
                      "Sunday School teachers and families."))],
        "Public Domain", short_title="Albert Barnes (OT)", original_date="Job 1844, Isaiah 1840, Daniel 1853, Psalms 1868-69",
        edition="Scans of 19th-century printings on archive.org (see provenance rows), OCR text cleaned by "
                "ingest/barnes_ot.py",
        source_name="Internet Archive (Princeton Theological Seminary, Brigham Young University and University of Toronto scans)",
        source_url="https://archive.org/details/notescriticalill01barn",
        license_evidence="All volumes printed 1847-1871 (US and Edinburgh), so public domain in the US; the "
                         "archive.org records of the Princeton and Toronto scans mark them NOT_IN_COPYRIGHT and the "
                         "BYU scans carry no restriction. No "
                         "Google-digitized copies were used (those carry Google's usage request).",
        coverage="Job, Psalms, Isaiah, Daniel - the four Old Testament books Barnes himself annotated",
        known_issues="Text comes from OCR and was cleaned automatically: expect occasional misspelt words, "
                     "Greek and Hebrew words replaced by '[...]', and some notes filed under a neighbouring verse "
                     "where the scan misread a verse number. Measured quality is in docs/REPORT.md.",
        ingest_script="ingest/barnes_ot.py")
    writer = db.EntryWriter(con, wid)
    stats = RefStats()
    summary = {}
    for book, word, vols in BOOKS:
        chapter = 0
        all_items, dropped = [], {}
        for n, (ident, fname, desc) in enumerate(vols):
            fetched = fetch(DL.format(id=ident, file=fname), "archive", f"{ident}.txt")
            db.add_provenance(con, wid, fetched, notes=desc)
            vol = Volume(book, word, matcher, fixer, verse_words)
            chapter = vol.run(open(fetched["path"], encoding="utf-8", errors="replace").read(), chapter, n == 0)
            all_items += vol.items
            for k, v in vol.dropped.items():
                dropped[k] = dropped.get(k, 0) + v
        notes = chapters = 0
        verses = set()
        for kind, ch, v, text in all_items:
            if len(text.split()) < 4:
                continue
            if kind == "book_intro":
                about = (vid(book, 1, 1), vid(book, book_last_chapter(book), chapter_last_verse(book, book_last_chapter(book))))
                for k, part in enumerate(split_parts(text), 1):
                    refs = extract_refs("", stats=stats)
                    writer.add("book_intro", f"{book}000000-intro#{k}", f"Albert Barnes: Introduction to {BOOK_NAME[book]} (part {k})",
                               part, [(about[0], about[1], "about", "verse_key", None)] +
                               [(s, e, "cites", "text_parse", t) for s, e, t in
                                __import__("library.scripture", fromlist=["parse_free_refs"]).parse_free_refs(part)])
                continue
            if kind == "chapter_intro":
                s, e = vid(book, ch, 1), vid(book, ch, chapter_last_verse(book, ch))
                title = f"Albert Barnes: {BOOK_NAME[book]} {ch} (chapter introduction)"
                key = f"{vid(book, ch, 0)}-intro"
                etype = "chapter_intro"
                chapters += 1
            else:
                s = e = vid(book, ch, v)
                title = f"Albert Barnes on {format_ref(s)}"
                key = f"{s}-{s}"
                etype = "commentary_note"
                notes += 1
                verses.add(s)
            from library.scripture import parse_free_refs
            refs = [(rs, re_, "cites", "text_parse", t) for rs, re_, t in parse_free_refs(text, default_book=book)]
            writer.add(etype, key, title, text, [(s, e, "about", "verse_key", None)] + refs)
        total_verses = sum(chapter_last_verse(book, c) for c in range(1, book_last_chapter(book) + 1))
        summary[BOOK_NAME[book]] = dict(verse_notes=notes, chapter_intros=chapters, verses_with_a_note=len(verses),
                                        verses_in_book=total_verses,
                                        coverage=round(len(verses) / total_verses, 3), dropped_blocks=dropped)
    writer.flush()
    out = dict(entries=writer.n_entries, scripture_links=writer.n_refs, books=summary, ocr_words_fixed=fixer.fixed)
    db.log_ingest(con, "ingest/barnes_ot.py", CODE, started, out)
    con.commit()
    for k, v in summary.items():
        print(k, v)
    print("entries", writer.n_entries, "OCR words repaired", fixer.fixed)
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
