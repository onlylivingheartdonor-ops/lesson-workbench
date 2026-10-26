"""Ingest sermons and devotional works from Project Gutenberg plain-text
editions (E. M. Bounds, J. C. Ryle, D. L. Moody, C. H. Spurgeon).

    python3 -m ingest.devotional            # all
    python3 -m ingest.devotional --list     # show how each book was divided

Each book is divided into its chapters / sermons / addresses using a rule
chosen for that book's layout (see BOOKS).  Very long chapters are split
into parts of about 1,500 words so subject tagging stays specific.  The
Project Gutenberg header, footer and license text are removed: the texts
themselves are public domain in the United States, and removing the
Project Gutenberg name is what the Project Gutenberg license asks of anyone
who redistributes the text outside its terms.
"""

import re
import sys

from library import db
from library.fetch import fetch
from library.markup import nice_name
from library.scripture import parse_free_refs

PG = "https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt"

AUTHORS = {
    "bounds": ("E. M. Bounds", "author", dict(sort_name="Bounds, Edward McKendree", born="1835", died="1913",
               description="American Methodist minister and Civil War chaplain, best known for his books on "
                           "prayer (several published after his death, edited by Homer W. Hodge).")),
    "ryle": ("J. C. Ryle", "author", dict(sort_name="Ryle, John Charles", born="1816", died="1900",
             description="Evangelical Anglican, first Bishop of Liverpool; plain, practical writer.")),
    "moody": ("D. L. Moody", "author", dict(sort_name="Moody, Dwight Lyman", born="1837", died="1899",
              description="American evangelist; founder of the Moody Church and Moody Bible Institute.")),
    "spurgeon": ("C. H. Spurgeon", "author", dict(sort_name="Spurgeon, Charles Haddon", born="1834", died="1892",
                 description="English Baptist preacher at the Metropolitan Tabernacle, London; 'Prince of "
                             "Preachers'.")),
}

# rule: 'roman'   - headings are lone Roman numerals; titles come from the contents page
#       'chapter' - headings are "CHAPTER I."; the title is the next short line
#       'contents'- headings are the titles listed on the contents page
#       'italic'  - headings are _Italic Title._ lines
BOOKS = [
    dict(code="BOUNDS-PTP", n=65115, author="bounds", type="devotional", title="Power Through Prayer",
         date="1907 (this edition c. 1912, Marshall Brothers)", rule="roman", start=(r"^I$", 2)),
    dict(code="BOUNDS-PIP", n=66112, author="bounds", type="devotional", title="Purpose in Prayer",
         date="1920", rule="roman", start=(r"^I$", 1)),
    dict(code="BOUNDS-EOP", n=73271, author="bounds", type="devotional", title="The Essentials of Prayer",
         date="1925", rule="roman", start=(r"^I$", 1)),
    dict(code="BOUNDS-ROP", n=73032, author="bounds", type="devotional", title="The Reality of Prayer",
         date="1924", rule="roman", start=(r"^I$", 1)),
    dict(code="BOUNDS-PPM", n=70657, author="bounds", type="devotional", title="Prayer and Praying Men",
         date="1921", rule="chapter", start=(r"^CHAPTER I$", 1)),
    dict(code="RYLE-PR", n=38162, author="ryle", type="devotional", title="Practical Religion",
         date="1878", rule="contents", start=(r"^PRACTICAL RELIGION$", 2)),
    dict(code="RYLE-CROSS", n=62001, author="ryle", type="devotional", title="The Cross: A Tract for the Times",
         date="1851", rule="whole", start=(r"^THE CROSS\.$", 2), end=r"^TRACTS AND OTHER WORKS"),
    dict(code="MOODY-WTG", n=30449, author="moody", type="sermon", title="The Way to God and How to Find It",
         date="1884", rule="chapter", start=(r"^CHAPTER I\.$", 1)),
    dict(code="MOODY-SP", n=33341, author="moody", type="sermon",
         title="Secret Power; or, The Secret of Success in Christian Life and Work", date="1881",
         rule="chapter", start=(r"^CHAPTER I\.$", 1)),
    dict(code="MOODY-WW", n=33340, author="moody", type="sermon",
         title="Weighed and Wanting: Addresses on the Ten Commandments", date="1898", rule="contents",
         start=(r"^Weighed in the Balances$", 2), end=r"^WORKS BY G\. CAMPBELL MORGAN"),
    dict(code="MOODY-PP", n=61883, author="moody", type="sermon", title="Prevailing Prayer: What Hinders It?",
         date="1884", rule="chapter", start=(r"^CHAPTER I\.$", 2)),
    dict(code="MOODY-OL", n=33015, author="moody", type="sermon", title="The Overcoming Life, and Other Sermons",
         date="1896", rule="contents", start=(r"^THE OVERCOMING LIFE\.$", 1), end=r"^THE RED LIBRARY"),
    dict(code="MOODY-SG", n=30657, author="moody", type="sermon",
         title="Sovereign Grace: Its Source, Its Nature and Its Effects", date="1891", rule="chapter",
         start=(r"^CHAPTER I\.$", 1)),
    dict(code="SPURGEON-AWG", n=60669, author="spurgeon", type="devotional",
         title="Around the Wicket Gate; or, A Friendly Talk with Seekers Concerning Faith in the Lord Jesus Christ",
         date="1890", rule="contents", start=(r"^AWAKENING\.$", 1), end=r"^RELIGIOUS AND DEVOTIONAL BOOKS"),
    dict(code="SPURGEON-GAS", n=42657, author="spurgeon", type="devotional", title="Gleanings among the Sheaves",
         date="1869", rule="italic", start=(r"^GLEANINGS AMONG THE SHEAVES\.$", 2)),
]

