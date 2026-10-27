"""Ingest a selection of C. H. Spurgeon's best-known early sermons from
public-domain 19th-century American printings scanned on archive.org.

    python3 -m ingest.spurgeon            # build
    python3 -m ingest.spurgeon --list     # list every sermon found in the volumes

Each volume's OCR text is divided at its "SERMON I." headings; the title,
the scripture text the sermon is preached on, and the body are taken in
turn.  Running page headers, page numbers and printers' signature marks are
removed and the text is cleaned with library/ocr.py.  Each sermon is linked
'about' its text verse, plus every reference and every quoted KJV verse it
contains.  Only the sermons in SELECTION are ingested.
"""

import difflib
import re
import sys

from library import db
from library.fetch import fetch
from library.ocr import WordFixer, build_vocab, clean_marks, normalize_refs, paragraphs, strip_garble
from library.scripture import format_ref, parse_free_refs
from ingest.devotional import kjv_shingles, quoted_verses

CODE = "SPURGEON-SERMONS"
DL = "https://archive.org/download/{id}/{id}_djvu.txt"
VOLUMES = [
    ("sermonsofrevchsp01spur", "Sermons of the Rev. C. H. Spurgeon of London, [first series], New York: Sheldon, "
                               "Blakeman & Co., 1857 (New York Public Library)"),
    ("sermonsofrevchsp02spur", "Sermons of the Rev. C. H. Spurgeon of London, second series, New York: Sheldon, "
                               "Blakeman & Co., 1857 (New York Public Library)"),
    ("sermonsofrevchsp03spuruoft", "Sermons of Rev. C. H. Spurgeon of London, vol. 3, New York: Funk & Wagnalls "
                                   "(University of Toronto)"),
    ("sermonsofrevchsp05spuruoft", "Sermons of Rev. C. H. Spurgeon of London, vol. 5, New York: Funk & Wagnalls "
                                   "(University of Toronto)"),
    ("spurgeonssermons06spuruoft", "Sermons of Rev. C. H. Spurgeon of London, vol. 6, New York: Funk & Wagnalls "
                                   "(University of Toronto)"),
]
# The scripture text each sermon is preached on.  Recorded by hand from the scans because the OCR of
# these lines is often damaged ("KEBRSWS, ix 21" for Hebrews 9:22); each was checked against the scan.
SERMON_TEXTS = {
    "Sovereignty and Salvation": "Isaiah 45:22", "The Bible": "Hosea 8:12",
    "The Personality of the Holy Ghost": "John 14:16-17", "Christ Crucified": "1 Corinthians 1:23-24",
    "The Tomb of Jesus": "Matthew 28:6", "Heaven and Hell": "Matthew 8:11-12", "Faith": "Hebrews 11:6",
    "The Sin of Unbelief": "2 Kings 7:19", "Election": "2 Thessalonians 2:13-14", "Songs in the Night": "Job 35:10",
    "God's Providence": "Ezekiel 1:15-19", "Sweet Comfort for Feeble Saints": "Matthew 12:20",
    "The Resurrection of the Dead": "Acts 24:15", "A Visit to Calvary": "John 19:5",
    "Healing for the Wounded": "Psalm 147:3", "Secret Sins": "Psalm 19:12",
    "Elijah's Appeal to the Undecided": "1 Kings 18:21", "Regeneration": "John 3:3",
    "The Blood-Shedding": "Hebrews 9:22", "A Mighty Saviour": "Isaiah 63:1", "The Anxious Inquirer": "Job 23:3",
    "Spiritual Revival, the Want of the Church": "Habakkuk 3:2", "The New Heart": "Ezekiel 36:26",
    "A Lecture for Little Faith": "2 Thessalonians 1:3", "The Voice of the Blood of Christ": "Hebrews 12:24",
    "The Fatherhood of God": "Matthew 6:9", "His Name - Wonderful": "Isaiah 9:6",
    "Christ Precious to Believers": "1 Peter 2:7", "Little Sins": "Genesis 19:20", "Growth in Grace": "2 Peter 3:18",
    "Hypocrisy": "Luke 12:1",
}
# OCR spellings of titles that fuzzy matching would otherwise miss
ALIASES = {"iieaiing for the wounded a sermon for the crimean soldiers": "Healing for the Wounded"}
SELECTION = [
    "Sovereignty and Salvation", "The Bible", "The Personality of the Holy Ghost", "Christ Crucified",
    "The Tomb of Jesus", "Heaven and Hell", "Faith", "The Sin of Unbelief", "Election", "Songs in the Night",
    "God's Providence", "Sweet Comfort for Feeble Saints", "The Resurrection of the Dead", "A Visit to Calvary",
    "Healing for the Wounded", "Secret Sins", "Elijah's Appeal to the Undecided", "Regeneration",
    "The Blood-Shedding", "A Mighty Saviour", "The Anxious Inquirer", "Spiritual Revival, the Want of the Church",
    "The New Heart", "A Lecture for Little Faith", "The Voice of the Blood of Christ", "The Fatherhood of God",
    "His Name - Wonderful", "Christ Precious to Believers", "Little Sins", "Growth in Grace", "Hypocrisy",
]
PART_WORDS = 1500
HEADING = re.compile(r"^\s*SERMON\s+[IVXLCY1l]{1,7}\s*\.?\s*$")   # OCR often reads V as Y


