"""Alexander Maclaren, Expositions of Holy Scripture (1904-1910), from the
Project Gutenberg plain-text editions (15 of the published volumes).

    python3 -m ingest.maclaren           # ingest
    python3 -m ingest.maclaren --list    # show the expositions found in each volume

Each volume lists its expositions on contents pages as "TITLE (Genesis xii. 1-9)".
The same titles head the expositions in the body.  Every exposition becomes
one entry (split into parts of about 1,500 words when long) linked 'about'
the passage named on the contents page, or, when the contents line gives
none, the passage quoted under the heading ("...'--GENESIS xii. 5.").
Other references and word-for-word KJV quotations are linked as 'cites'.
"""

import re
import sys

from library import db
from library.fetch import fetch
from library.scripture import (book_from_name, chapter_last_verse, is_valid, parse_free_refs, roman_to_int,
                               vid)
from ingest.devotional import PG, body_lines, kjv_shingles, norm, parts, quoted_verses, tidy_title

AUTHOR = ("Alexander Maclaren", "author", dict(
    sort_name="Maclaren, Alexander", born="1826", died="1910",
    description="Scottish-born Baptist preacher; minister of Union Chapel, Manchester, for 45 years and twice "
                "president of the Baptist Union of Great Britain and Ireland; called 'the prince of expository "
                "preachers'."))

VOLUMES = [  # Gutenberg number, books covered (as printed on the title page)
    (7069, "Genesis, Exodus, Leviticus and Numbers"),
    (8068, "Deuteronomy, Joshua, Judges, Ruth, First Samuel, Second Samuel, First Kings, Second Kings i-vii"),
    (7883, "Second Kings from viii, Chronicles, Ezra and Nehemiah"),
    (7925, "Psalms"),
    (8069, "Isaiah and Jeremiah"),
    (15836, "Ezekiel, Daniel, the Minor Prophets, St Matthew i-viii"),
    (7351, "St Matthew ix-xxviii"),
    (8071, "St Mark"),
    (8200, "St Luke"),
    (8070, "St John i-xiv"),
    (8381, "St John xv-xxi"),
    (8397, "The Acts"),
    (13601, "Romans, Corinthians (to II Corinthians v)"),
    (21190, "Second Corinthians, Galatians, Philippians, Colossians, Thessalonians, First Timothy"),
    (24674, "Ephesians, Epistles of St Peter and St John"),
]

_REF = re.compile(
    r"((?:[1-3]|I{1,3}|First|Second|Third)?\s?(?:St\.?\s)?[A-Za-z][A-Za-z]+)\.?\s+"
    r"([ivxlcIVXLC]+|\d+)(?:\.\s*|\.?,?\s+)([\dlI]+)(?:\s*[-–]\s*([\dlI]+))?"
    r"(?:\s*-{2,}\s*([ivxlcIVXLC]+)\.\s*([\dlI]+))?")
_CH_ONLY = re.compile(r"((?:[1-3]|I{1,3}|First|Second)?\s?[A-Za-z][A-Za-z]+)\.?\s+([ivxlcIVXLC]+)\.?\s*\)?$")
ORDINAL = {"first": "1", "second": "2", "third": "3", "i": "1", "ii": "2", "iii": "3"}


def _num(tok):
    return int(tok.replace("l", "1").replace("I", "1"))


def _book(name):
    name = re.sub(r"^St\.?\s", "", name.strip())
    parts_ = name.split(None, 1)
    if len(parts_) == 2 and parts_[0].lower() in ORDINAL:
        name = ORDINAL[parts_[0].lower()] + " " + parts_[1]
    name = re.sub(r"^St\.?\s", "", name)
    b = book_from_name(name.title())
    if not b and name.lower().rstrip("s") == "psalm":
        b = 19
    return b


