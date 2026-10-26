"""Canonical scripture scheme for the library.

Every scripture reference in the database is normalized to the 66-book
Protestant canon using KJV chapter/verse numbering (the scheme used by
Nave's, the Treasury of Scripture Knowledge, Strong's and the SWORD
commentaries).  A verse is stored as one integer:

    verse_id = book_number * 1_000_000 + chapter * 1_000 + verse

so a passage range is simply (start_verse_id, end_verse_id) and
"does this range contain Gen 3:15?" is an integer BETWEEN test that works
the same in SQLite and PostgreSQL.  Verse 0 is used for "whole chapter"
references (e.g. "Psalm 23" -> 19023000 .. 19023999 after expansion).
"""

import re

# (number, OSIS id, USFM code, VPL/BibleWorks code, display name, extra abbreviations)
BOOKS = [
    (1, "Gen", "GEN", "GEN", "Genesis", ["ge", "gn", "gen"]),
    (2, "Exod", "EXO", "EXO", "Exodus", ["ex", "exo", "exod"]),
    (3, "Lev", "LEV", "LEV", "Leviticus", ["le", "lv", "lev"]),
    (4, "Num", "NUM", "NUM", "Numbers", ["nu", "nm", "num"]),
    (5, "Deut", "DEU", "DEU", "Deuteronomy", ["de", "dt", "deu", "deut"]),
    (6, "Josh", "JOS", "JOS", "Joshua", ["jos", "josh", "jsh"]),
    (7, "Judg", "JDG", "JDG", "Judges", ["jdg", "jud", "judg", "jg"]),
    (8, "Ruth", "RUT", "RUT", "Ruth", ["ru", "rut", "rth"]),
    (9, "1Sam", "1SA", "1SA", "1 Samuel", ["1sa", "1sam", "1sm", "isam", "1samuel", "isamuel"]),
    (10, "2Sam", "2SA", "2SA", "2 Samuel", ["2sa", "2sam", "2sm", "iisa", "iisam", "2samuel", "iisamuel"]),
    (11, "1Kgs", "1KI", "1KI", "1 Kings", ["1ki", "1kg", "1kgs", "1kin", "iki", "ikgs", "ikings", "1kings"]),
    (12, "2Kgs", "2KI", "2KI", "2 Kings", ["2ki", "2kg", "2kgs", "2kin", "iiki", "iikgs", "iikings", "2kings"]),
    (13, "1Chr", "1CH", "1CH", "1 Chronicles", ["1ch", "1chr", "1chron", "ich", "ichr", "ichron", "1chronicles", "ichronicles"]),
    (14, "2Chr", "2CH", "2CH", "2 Chronicles", ["2ch", "2chr", "2chron", "iich", "iichr", "iichron", "2chronicles", "iichronicles"]),
    (15, "Ezra", "EZR", "EZR", "Ezra", ["ezr", "ezra"]),
    (16, "Neh", "NEH", "NEH", "Nehemiah", ["ne", "neh"]),
    (17, "Esth", "EST", "EST", "Esther", ["es", "est", "esth"]),
    (18, "Job", "JOB", "JOB", "Job", ["jb", "job"]),
    (19, "Ps", "PSA", "PSA", "Psalms", ["ps", "psa", "pss", "psalm", "psalms", "psm"]),
    (20, "Prov", "PRO", "PRO", "Proverbs", ["pr", "pro", "prov", "prv"]),
    (21, "Eccl", "ECC", "ECC", "Ecclesiastes", ["ec", "ecc", "eccl", "eccles", "qoh"]),
    (22, "Song", "SNG", "SOL", "Song of Solomon", ["so", "sol", "song", "sng", "canticles", "cant", "ss", "songofsongs", "songofsolomon"]),
    (23, "Isa", "ISA", "ISA", "Isaiah", ["is", "isa", "isai"]),
    (24, "Jer", "JER", "JER", "Jeremiah", ["je", "jer", "jr"]),
    (25, "Lam", "LAM", "LAM", "Lamentations", ["la", "lam"]),
    (26, "Ezek", "EZK", "EZE", "Ezekiel", ["eze", "ezek", "ezk"]),
    (27, "Dan", "DAN", "DAN", "Daniel", ["da", "dan", "dn"]),
    (28, "Hos", "HOS", "HOS", "Hosea", ["ho", "hos"]),
    (29, "Joel", "JOL", "JOE", "Joel", ["joe", "joel", "jl"]),
    (30, "Amos", "AMO", "AMO", "Amos", ["am", "amo"]),
    (31, "Obad", "OBA", "OBA", "Obadiah", ["ob", "oba", "obad"]),
    (32, "Jonah", "JON", "JON", "Jonah", ["jon", "jnh", "jonah"]),
    (33, "Mic", "MIC", "MIC", "Micah", ["mi", "mic"]),
    (34, "Nah", "NAM", "NAH", "Nahum", ["na", "nah", "nam"]),
    (35, "Hab", "HAB", "HAB", "Habakkuk", ["hab", "hb"]),
    (36, "Zeph", "ZEP", "ZEP", "Zephaniah", ["zep", "zeph", "zp"]),
    (37, "Hag", "HAG", "HAG", "Haggai", ["hag", "hg"]),
    (38, "Zech", "ZEC", "ZEC", "Zechariah", ["zec", "zech", "zc"]),
    (39, "Mal", "MAL", "MAL", "Malachi", ["mal", "ml"]),
    (40, "Matt", "MAT", "MAT", "Matthew", ["mt", "mat", "matt"]),
    (41, "Mark", "MRK", "MAR", "Mark", ["mk", "mr", "mar", "mrk"]),
    (42, "Luke", "LUK", "LUK", "Luke", ["lk", "lu", "luk"]),
    (43, "John", "JHN", "JOH", "John", ["jn", "joh", "jhn"]),
    (44, "Acts", "ACT", "ACT", "Acts", ["ac", "act"]),
    (45, "Rom", "ROM", "ROM", "Romans", ["ro", "rom", "rm"]),
    (46, "1Cor", "1CO", "1CO", "1 Corinthians", ["1co", "1cor", "ico", "icor", "1corinthians", "icorinthians"]),
    (47, "2Cor", "2CO", "2CO", "2 Corinthians", ["2co", "2cor", "iico", "iicor", "2corinthians", "iicorinthians"]),
    (48, "Gal", "GAL", "GAL", "Galatians", ["ga", "gal"]),
    (49, "Eph", "EPH", "EPH", "Ephesians", ["eph", "ep"]),
    (50, "Phil", "PHP", "PHI", "Philippians", ["php", "phil", "phi", "phl"]),
    (51, "Col", "COL", "COL", "Colossians", ["col"]),
    (52, "1Thess", "1TH", "1TH", "1 Thessalonians", ["1th", "1thes", "1thess", "ith", "ithes", "ithess", "1thessalonians", "ithessalonians"]),
    (53, "2Thess", "2TH", "2TH", "2 Thessalonians", ["2th", "2thes", "2thess", "iith", "iithes", "iithess", "2thessalonians", "iithessalonians"]),
    (54, "1Tim", "1TI", "1TI", "1 Timothy", ["1ti", "1tim", "iti", "itim", "1timothy", "itimothy"]),
    (55, "2Tim", "2TI", "2TI", "2 Timothy", ["2ti", "2tim", "iiti", "iitim", "2timothy", "iitimothy"]),
    (56, "Titus", "TIT", "TIT", "Titus", ["tit", "ti"]),
    (57, "Phlm", "PHM", "PHM", "Philemon", ["phm", "phlm", "philem", "phile"]),
    (58, "Heb", "HEB", "HEB", "Hebrews", ["he", "heb"]),
    (59, "Jas", "JAS", "JAM", "James", ["jas", "jam", "jms", "jm"]),
    (60, "1Pet", "1PE", "1PE", "1 Peter", ["1pe", "1pet", "1pt", "ipe", "ipet", "1peter", "ipeter"]),
    (61, "2Pet", "2PE", "2PE", "2 Peter", ["2pe", "2pet", "2pt", "iipe", "iipet", "2peter", "iipeter"]),
    (62, "1John", "1JN", "1JO", "1 John", ["1jo", "1jn", "1joh", "1john", "ijo", "ijn", "ijoh", "ijohn"]),
    (63, "2John", "2JN", "2JO", "2 John", ["2jo", "2jn", "2joh", "2john", "iijo", "iijn", "iijoh", "iijohn"]),
    (64, "3John", "3JN", "3JO", "3 John", ["3jo", "3jn", "3joh", "3john", "iiijo", "iiijn", "iiijoh", "iiijohn"]),
    (65, "Jude", "JUD", "JUD", "Jude", ["jude", "jud", "jde"]),
    (66, "Rev", "REV", "REV", "Revelation", ["re", "rev", "rv", "apoc", "revelation", "revelations"]),
]