def norm(s):
    return re.sub(r"[^a-z]+", " ", s.lower()).strip()


def _caps(ln):
    letters = re.sub(r"[^A-Za-z]", "", ln)
    return len(letters) >= 4 and sum(ch.isupper() for ch in letters) / len(letters) > 0.8


def split_sermons(raw):
    lines = raw.replace("\r", "").split("\n")
    starts = [i for i, ln in enumerate(lines) if HEADING.match(ln)]
    # Sermons whose "SERMON N." heading the OCR lost: a capitalised title line followed
    # within a few lines by the quoted scripture text ("... — PSALM xc. 1.").
    extra = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not (_caps(s) and 2 <= len(s.split()) <= 10 and not re.search(r"\d", s)):
            continue
        if any(i - 3 <= st <= i for st in starts):
            continue
        nxt = [x.strip() for x in lines[i + 1:i + 6] if x.strip()][:3]
        if nxt and re.match(r"^[\"“‘'*«u]{1,2}\s?[A-Z]", nxt[0]) and \
                any(re.search(r"[—–-]\s*[1-3I]?\s?[A-Z][A-Za-z]+\.?,?\s+[ivxlcIVXLC\d]", x) for x in nxt):
            extra.append(i - 1)
    starts = sorted(set(starts) | set(extra))
    sermons = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        j = i + 1
        title_lines = []
        while j < end and len(title_lines) < 3:
            ln = lines[j].strip()
            j += 1
            if not ln:
                if title_lines:
                    break
                continue
            letters = re.sub(r"[^A-Za-z]", "", ln)
            if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.7:
                title_lines.append(ln)
            else:
                j -= 1
                break
        title = " ".join(title_lines).strip(" .*")
        body_lines = lines[j:end]
        sermons.append((title, body_lines))
    return sermons


def clean_body(title, body_lines, fixer):
    tnorm = norm(title)
    kept = []
    for ln in body_lines:
        s = ln.strip()
        if re.fullmatch(r"[\d*.\s]{1,8}", s):                            # page numbers, signature marks
            continue
        if re.fullmatch(r"\d*\s*SERMONS?\.?\s*\d*", s, re.I):            # running header "2 SERMONS."
            continue
        sn = norm(re.sub(r"\d+", "", s))
        if sn and tnorm and (sn == tnorm or difflib.SequenceMatcher(None, sn, tnorm).ratio() > 0.85) \
                and len(s) < len(title) + 12:
            continue                                                     # running header with the title
        kept.append(ln)
    paras = []
    for p in paragraphs("\n".join(kept)):
        p = strip_garble(clean_marks(normalize_refs(fixer.fix_text(p))))
        if p:
            paras.append(p)
    # Paragraphs broken by page turns: join when the next one continues a sentence.
    joined = []
    for p in paras:
        if joined and not re.search(r"[.!?:\"”)]$", joined[-1]) and p[:1].islower():
            joined[-1] += " " + p
        else:
            joined.append(p)
    return joined