PART_WORDS = 1500
SHINGLE = 8


def _words(text):
    return re.findall(r"[a-z]+", text.lower().replace("\u2019", "'").replace("'", ""))


def kjv_shingles(con):
    """Map every run of SHINGLE consecutive KJV words to the verse it comes from."""
    index = {}
    for v, text in con.execute("SELECT b.verse_id, b.text FROM bible_text b JOIN works w ON w.id=b.work_id "
                               "WHERE w.code='KJV'"):
        ws = _words(re.sub(r"[\[\]]", "", text))
        for i in range(len(ws) - SHINGLE + 1):
            key = " ".join(ws[i:i + SHINGLE])
            index[key] = None if key in index and index[key] != v else v   # None = phrase occurs in several verses
    return index


def quoted_verses(body, index):
    """Verses quoted word-for-word in a text: at least SHINGLE + 1 consecutive
    words (two overlapping runs), so stock phrases like "on the right hand or on
    the left" are not mistaken for quotations."""
    ws = _words(body)
    hits, prev = {}, None
    for i in range(len(ws) - SHINGLE + 1):
        v = index.get(" ".join(ws[i:i + SHINGLE]))
        if v and v == prev:
            hits.setdefault(v, " ".join(ws[i - 1:i + SHINGLE]))
        prev = v
    return hits
ROMAN = r"[IVXLC]+"