BOOK_NUM_BY_OSIS = {b[1]: b[0] for b in BOOKS}
BOOK_NUM_BY_USFM = {b[2]: b[0] for b in BOOKS}
BOOK_NUM_BY_VPL = {b[3]: b[0] for b in BOOKS}
BOOK_NAME = {b[0]: b[4] for b in BOOKS}
BOOK_OSIS = {b[0]: b[1] for b in BOOKS}

# KJV chapter verse counts, used to walk SWORD verse indexes and to clamp
# open-ended ranges.  Generated once from the KJV text by
# ingest/bibles.py and checked into library/kjv_counts.py.
try:
    from library.kjv_counts import KJV_VERSE_COUNTS  # {book: [verses in ch1, ch2, ...]}
except ImportError:  # first bootstrap run, before the KJV is ingested
    KJV_VERSE_COUNTS = None


def _norm(s):
    return re.sub(r"[\s.]", "", s.lower())


ABBREV = {}
for _num, _osis, _usfm, _vpl, _name, _extra in BOOKS:
    for a in [_osis, _usfm, _vpl, _name] + _extra:
        ABBREV[_norm(a)] = _num
# Ambiguous short forms resolved to the most common meaning in these texts.
ABBREV.update({"jud": 7, "judges": 7, "jude": 65, "phil": 50, "php": 50, "ti": 56})
# A handful of older forms seen in 19th-century commentaries.
ABBREV.update({"deu": 5, "joshua": 6, "sa": 9, "sam": 9, "kgs": 11, "chron": 13,
               "eccle": 21, "eccles": 21, "ecclus": None, "wisd": None, "tob": None,
               "macc": None, "1macc": None, "2macc": None, "sir": None, "bar": None,
               "apocalypse": 66, "philemon": 57, "thess": 52, "pet": 60, "cor": 46})


