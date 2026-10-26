"""Convert SWORD module markup (OSIS, ThML, TEI) to plain text and pull out
scripture references.

Reference resolution
--------------------
Source editions mark references in three ways:
  <reference osisRef="Matt.6.14">Mt 6:14</reference>     (OSIS)
  <ref osisRef="Bible:Rev.1.8">Rev. 1:8</ref>             (TEI)
  <scripRef passage="Mt 6:14">...</scripRef>              (ThML)

Follow-on references are often abbreviated ("Rev. 1:8, 11; 21:6").  Some
editions resolve those wrongly in their markup (the CrossWire Easton's tags
the "11" above as Gen.1.11).  So when a machine-generated osisRef points at
a different book than the list it directly continues, the visible text wins.
Hand-written ThML passage="..." attributes (Smith's, Barnes) are trusted as
given.  Every override is counted so the report can say how many were
corrected.
"""

import html
import re

from library.scripture import (BOOK_NAME, book_from_name, book_last_chapter, chapter_last_verse, is_valid, parse_free_refs,
                               parse_osis_ref, split_vid, vid)

# ---------------------------------------------------------------------------
# Headwords
# ---------------------------------------------------------------------------

SMALL = {"of", "the", "and", "in", "to", "a", "an", "by", "for", "on", "with", "at", "from", "as", "or", "is"}


def nice_name(s):
    """'SIN, FORGIVENESS OF' -> 'Sin, Forgiveness of'; keeps hyphenated names tidy."""
    words = re.split(r"(\s+|-)", s.strip().lower())
    out = []
    for i, w in enumerate(words):
        if w and not w.isspace() and w != "-" and (i == 0 or w not in SMALL):
            w = w[0].upper() + w[1:]
        out.append(w)
    return "".join(out)


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------

_BREAK_TAGS = re.compile(
    r"<(?:br|lb)\s*/?>|</?p\b[^>]*>|<div\b[^>]*type=\"(?:x-p|paragraph)\"[^>]*/>|</?(?:div|li|item|ol|ul|list|"
    r"title|h\d|table|tr|def|entryFree)\b[^>]*>|<milestone\b[^>]*type=\"x-p\"[^>]*/>", re.I)