def maclaren_refs(text):
    """Passages written in Maclaren's style: 'Genesis i. 26--ii. 3', 'GENESIS xii. 5', 'Psalm xxiii.'"""
    out = []
    for m in _REF.finditer(text):
        b = _book(m.group(1))
        if not b:
            continue
        ch = roman_to_int(m.group(2).lower()) if not m.group(2).isdigit() else int(m.group(2))
        v1 = _num(m.group(3))
        if not ch or not is_valid(b, ch, v1):
            continue
        start = end = vid(b, ch, v1)
        if m.group(5):
            ch2 = roman_to_int(m.group(5).lower())
            v2 = _num(m.group(6))
            if ch2 and is_valid(b, ch2, v2):
                end = vid(b, ch2, v2)
        elif m.group(4) and is_valid(b, ch, _num(m.group(4))):
            end = vid(b, ch, _num(m.group(4)))
        else:  # "cxxv. 1, 2" - a short list of verses taken as a range
            more = re.match(r"(?:\s*,\s*(\d+))+", text[m.end():])
            if more:
                last = int(re.findall(r"\d+", more.group(0))[-1])
                if v1 < last <= v1 + 6 and is_valid(b, ch, last):
                    end = vid(b, ch, last)
        if end >= start:
            out.append((start, end, m.group(0)))
    if not out:
        m = _CH_ONLY.search(text.strip())
        if m:
            b = _book(m.group(1))
            ch = roman_to_int(m.group(2).lower())
            if b and ch and is_valid(b, ch, 1):
                out.append((vid(b, ch, 1), vid(b, ch, chapter_last_verse(b, ch)), m.group(0)))
    return out


_CONTENTS_LINE = re.compile(r"^(.*\S)\s*\(([^()]*[ivxlcIVXLC\d]+\.?[^()]*)\)\s*\d*\s*$")
_EPIGRAPH = re.compile(r"-{1,2}\s*((?:[1-3]|I{1,3})?\s?[A-Z][A-Za-z .]+?\s[ivxlc]+\.\s*[\dl]+(?:\s*[-\u2013,]\s*[\dl]+)*)")


def key(title):
    return re.sub(r"[^a-z]", "", title.lower())


_CONTENTS_ITEM = re.compile(r"([A-Z][A-Z0-9'\u2019,;:!?.\- ]{2,90}?)\s*\(([^()]{3,70})\)")


def contents_refs(lines):
    """Map title key -> passage text for every "TITLE (Passage)" item on the contents pages.
    Items can run together on one line or wrap across lines, so the text is scanned as a whole."""
    refs = {}
    text = " ".join(ln.strip() for ln in lines)
    for m in _CONTENTS_ITEM.finditer(text):
        title, ref = m.group(1).strip(" '.,"), m.group(2)
        if not re.search(r"[ivxlcIVXLC]+\.?,?\s*[\dl]|[ivxlc]+\.?\)?$", ref):
            continue
        # The match can start too early (book headings, "CONTENTS" and the like run into the
        # title), so every trailing run of words is registered; the real title is one of them.
        words = title.split()
        for k in range(len(words)):
            kk = key(" ".join(words[k:]))
            if len(kk) >= 3:
                refs.setdefault(kk, ref)
    return refs


def is_heading(lines, i):
    s = lines[i].strip()
    if not s or (i and lines[i - 1].strip()) or (i + 1 < len(lines) and lines[i + 1].strip()):
        return False
    if len(s.split()) > 14 or _CONTENTS_LINE.match(s) or re.fullmatch(r"[IVXL]+\.?|[*\s]+|_.*_", s):
        return False
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) >= 0.8 * len(letters)


def split_volume(lines):
    refs = contents_refs(lines)
    heads = [i for i in range(len(lines)) if is_heading(lines, i)]
    sections = []
    for idx, i in enumerate(heads):
        stop = heads[idx + 1] if idx + 1 < len(heads) else len(lines)
        paras, cur = [], []
        for ln in lines[i + 1:stop]:
            if ln.strip():
                cur.append(ln.strip())
            elif cur:
                paras.append(" ".join(cur))
                cur = []
        if cur:
            paras.append(" ".join(cur))
        paras = [p for p in paras if not re.fullmatch(r"[IVXL]+\.?|\*[\s*]*", p)]
        title = lines[i].strip()
        if sum(len(p.split()) for p in paras) < 300 or re.fullmatch(
                r"(?i)contents|the (first |second )?(book|gospel|epistles?|prophecy) of .*|st\.? \w+|the proverbs|"
                r"the (acts|psalms)|(the )?(first|second) (book|epistle) .*", title.strip()):
            continue  # contents pages, title pages, book headings, series titles with no text of their own
        ref = refs.get(key(title), "")
        about = maclaren_refs(ref) if ref else []
        if not about:
            m = _EPIGRAPH.search(" ".join(paras[:2])[:700])
            if m:
                about = maclaren_refs(m.group(1))
                ref = ref or m.group(1).strip()
        sections.append((tidy_title(title), ref, about, paras))
    return sections, len(refs)