def book_from_name(name):
    """Return the book number for a name/abbreviation, or None."""
    return ABBREV.get(_norm(name))


def vid(book, chapter, verse):
    return book * 1_000_000 + chapter * 1_000 + verse


def split_vid(v):
    return v // 1_000_000, (v // 1_000) % 1_000, v % 1_000


def chapter_last_verse(book, chapter):
    if KJV_VERSE_COUNTS and book in KJV_VERSE_COUNTS and 1 <= chapter <= len(KJV_VERSE_COUNTS[book]):
        return KJV_VERSE_COUNTS[book][chapter - 1]
    return 999


def book_last_chapter(book):
    if KJV_VERSE_COUNTS and book in KJV_VERSE_COUNTS:
        return len(KJV_VERSE_COUNTS[book])
    return 999


def is_valid(book, chapter, verse):
    if not (1 <= book <= 66) or chapter < 1:
        return False
    if KJV_VERSE_COUNTS is None:
        return True
    if chapter > len(KJV_VERSE_COUNTS[book]):
        return False
    return 0 <= verse <= KJV_VERSE_COUNTS[book][chapter - 1]


def format_ref(start, end=None):
    """Human-readable reference, e.g. 'Matthew 6:14-15' or 'Psalms 23'."""
    b, c, v = split_vid(start)
    s = f"{BOOK_NAME[b]} {c}" + (f":{v}" if v else "")
    if end is None or end == start:
        return s
    b2, c2, v2 = split_vid(end)
    if v == 0 and v2 >= chapter_last_verse(b2, c2) and b2 == b:
        # whole-chapter range
        return s if c2 == c else f"{BOOK_NAME[b]} {c}-{c2}"
    if b2 != b:
        return f"{s} - {BOOK_NAME[b2]} {c2}:{v2}"
    if c2 != c:
        return f"{s}-{c2}:{v2}"
    return f"{s}-{v2}"