_NOTE = re.compile(r"<note\b[^>]*>(.*?)</note>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def to_text(markup):
    s = markup.replace("\r", "")
    # Footnotes are kept, in brackets, where they occur.
    s = _NOTE.sub(lambda m: " [" + _TAG.sub("", m.group(1)).strip() + "] ", s)
    s = re.sub(r"<title\b[^>]*>", "\n\n", s, flags=re.I)
    s = re.sub(r"</title>", "\n\n", s, flags=re.I)
    s = re.sub(r"<(?:li|item)\b[^>]*>", "\n", s, flags=re.I)
    s = _BREAK_TAGS.sub("\n", s)
    s = _TAG.sub("", s)
    s = html.unescape(s)
    s = s.replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    # Collapse runs of blank lines into paragraph breaks.
    out, blank = [], False
    for ln in lines:
        if not ln:
            blank = True
            continue
        if out and blank:
            out.append("")
        out.append(ln)
        blank = False
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# Reference lists ("Job 26:7; Isa 45:18; 104:30", "8,13,19")
# ---------------------------------------------------------------------------

_BOOK_PREFIX = re.compile(r"^((?:[1-3]|I{1,3})?\s?[A-Za-z][A-Za-z]*\.?(?:\s+of\s+(?:Solomon|Songs))?)\s*(.*)$")
_ITEM = re.compile(r"^(\d+)(?:[:.](\d+))?(?:\s*[-–]\s*(\d+)(?:[:.](\d+))?)?[a-z]?$")


def parse_ref_list(text, book=None, chapter=None, first_is_verse=None):
    """Parse a citation list using the usual conventions: ';' separates
    chapters, ',' separates verses, a book name carries forward.

    Returns (refs, book, chapter) where refs is [(start_vid, end_vid)] and
    the returned book/chapter are the context after the last reference.
    """
    refs = []
    text = text.replace("—", "-").replace(" and ", ", ")
    segments = [seg.strip() for seg in text.split(";")]
    for si, seg in enumerate(segments):
        if not seg:
            continue
        m = _BOOK_PREFIX.match(seg)
        seg_has_book = False
        if m:
            b = book_from_name(m.group(1))
            if b:
                book, seg, seg_has_book = b, m.group(2), True
                chapter = None
            elif not seg[0].isdigit():
                continue  # not a reference
        if book is None:
            continue
        verse_mode = False
        if si == 0 and not seg_has_book and chapter is not None:
            verse_mode = first_is_verse if first_is_verse is not None else True
        for item in [x.strip() for x in seg.split(",")]:
            if not item:
                continue
            im = _ITEM.match(item.replace(" ", ""))
            if not im:
                break
            a, b2, c, d = im.groups()
            a = int(a)
            if b2 is not None:  # ch:v[-v | -ch:v]
                chapter, v1 = a, int(b2)
                if not is_valid(book, chapter, v1):
                    break
                if c is not None and d is not None:
                    end = vid(book, int(c), int(d))
                elif c is not None:
                    end = vid(book, chapter, int(c))
                else:
                    end = vid(book, chapter, v1)
                start = vid(book, chapter, v1)
                verse_mode = True
            elif verse_mode and chapter is not None:  # verse[-verse] in current chapter
                if not is_valid(book, chapter, a):
                    break
                start = vid(book, chapter, a)
                end = vid(book, chapter, int(c)) if c is not None else start
            elif book_last_chapter(book) == 1:  # "Jude 14", "Phm 10-18": one-chapter books cite verses
                chapter = 1
                if not is_valid(book, 1, a):
                    break
                start = vid(book, 1, a)
                end = vid(book, 1, int(c)) if c is not None else start
                verse_mode = True
            else:  # whole chapter(s)
                if not is_valid(book, a, 0):
                    break
                chapter = a
                last_ch = int(c) if c is not None else a
                start = vid(book, a, 0)
                end = vid(book, last_ch, chapter_last_verse(book, last_ch))
            if end < start or not is_valid(*split_vid(end)):
                end = start
            refs.append((start, end))
    return refs, book, chapter


# ---------------------------------------------------------------------------
# Reference extraction from markup
# ---------------------------------------------------------------------------

_REF_TAG = re.compile(
    r"<(reference|ref|scripRef)\b([^>]*)>(.*?)</\1>|<scripRef\b([^>]*)/>", re.I | re.S)
_ATTR = re.compile(r"(osisRef|passage)\s*=\s*\"([^\"]*)\"", re.I)


class RefStats:
    def __init__(self):
        self.tags = 0
        self.resolved = 0
        self.corrected = 0          # markup attribute disagreed with visible text; text used
        self.unresolved = 0
        self.free_text = 0
        self.examples = []          # a few (visible text, markup attribute, chosen) samples of corrections

    def as_dict(self):
        return dict(ref_tags=self.tags, ref_tags_resolved=self.resolved, ref_tags_corrected=self.corrected,
                    ref_tags_unresolved=self.unresolved, free_text_refs=self.free_text)


def _attr_refs(attrs, book, chapter):
    m = _ATTR.findall(attrs or "")
    for name, value in m:
        if name.lower() == "osisref":
            value = re.sub(r"\b[A-Za-z]+:", "", value)  # strip "Bible:" work prefixes
            r = parse_osis_ref(value)
            if r:
                return r
        else:
            r, _, _ = parse_ref_list(value, book, chapter)
            if r:
                return r
    return []


def extract_refs(markup, book=None, chapter=None, stats=None, free_text=True):
    """Return [(start_vid, end_vid, method, ref_text)] for a markup fragment.

    `book`/`chapter` give the starting context (e.g. the verse a commentary
    note belongs to) so that relative references like "8:22" resolve.
    """
    stats = stats or RefStats()
    out = []
    last_end = 0
    tag_spans = []
    for m in _REF_TAG.finditer(markup):
        attrs = m.group(2) if m.group(1) else m.group(4)
        if re.search(r'target="(?!Bible:)', attrs or ""):
            continue  # a pointer to another dictionary entry, not scripture
        stats.tags += 1
        inner = _TAG.sub("", m.group(3) or "").strip()
        inner = html.unescape(inner)
        # "<ref>Phm 1</ref>:10-18": the rest of the reference sits just after the tag.
        tail = re.match(r":\d+(?:\s*[-\u2013]\s*\d+)?", markup[m.end():])
        if tail and inner and not re.search(r"[:.]\d+\s*$", inner):
            inner += tail.group(0)
        between = _TAG.sub("", markup[last_end:m.start()])
        last_end = m.end()
        tag_spans.append((m.start(), m.end()))
        sep_only = re.fullmatch(r"[\s,;.:]*", between) is not None
        first_is_verse = None
        if sep_only and ";" in between:
            first_is_verse = False
        elif sep_only and "," in between:
            first_is_verse = True
        disp, nbook, nchap = parse_ref_list(inner, book, chapter, first_is_verse) if inner else ([], book, chapter)
        has_book = bool(inner) and bool(_BOOK_PREFIX.match(inner)) and book_from_name(_BOOK_PREFIX.match(inner).group(1)) is not None
        attr = _attr_refs(attrs, book, chapter)
        # ThML passage="de 9:20" attributes are written by hand with the book
        # name and are trusted; osisRef attributes were generated by conversion
        # software and are only overridden for a list continuation ("1:8, 11").
        hand_made = bool(re.search(r'passage\s*=\s*"\s*[1-3]?\s?[A-Za-z]', attrs or ""))
        chosen = None
        if has_book and disp:
            chosen = disp
        elif hand_made and attr:
            chosen = attr
        elif disp and attr:
            same_book = split_vid(attr[0][0])[0] == split_vid(disp[0][0])[0]
            if same_book or not sep_only:
                chosen = attr
            else:
                chosen = disp
                stats.corrected += 1
                if len(stats.examples) < 25:
                    stats.examples.append((inner, attrs.strip(), chosen))
        elif attr:
            chosen = attr
        elif disp:
            chosen = disp
        if not chosen:
            stats.unresolved += 1
            continue
        stats.resolved += 1
        for s, e in chosen:
            out.append((s, e, "source_markup", inner[:120] or None))
        # Update context from what was chosen.
        b, c, v = split_vid(chosen[-1][1])
        book, chapter = b, c
    if free_text:
        # References written in plain text (outside any reference tag).
        plain = []
        pos = 0
        for a, b in tag_spans:
            plain.append(markup[pos:a])
            pos = b
        plain.append(markup[pos:])
        txt = html.unescape(_TAG.sub(" ", " ".join(plain)))
        for s, e, t in parse_free_refs(txt):
            stats.free_text += 1
            out.append((s, e, "text_parse", t[:120]))
    return out

