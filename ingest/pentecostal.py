"""Early Pentecostal writings published before 1931 (public domain in the US),
from scans on archive.org, with the OCR text cleaned.

    python3 -m ingest.pentecostal           # ingest
    python3 -m ingest.pentecostal --list    # show how each book was divided

Each book is divided at its "CHAPTER I." headings (titles taken from the
contents page where readable); running page headers (capital-letter lines that
repeat down the pages) and page numbers are dropped; long chapters are split
into parts of about 1,500 words.
"""

import re
import sys
from collections import Counter

from library import db
from library.fetch import fetch
from library.ocr import WordFixer, build_vocab, clean_marks, normalize_refs, paragraphs, strip_garble
from library.scripture import parse_free_refs, roman_to_int
from ingest.devotional import kjv_shingles, norm, parts, quoted_verses, tidy_title

AUTHORS = {
    "etter": ("Maria Woodworth-Etter", "author", dict(
        sort_name="Woodworth-Etter, Maria Beulah", born="1844", died="1924",
        description="American healing evangelist; first a Holiness preacher, she joined the Pentecostal movement "
                    "from 1912 and founded what became Lakeview Temple, Indianapolis.")),
    "mcpherson": ("Aimee Semple McPherson", "author", dict(
        sort_name="McPherson, Aimee Semple", born="1890", died="1944",
        description="Canadian-American Pentecostal evangelist; founder of Angelus Temple, Los Angeles, and of the "
                    "International Church of the Foursquare Gospel.")),
    "montgomery": ("Carrie Judd Montgomery", "author", dict(
        sort_name="Montgomery, Carrie Judd", born="1858", died="1946",
        description="American writer and teacher on divine healing; baptized in the Spirit in 1908 and associated "
                    "with the Assemblies of God; editor of Triumphs of Faith.")),
}

BOOKS = [
    dict(code="ETTER-SW", ident="signswondersgodw0000wood", author="etter", type="devotional",
         title="Signs and Wonders God Wrought in the Ministry for Forty Years", date="1916",
         edition="Indianapolis: Mrs. M. B. W. Etter, 1916 (School of Theology at Claremont scan)"),
    dict(code="MCPHERSON-TIT", ident="thisisthatperson00mcphrich", author="mcpherson", type="devotional",
         title="This Is That: Personal Experiences, Sermons and Writings", date="c1921",
         edition="Los Angeles: The Bridal Call Publishing House, c1921 (University of California Libraries scan)"),
    dict(code="MONTGOMERY-SOV", ident="secretsofvictory00montrich", author="montgomery", type="devotional",
         title="Secrets of Victory", date="1921",
         edition="Oakland: Office of Triumphs of Faith, 1921, compiled by Sadie A. Cody (University of California "
                 "Libraries scan)"),
]

CHAPTER = re.compile(r"^CHAPTER[:\s]+([IVXLYHxl1]{1,7})[\s.,:\-]*$")


def roman(s):
    return roman_to_int(s.upper().replace("L", "I").replace("1", "I").replace("Y", "V").replace("H", "II").lower()) or 0


def rebreak(p, size=250):
    """The scans have few paragraph breaks: cut very long paragraphs at sentence ends."""
    if len(p.split()) <= 2 * size:
        return [p]
    out, cur, n = [], [], 0
    for sent in re.split(r"(?<=[.!?\u201d\"])\s+(?=[A-Z\u201c\"])", p):
        cur.append(sent)
        n += len(sent.split())
        if n >= size:
            out.append(" ".join(cur))
            cur, n = [], 0
    if cur:
        out.append(" ".join(cur))
    return out


def letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def split_book(raw):
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.split("\n")]
    caps = Counter(ln for ln in lines if ln and ln.upper() == ln and len(ln) > 5 and not CHAPTER.match(ln))
    repeated = {ln for ln, n in caps.items() if n >= 5}
    chap_lines = [i for i, ln in enumerate(lines) if CHAPTER.match(ln)]

    def words_until(i, j):
        return sum(len(ln.split()) for ln in lines[i + 1:j])

    # A real chapter heading is followed by a page or more of text before the next heading; the entries
    # on the contents page are only a line or two apart.
    body = [i for k, i in enumerate(chap_lines)
            if words_until(i, chap_lines[k + 1] if k + 1 < len(chap_lines) else len(lines)) >= 150]
    first_body = body[0] if body else len(lines)
    contents = [i for i in chap_lines if i < first_body]
    titles = []
    for i in contents:
        nxt = next((ln for ln in lines[i + 1:i + 5] if ln and not CHAPTER.match(ln)), "")
        titles.append(re.sub(r"[\s.\u2022\-]*\d+$", "", nxt).strip())
    if abs(len(titles) - len(body)) > 2:
        titles = []
    # The contents list can have an extra or a missing line (a preface, an unreadable entry), which
    # shifts every title by one; pick the shift under which the most chapters begin with their title.
    starts = [letters(" ".join(lines[i + 1:i + 8]))[:80] for i in body]
    best, best_hits = 0, -1
    for off in (0, -1, 1, -2, 2):
        hits = sum(1 for k, st in enumerate(starts)
                   if 0 <= k + off < len(titles) and len(letters(titles[k + off])) >= 6
                   and letters(titles[k + off])[:20] in st)
        if hits > best_hits:
            best, best_hits = off, hits
    shifted = [titles[k + best] if 0 <= k + best < len(titles) else "" for k in range(len(body))]
    # The shift can change part-way through the list, so a chapter whose opening names one of the listed
    # titles takes that title; the others keep the shifted one.
    usable = [t for t in titles if len(letters(t)) >= 6]
    def opening(i):
        # A chapter that opens "Its Title. Body text..." names itself in that short first sentence.
        m = re.match(r"^([A-Z\u201c\"][^.!?]{5,60})[.!?]\s", " ".join(ln for ln in lines[i + 1:i + 8] if ln))
        return m.group(1).strip() if m and len(m.group(1).split()) <= 9 else ""
    titles = [next((t for t in usable if letters(t)[:20] in st), "") or opening(body[k]) or shifted[k]
              for k, st in enumerate(starts)]
    titles = [re.sub(r"[\s\u00bb\u2022.]+(\d+)?$", "", t) for t in titles]
    # Titles listed on the contents pages ("TITLE ...... 281"), used to divide a long last chapter.
    listed = []
    for ln in lines[:first_body]:
        m = re.match(r"^(.*?[A-Za-z].*?)[\s.\u2022\-]*\b(\d{1,3})$", ln)
        if m and m.group(1).upper() == m.group(1) and len(letters(m.group(1))) >= 4:
            listed.append(m.group(1).strip(" .-\u2022"))
    sections = []
    for k, i in enumerate(body):
        stop = body[k + 1] if k + 1 < len(body) else len(lines)
        seg = lines[i + 1:stop]
        title = titles[k] or ""
        last = k + 1 == len(body)
        if last and words_until(i, stop) > 15000 and listed:
            # Split the remainder at the first appearance of each listed title, in order.
            cuts, pos = [], 0
            seg_letters = [letters(ln) for ln in seg]
            for t in listed:
                want = letters(t)
                hit = next((idx for idx in range(pos, len(seg)) if seg_letters[idx] == want), None)
                if hit is not None:
                    cuts.append((hit, t))
                    pos = hit + 1
            pieces = [(0, title)] + cuts
        else:
            pieces = [(0, title)]
        for p_idx, (start, ptitle) in enumerate(pieces):
            end = pieces[p_idx + 1][0] if p_idx + 1 < len(pieces) else len(seg)
            chunk = [ln for ln in seg[start + (1 if p_idx else 0):end]
                     if ln not in repeated and not re.fullmatch(r"[\divxlcIVXLC]{1,5}\.?|[\W_]+", ln or "x")]
            paras = paragraphs("\n".join(chunk))
            if not ptitle and paras and len(paras[0].split()) <= 12 and paras[0].upper() == paras[0]:
                ptitle = paras.pop(0)
            if sum(len(x.split()) for x in paras) < 80:
                continue
            name = f"Chapter {k + 1}: {tidy_title(ptitle)}" if p_idx == 0 else tidy_title(ptitle)
            if p_idx and sum(len(x.split()) for x in paras) > 15000:
                name = "Later chapters"   # a stretch whose titles could not be matched to the contents
            if p_idx == 0 and not ptitle:
                name = f"Chapter {k + 1}"
            sections.append((name, paras))
    return sections


def main(argv):
    started = db.now()
    listing = "--list" in argv
    con = None if listing else db.connect()
    index = kjv_shingles(con) if con else None
    fixer = WordFixer(build_vocab(con)) if con else None
    results = {}
    for book in BOOKS:
        fetched = fetch(f"https://archive.org/download/{book['ident']}/{book['ident']}_djvu.txt", "archive",
                        f"{book['ident']}_djvu.txt")
        sections = split_book(open(fetched["path"], encoding="utf-8", errors="replace").read())
        if listing:
            print(f"== {book['code']} {book['title']}: {len(sections)} chapters")
            for t, p in sections:
                print(f"     {sum(len(x.split()) for x in p):>6} words  {t}")
            continue
        wid = db.upsert_work(
            con, book["code"], book["title"], book["type"], [AUTHORS[book["author"]]], "Public Domain",
            short_title=f"{AUTHORS[book['author']][0]}, {book['title'].split(':')[0]}", original_date=book["date"],
            edition=book["edition"] + "; OCR text cleaned by ingest/pentecostal.py",
            source_name="Internet Archive", source_url=f"https://archive.org/details/{book['ident']}",
            license_evidence="Published in the United States before 1931, so in the US public domain (US copyright "
                             "lasts 95 years from publication for works of this period). Not a Google-digitized copy.",
            coverage=f"Complete book ({len(sections)} chapters)",
            known_issues="Text comes from OCR and was cleaned automatically: expect occasional misspelt words and "
                         "stray page headers. Testimonies and sermons, not commentary.",
            ingest_script="ingest/pentecostal.py")
        db.add_provenance(con, wid, fetched, notes=book["edition"])
        w = db.EntryWriter(con, wid)
        for title, paras in sections:
            paras = [strip_garble(clean_marks(normalize_refs(fixer.fix_text(p)))) for p in paras]
            paras = [q for p in paras for q in rebreak(p)]
            chunks = parts(paras)
            for k, chunk in enumerate(chunks, 1):
                body = "\n\n".join(chunk)
                t = title if len(chunks) == 1 else f"{title} (part {k} of {len(chunks)})"
                refs = [(s, e, "cites", "text_parse", txt[:120]) for s, e, txt in parse_free_refs(body)]
                refs += [(v, v, "cites", "quotation_match", f"quotes: {q} ...")
                         for v, q in quoted_verses(body, index).items()]
                w.add("section", f"{norm(title)[:80]}#{k}", t, body, refs)
        w.flush()
        results[book["code"]] = dict(chapters=len(sections), entries=w.n_entries, scripture_links=w.n_refs)
        db.log_ingest(con, "ingest/pentecostal.py", book["code"], started, results[book["code"]])
        con.commit()
        print(book["code"], results[book["code"]])
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