# ---------------------------------------------------------------------------
# OSIS reference strings ("Matt.6.14-Matt.6.15", "Gen.1", "Ps.23.1 Ps.23.4")
# ---------------------------------------------------------------------------

_OSIS_POINT = re.compile(r"^(?:[A-Za-z0-9]+:)?([1-3]?[A-Za-z]+)\.(\d+)(?:\.(\d+))?(?:![^-\s]*)?$")


def _osis_point(p):
    m = _OSIS_POINT.match(p.strip())
    if not m:
        return None
    book = BOOK_NUM_BY_OSIS.get(m.group(1)) or book_from_name(m.group(1))
    if not book:
        return None
    ch = int(m.group(2))
    vs = int(m.group(3)) if m.group(3) else None
    return book, ch, vs


def parse_osis_ref(osis):
    """Parse an osisRef attribute into a list of (start_vid, end_vid)."""
    out = []
    for part in re.split(r"[\s;,]+", osis.strip()):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            pa = _osis_point(a)
            if not pa:
                continue
            pb = _osis_point(b)
            if not pb:
                # "Gen.1.1-3" style
                if b.isdigit():
                    pb = (pa[0], pa[1], int(b)) if pa[2] is not None else (pa[0], int(b), None)
                else:
                    continue
            start = vid(pa[0], pa[1], pa[2] if pa[2] is not None else 0)
            end_v = pb[2] if pb[2] is not None else chapter_last_verse(pb[0], pb[1])
            end = vid(pb[0], pb[1], end_v)
        else:
            pa = _osis_point(part)
            if not pa:
                continue
            if pa[2] is None:
                start, end = vid(pa[0], pa[1], 0), vid(pa[0], pa[1], chapter_last_verse(pa[0], pa[1]))
            else:
                start = end = vid(*pa)
        if end >= start and is_valid(*split_vid(start)):
            out.append((start, end))
    return out


# ---------------------------------------------------------------------------
# Free-text references ("Mt 6:14, 15; 18:21-35", "Ge 1:1", "Ps. xxiii. 1")
# ---------------------------------------------------------------------------