def body_lines(path):
    text = open(path, encoding="utf-8-sig").read().replace("\r", "")
    m = re.search(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text)
    e = re.search(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG", text)
    text = text[m.end() if m else 0: e.start() if e else len(text)]
    return text.split("\n")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def contents_titles(lines):
    """Titles from the contents page, keyed by Roman numeral when present."""
    titles, by_roman = [], {}
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\s*CONTENTS\.?\s*$", ln, re.I)), None)
    if start is None:
        return titles, by_roman
    blank_run = 0
    for ln in lines[start + 1:start + 200]:
        s = ln.strip()
        if not s:
            blank_run += 1
            if blank_run >= 4 and titles:
                break
            continue
        blank_run = 0
        if re.match(r"^(CHAPTER|PAGE)\b", s) and len(s.split()) <= 3:
            continue
        s = re.sub(r"[\s.]*\b\d+$", "", s).strip()           # page numbers
        m = re.match(r"^(" + ROMAN + r")\.?\s+(.*)$", s)
        if m and m.group(2):
            by_roman[m.group(1)] = m.group(2).strip(" .")
            titles.append(m.group(2).strip(" ."))
        elif s and len(s) < 90 and not s.startswith("["):
            titles.append(s.strip(" ."))
    return titles, by_roman


def tidy_title(t):
    t = re.sub(r"_", "", t).strip(" .")
    t = re.sub(r"\s{2,}\d+$", "", t)
    return nice_name(t) if t.isupper() else t


def split_book(book, lines):
    pat, nth = book["start"]
    hits = [i for i, ln in enumerate(lines) if re.match(pat, ln.strip())]
    if len(hits) < nth:
        raise ValueError(f"{book['code']}: start marker {pat!r} not found")
    start = hits[nth - 1]
    end = len(lines)
    if book.get("end"):
        e = next((i for i in range(start, len(lines)) if re.match(book["end"], lines[i].strip())), None)
        end = e if e is not None else end
    titles, by_roman = contents_titles(lines[:start])
    rule = book["rule"]
    heads = []  # (line index, title, lines consumed by heading)
    if rule == "whole":
        heads = [(start, book["title"], 1)]
    elif rule == "roman":
        for i in range(start, end):
            s = lines[i].strip()
            if re.fullmatch(ROMAN + r"\.?", s) and (i == 0 or not lines[i - 1].strip()):
                r = s.rstrip(".")
                heads.append((i, by_roman.get(r) or f"Chapter {r}", 1))
    elif rule == "chapter":
        for i in range(start, end):
            s = lines[i].strip()
            m = re.fullmatch(r"CHAPTER (" + ROMAN + r")\.?", s)
            if m:
                j = i + 1
                while j < end and not lines[j].strip():
                    j += 1
                nxt = lines[j].strip() if j < end else ""
                if nxt and len(nxt) < 70 and (nxt.isupper() or nxt.istitle()):
                    heads.append((i, nxt, j - i + 1))
                else:
                    heads.append((i, by_roman.get(m.group(1)) or f"Chapter {m.group(1)}", 1))
    elif rule == "contents":
        # Body headings may be shortened or lengthened versions of the contents
        # entries ("A HELPFUL SURVEY." for "A HELPFUL SURVEY OF CHRIST'S WORK").
        titles = [re.sub(r"^PART " + ROMAN + r"\.\s*", "", t) for t in titles]
        want = [norm(t) for t in titles if norm(t)]

        def same(a, b):
            if a == b:
                return True
            short, long_ = sorted((a, b), key=len)
            return len(short.split()) >= 2 and (long_.startswith(short + " ") or long_.endswith(" " + short))

        k = 0
        for i in range(start, end):
            s = norm(lines[i])
            if (not s or k >= len(want) or len(s.split()) > 10 or lines[i].strip().startswith("[")
                    or (i and lines[i - 1].strip())):
                continue
            for jj in range(k, min(k + 3, len(want))):
                if same(s, want[jj]):
                    heads.append((i, lines[i].strip(), 1))
                    k = jj + 1
                    break
        if not heads or heads[0][0] != start:
            heads.insert(0, (start, tidy_title(lines[start]), 1))
    elif rule == "italic":
        for i in range(start + 1, end):
            m = re.fullmatch(r"_(.+?)\.?_", lines[i].strip())
            if m and not lines[i - 1].strip():
                heads.append((i, m.group(1), 1))
    sections = []
    for idx, (i, title, used) in enumerate(heads):
        stop = heads[idx + 1][0] if idx + 1 < len(heads) else end
        paras, cur = [], []
        for ln in lines[i + used:stop]:
            if ln.strip():
                cur.append(ln.strip())
            elif cur:
                paras.append(" ".join(cur))
                cur = []
        if cur:
            paras.append(" ".join(cur))
        paras = [re.sub(r"\[Illustration[^\]]*\]", "", p).strip() for p in paras]
        paras = [p for p in paras if p]
        if sum(len(p.split()) for p in paras) < 40:
            continue
        sections.append((tidy_title(title), paras))
    return sections


def parts(paras):
    out, cur, n = [], [], 0
    for p in paras:
        cur.append(p)
        n += len(p.split())
        if n >= PART_WORDS:
            out.append(cur)
            cur, n = [], 0
    if cur:
        if out and n < PART_WORDS // 3:
            out[-1].extend(cur)
        else:
            out.append(cur)
    return out


def main(argv):
    started = db.now()
    listing = "--list" in argv
    con = None if listing else db.connect()
    results = {}
    index = kjv_shingles(con) if con else None
    for book in BOOKS:
        fetched = fetch(PG.format(n=book["n"]), "gutenberg", f"pg{book['n']}.txt")
        sections = split_book(book, body_lines(fetched["path"]))
        if listing:
            print(f"== {book['code']} {book['title']}: {len(sections)} sections")
            for t, p in sections:
                print(f"     {sum(len(x.split()) for x in p):>6} words  {t}")
            continue
        wid = db.upsert_work(
            con, book["code"], book["title"], book["type"], [AUTHORS[book["author"]]], "Public Domain (USA)",
            short_title=f"{AUTHORS[book['author']][0]}, {book['title'].split(':')[0].split(';')[0]}",
            original_date=book["date"], edition=f"Project Gutenberg eBook #{book['n']} (plain text, UTF-8)",
            source_name="Project Gutenberg", source_url=f"https://www.gutenberg.org/ebooks/{book['n']}",
            license_evidence="Project Gutenberg: 'This eBook is for the use of anyone anywhere in the United "
                             "States and most other parts of the world at no cost and with almost no restrictions "
                             "whatsoever.' Text is public domain in the USA; Project Gutenberg header, footer and "
                             "trademark removed.",
            coverage=f"Complete book ({len(sections)} chapters/sections)",
            known_issues="Public domain in the USA; status in other countries not checked.",
            ingest_script="ingest/devotional.py")
        db.add_provenance(con, wid, fetched)
        w = db.EntryWriter(con, wid)
        kind = "sermon" if book["type"] == "sermon" else "section"
        for title, paras in sections:
            chunks = parts(paras)
            for k, chunk in enumerate(chunks, 1):
                body = "\n\n".join(chunk)
                t = title if len(chunks) == 1 else f"{title} (part {k} of {len(chunks)})"
                refs = [(s, e, "cites", "text_parse", txt[:120]) for s, e, txt in parse_free_refs(body)]
                refs += [(v, v, "cites", "quotation_match", f"quotes: {q} ...") for v, q in quoted_verses(body, index).items()]
                w.add(kind, f"{norm(title)[:80]}#{k}", t, body, refs)
        w.flush()
        quoted = con.execute("SELECT COUNT(*) FROM entry_scripture es JOIN entries e ON e.id=es.entry_id "
                             "WHERE e.work_id=? AND es.method='quotation_match'", (wid,)).fetchone()[0]
        results[book["code"]] = dict(sections=len(sections), entries=w.n_entries, scripture_links=w.n_refs,
                                     of_which_quotation_matches=quoted)
        db.log_ingest(con, "ingest/devotional.py", book["code"], started, results[book["code"]])
        con.commit()
        print(book["code"], results[book["code"]])
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