def text_reference(paras):
    """The scripture text a sermon is preached on: the first paragraph, ending '— Isaiah xlv. 22.'"""
    if not paras:
        return None, []
    for head in (paras[0], " ".join(paras[:2])):
        tail = re.split(r"[—–]|\s-+\s?|\"\s*-", head)[-1][-60:]
        # "PSALM xc. 1" -> "Psalm xc. 1"; "Galatians, iv. 24" -> "Galatians iv. 24"; "cxHii" -> "cxlii"
        tail = re.sub(r"\b([1-3I]{0,3}\s?)([A-Z]{3,})\b", lambda m: m.group(1) + m.group(2).title(), tail)
        tail = re.sub(r"([A-Za-z])\s*,\s*(?=[ivxlcIVXLC\d])", r"\1 ", tail)
        tail = re.sub(r"\b([ivxlcIVXLCH]{1,8})\.(?=\s?\d)", lambda m: m.group(1).lower().replace("h", "l") + ".", tail)
        refs = parse_free_refs(normalize_refs(tail))
        if refs:
            return head, refs
    return paras[0], []


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
    con = db.connect()
    fixer = WordFixer(build_vocab(con))
    wanted = {norm(t): t for t in SELECTION}
    found = {}
    fetched_all = []
    for ident, desc in VOLUMES:
        fetched = fetch(DL.format(id=ident), "archive", f"{ident}.txt")
        fetched_all.append((fetched, desc))
        for title, body in split_sermons(open(fetched["path"], encoding="utf-8", errors="replace").read()):
            if listing:
                print(f"{ident}: {title}")
                continue
            key = norm(fixer.fix_text(title))
            if norm(title) in ALIASES:
                key = norm(ALIASES[norm(title)])
            match = difflib.get_close_matches(key, list(wanted), n=1, cutoff=0.88)
            if match and (match[0] not in found or len(body) > len(found[match[0]][2])):
                found[match[0]] = (wanted[match[0]], ident, body)
    if listing:
        return {}
    wid = db.upsert_work(
        con, CODE, "Selected Sermons of C. H. Spurgeon (preached 1855-1859)", "sermon",
        [("C. H. Spurgeon", "author", dict(sort_name="Spurgeon, Charles Haddon", born="1834", died="1892",
          description="English Baptist preacher at New Park Street Chapel and the Metropolitan Tabernacle, "
                      "London; 'Prince of Preachers'."))],
        "Public Domain", short_title="Spurgeon's Sermons",
        original_date="Preached 1855-1859; American editions from 1857",
        edition="American printings scanned on archive.org (see provenance rows); OCR text cleaned by "
                "ingest/spurgeon.py",
        source_name="Internet Archive (New York Public Library and University of Toronto scans)",
        source_url="https://archive.org/details/sermonsofrevchsp01spur",
        license_evidence="19th-century American printings, public domain in the US; the archive.org records mark "
                         "these scans NOT_IN_COPYRIGHT. Not taken from CCEL or from modern re-typeset "
                         "compilations.",
        coverage=f"{len(found)} of Spurgeon's best-known early sermons (selection, not the full set)",
        known_issues="Text comes from OCR and was cleaned automatically: expect occasional misspelt words. "
                     "Hymn verses quoted in the sermons are kept as paragraphs.",
        ingest_script="ingest/spurgeon.py")
    for fetched, desc in fetched_all:
        db.add_provenance(con, wid, fetched, notes=desc)
    index = kjv_shingles(con)
    w = db.EntryWriter(con, wid)
    report = []
    for key in [norm(t) for t in SELECTION]:
        if key not in found:
            report.append((wanted[key], "NOT FOUND"))
            continue
        title, ident, body = found[key]
        paras = clean_body(title, body, fixer)
        head, parsed_refs = text_reference(paras)
        text_refs = parse_free_refs(SERMON_TEXTS[title])
        if parsed_refs and parsed_refs[0][0] != text_refs[0][0]:
            report.append((title, f"note: OCR text line read as {format_ref(parsed_refs[0][0])}; "
                                  f"hand-checked text {SERMON_TEXTS[title]} used"))
        chunks = parts(paras)
        for k, chunk in enumerate(chunks, 1):
            text = "\n\n".join(chunk)
            refs = [(s, e, "about", "text_parse", "sermon text") for s, e, _ in text_refs]
            refs += [(s, e, "cites", "text_parse", t[:120]) for s, e, t in parse_free_refs(text)]
            refs += [(v, v, "cites", "quotation_match", f"quotes: {q} ...") for v, q in quoted_verses(text, index).items()]
            t = title if len(chunks) == 1 else f"{title} (part {k} of {len(chunks)})"
            w.add("sermon", f"{key[:80]}#{k}", t, text, refs)
        report.append((title, f"{sum(len(p.split()) for p in paras)} words, text "
                              f"{', '.join(format_ref(s, e) for s, e, _ in text_refs) or 'not recognised'}"))
    w.flush()
    out = dict(sermons=len(found), entries=w.n_entries, scripture_links=w.n_refs,
               missing=[t for t, r in report if r == "NOT FOUND"])
    db.log_ingest(con, "ingest/spurgeon.py", CODE, started, out)
    con.commit()
    for t, r in report:
        print(f"  {t}: {r}")
    print(out)
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