_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def roman_to_int(s):
    s = s.lower()
    if not s or any(ch not in _ROMAN for ch in s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        val = _ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = max(prev, val)
    return total


_BOOK_TOKEN = r"(?:(?:[1-3]|I{1,3})\s?)?[A-Z][a-z]+\.?"
_NUM = r"(?:\d+|[ivxlc]+)"
_FREE_REF = re.compile(
    r"\b(" + _BOOK_TOKEN + r"(?:\sof\s(?:Solomon|Songs))?)\s+"          # book (allows "Song of Solomon")
    r"(" + _NUM + r")(?:[:.,]\s?(" + _NUM + r"))?"                        # chapter[:verse]
    r"((?:\s?[-–]\s?\d+(?:[:.]\d+)?)?"                                   # -verse or -ch:verse
    r"(?:\s?,\s?\d+(?:\s?[-–]\s?\d+)?(?![:.]\d))*"                       # , verse lists
    r"(?:\s?;\s?\d+[:.]\d+(?:\s?[-–]\s?\d+(?:[:.]\d+)?)?(?:\s?,\s?\d+(?:\s?[-–]\s?\d+)?(?![:.]\d))*)*)"  # ; ch:verse continuations
)


def _to_int(tok):
    if tok is None:
        return None
    if tok.isdigit():
        return int(tok)
    return roman_to_int(tok)


def parse_free_refs(text, default_book=None):
    """Find scripture references in running text.

    Returns a list of (start_vid, end_vid, matched_text).  Only references
    whose book resolves and whose chapter/verse exist in the KJV scheme are
    returned, which filters out most false positives ("Chapter 3", dates).
    """
    out = []
    for m in _FREE_REF.finditer(text):
        book = book_from_name(m.group(1))
        if not book:
            continue
        ch = _to_int(m.group(2))
        vs = _to_int(m.group(3))
        if ch is None:
            continue
        if vs is None and book_last_chapter(book) == 1:  # "Jude 14" = Jude 1:14
            ch, vs = 1, ch
        # Two-letter abbreviations ("He", "Is", "Am") are only trusted with a verse.
        if vs is None and len(_norm(m.group(1))) <= 2:
            continue
        rest = m.group(4) or ""
        refs = []
        if vs is None:
            if not is_valid(book, ch, 0):
                continue
            refs.append((vid(book, ch, 0), vid(book, ch, chapter_last_verse(book, ch))))
        else:
            if not is_valid(book, ch, vs):
                continue
            cur_ch, last = ch, (book, ch, vs)
            start = vid(book, ch, vs)
            end = start
            for tok in re.finditer(r"([-–,;])\s?(\d+)(?:[:.](\d+))?", rest):
                sep, a, b = tok.group(1), int(tok.group(2)), tok.group(3)
                if sep in "-–":
                    if b is not None:
                        cur_ch, v2 = a, int(b)
                    else:
                        v2 = a
                    if is_valid(book, cur_ch, v2):
                        end = vid(book, cur_ch, v2)
                elif sep == ",":
                    refs.append((start, end))
                    if b is not None:
                        cur_ch, a = a, int(b)
                    if is_valid(book, cur_ch, a):
                        start = end = vid(book, cur_ch, a)
                else:  # ";" new chapter:verse in same book
                    refs.append((start, end))
                    if b is not None and is_valid(book, a, int(b)):
                        cur_ch = a
                        start = end = vid(book, a, int(b))
            refs.append((start, end))
        for s, e in refs:
            if e >= s:
                out.append((s, e, m.group(0)))
    # de-duplicate, keep order
    seen, uniq = set(), []
    for r in out:
        if (r[0], r[1]) not in seen:
            seen.add((r[0], r[1]))
            uniq.append(r)
    return uniq


def sword_index_map():
    """Map SWORD KJV-versification verse-index positions to verse ids.

    Returns two dicts {index: vid} for 'ot' and 'nt'.  Index layout per
    testament: 0 = module header, 1 = testament header, then for each book
    a book-intro slot, and for each chapter a chapter-intro slot followed
    by its verses.  Intro slots map to vid(book, 0, 0) / vid(book, ch, 0).
    """
    if KJV_VERSE_COUNTS is None:
        raise RuntimeError("KJV verse counts not generated yet; run ingest.bibles first")
    maps = {}
    for testament, books in (("ot", range(1, 40)), ("nt", range(40, 67))):
        idx = 2
        m = {}
        for b in books:
            m[idx] = vid(b, 0, 0)
            idx += 1
            for c, nverses in enumerate(KJV_VERSE_COUNTS[b], start=1):
                m[idx] = vid(b, c, 0)
                idx += 1
                for v in range(1, nverses + 1):
                    m[idx] = vid(b, c, v)
                    idx += 1
        maps[testament] = m
    return maps


def expand_range(start, end, cap=400):
    """List every verse id in [start, end] (KJV scheme), at most `cap` of them.
    Verse-0 (whole chapter / intro) starts are treated as verse 1."""
    out = []
    b, c, v = split_vid(start)
    b2, c2, v2 = split_vid(end)
    if c == 0:
        c, v = 1, 1
    v = max(v, 1)
    while (b, c) <= (b2, c2) and len(out) < cap:
        last = chapter_last_verse(b, c) if (b, c) != (b2, c2) else min(v2, chapter_last_verse(b, c))
        for x in range(v, last + 1):
            out.append(vid(b, c, x))
            if len(out) >= cap:
                break
        c, v = c + 1, 1
        if c > book_last_chapter(b):
            b, c = b + 1, 1
            if b > 66:
                break
    return out