def main(argv):
    started = db.now()
    listing = "--list" in argv
    con = None if listing else db.connect()
    index = kjv_shingles(con) if con else None
    total = dict(volumes=0, expositions=0, entries=0, without_passage=0)
    vols = []
    for n, books in VOLUMES:
        fetched = fetch(PG.format(n=n), "gutenberg", f"pg{n}.txt")
        sections, n_contents = split_volume(body_lines(fetched["path"]))
        vols.append((n, books, fetched, sections, n_contents))
        if listing:
            print(f"== {n} {books}: {len(sections)} expositions of {n_contents} contents lines")
            for t, ref, about, paras in sections:
                print(f"   {sum(len(p.split()) for p in paras):>6}  {t[:60]:<60} {ref[:28]:<28} {about[:1]}")
    if listing:
        return
    wid = db.upsert_work(
        con, "MACLAREN", "Expositions of Holy Scripture", "commentary", [AUTHOR], "Public Domain (USA)",
        short_title="Alexander Maclaren",
        original_date="1904-1910 (Hodder & Stoughton, London; George H. Doran, New York)",
        edition="Project Gutenberg eBooks " + ", ".join(f"#{n}" for n, *_ in VOLUMES) + " (plain text, UTF-8)",
        source_name="Project Gutenberg", source_url="https://www.gutenberg.org/ebooks/search/?query=maclaren+expositions",
        license_evidence="Published 1904-1910; the author died in 1910. Project Gutenberg: 'This eBook is for the use "
                         "of anyone anywhere in the United States and most other parts of the world at no cost and "
                         "with almost no restrictions whatsoever.' Project Gutenberg header, footer and trademark "
                         "removed.",
        coverage="15 volumes on Project Gutenberg: " + "; ".join(b for _, b, *_ in VOLUMES) + ". Books not "
                 "covered are listed in docs/REPORT.md (the Gutenberg set lacks some volumes).",
        known_issues="Expositions are sermons on a passage, not verse-by-verse notes; each entry is linked to its "
                     "passage as a whole.",
        ingest_script="ingest/maclaren.py")
    w = db.EntryWriter(con, wid)
    for n, books, fetched, sections, _ in vols:
        db.add_provenance(con, wid, fetched)
        total["volumes"] += 1
        for title, ref, about, paras in sections:
            total["expositions"] += 1
            if not about:
                # Last resort: the passage printed under the heading, recognised as KJV text.
                q = sorted(quoted_verses(" ".join(paras[:3]), index))
                if q and q[0] // 1000000 == q[-1] // 1000000 and q[-1] - q[0] < 3000:
                    about = [(q[0], q[-1], "passage printed under the heading (KJV text match)")]
                    total["passage_from_kjv_match"] = total.get("passage_from_kjv_match", 0) + 1
            if not about:
                total["without_passage"] += 1
            chunks = parts(paras)
            for k, chunk in enumerate(chunks, 1):
                body = "\n\n".join(chunk)
                t = title if len(chunks) == 1 else f"{title} (part {k} of {len(chunks)})"
                if ref:
                    t = f"{t} ({ref})"
                refs = [(s, e, "about", "quotation_match" if "KJV text match" in txt else "text_parse", txt[:120])
                        for s, e, txt in about]
                refs += [(s, e, "cites", "text_parse", txt[:120]) for s, e, txt in parse_free_refs(body)]
                refs += [(v, v, "cites", "quotation_match", f"quotes: {q} ...")
                         for v, q in quoted_verses(body, index).items()]
                w.add("exposition", f"{n}:{norm(title)[:70]}#{k}", t, body, refs)
    w.flush()
    total["entries"] = w.n_entries
    total["scripture_links"] = w.n_refs
    db.log_ingest(con, "ingest/maclaren.py", "MACLAREN", started, total)
    con.commit()
    print("MACLAREN", total)
    return total


if __name__ == "__main__":
    main(sys.argv[1:])
