"""Clean-up tools for OCR text from scanned 19th-century books (archive.org).

* paragraphs(): split the raw OCR text into blank-line-separated blocks and
  join each block's lines, re-joining words hyphenated across line breaks.
* WordFixer: repairs common OCR letter confusions ("tliere" -> "there",
  "Avliich" -> "which", "LoED" -> "LORD") but only when the repaired word is
  a known English word and the damaged one is not.  The vocabulary comes from
  the clean commentary texts already in the database.
* normalize_refs(): repairs OCR damage in scripture references
  ("Ps. Ixxx. 1" -> "Ps. lxxx. 1", "Tsa. xl." -> "Isa. xl.").
* KjvMatcher: says how much of a block is printed KJV text, so the Bible text
  printed above the notes can be dropped.
"""

import json
import os
import re
from collections import Counter

from library.db import ROOT

VOCAB_CACHE = os.path.join(ROOT, "raw", "ocr_vocab.json")

# (damaged, repaired) letter sequences typical of these scans
CONFUSIONS = [
    ("li", "h"), ("Li", "H"), ("li", "ll"), ("il", "ll"), ("tli", "th"), ("Tli", "Th"), ("Av", "W"), ("av", "w"), ("v.'", "w"), ("rn", "m"),
    ("ii", "u"), ("ii", "n"), ("in", "m"), ("ri", "n"), ("ni", "m"), ("cl", "d"), ("ti", "ff"), ("fi", "ff"),
    ("I", "l"), ("l", "I"), ("1", "l"), ("0", "o"), ("c", "e"), ("e", "c"), ("o", "e"), ("u", "n"), ("n", "u"),
    ("Il", "R"), ("E", "R"), ("Ii", "R"), ("J", "I"), ("t", "f"), ("f", "t"), ("h", "b"), ("b", "h"),
    ("vv", "w"), ("VV", "W"), ("ij", "y"), ("Ji", "h"), ("7i", "h"), ("T7i", "Th"), ("tv", "w"), ("ui", "m"), ("iu", "m"), ("j", "i"), ("y", "v"), ("v", "y"), ("s", "e"),
]


def build_vocab(con, work_codes=("CLARKE", "MHC", "JFB", "BARNES", "EASTON", "SMITH", "ISBE")):
    if os.path.exists(VOCAB_CACHE):
        return Counter(json.load(open(VOCAB_CACHE)))
    vocab = Counter()
    q = f"SELECT e.body FROM entries e JOIN works w ON w.id = e.work_id WHERE w.code IN ({','.join('?' * len(work_codes))})"
    for (body,) in con.execute(q, work_codes):
        vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", body))
    for (text,) in con.execute("SELECT b.text FROM bible_text b JOIN works w ON w.id=b.work_id WHERE w.code='KJV'"):
        vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", text))
    vocab = Counter({w: n for w, n in vocab.items() if n >= 3})
    os.makedirs(os.path.dirname(VOCAB_CACHE), exist_ok=True)
    json.dump(vocab, open(VOCAB_CACHE, "w"))
    return vocab


class WordFixer:
    def __init__(self, vocab):
        self.vocab = vocab
        self.cache = {}
        self.fixed = 0

    def known(self, w):
        return self.vocab.get(w.lower(), 0)

    def fix(self, w):
        if w in self.cache:
            return self.cache[w]
        out = w
        if len(w) >= 3 and not self.known(w):
            best, best_n = None, 0
            cands = set()
            for bad, good in CONFUSIONS:
                start = w.find(bad)
                while start >= 0:
                    cands.add(w[:start] + good + w[start + len(bad):])
                    start = w.find(bad, start + 1)
            # two independent confusions ("tliem" -> "them" needs one; "Avliich" needs two)
            for c in list(cands):
                for bad, good in CONFUSIONS[:12]:
                    i = c.find(bad)
                    if i >= 0:
                        cands.add(c[:i] + good + c[i + len(bad):])
            for c in cands:
                n = self.known(c)
                if n > best_n:
                    best, best_n = c, n
            if best and best_n >= 5:
                if w.isupper() and len(w) > 1:
                    best = best.upper()
                elif w[0].isupper():
                    best = best[0].upper() + best[1:]
                out = best
                self.fixed += 1
        self.cache[w] = out
        return out

    def fix_text(self, text):
        text = re.sub(r"\bLo[EB]D\b|\bLOKD\b|\bLOED\b", "LORD", text)
        text = re.sub(r"(?:(?<=\s)|^)/(?=\s?[a-z])", "I", text)   # italic capital I read as "/"
        return re.sub(r"[A-Za-z0-9.']*[A-Za-z][A-Za-z0-9.']*",
                      lambda m: self._fix_token(m.group(0)), text)

    def _fix_token(self, tok):
        core = tok.strip(".'")
        if (not core or core.isdigit() or not re.search(r"[A-Za-z]", core) or "." in core
                or re.fullmatch(r"[IVXLCivxlc]+", core)):
            return tok
        fixed = self.fix(core)
        return tok.replace(core, fixed, 1) if fixed != core else tok


_ROMAN_OCR = re.compile(r"\b([IVXLClivxlc]{1,8})(?=\.\s?\d)")
_BOOKS_OCR = {"Tsa": "Isa", "Isa": "Isa", "Pa": "Ps", "Fs": "Ps", "Prov": "Prov", "Jer": "Jer", "Gen": "Gen",
              "Ex": "Ex", "Matt": "Matt", "Heb": "Heb", "Deut": "Deut", "Rom": "Rom"}


def normalize_refs(text):
    """Repair Roman-numeral chapter numbers damaged by OCR: 'Ixxx.' -> 'lxxx.', 'xxvil.' -> 'xxvii.'."""
    def roman(m):
        r = m.group(1)
        if not any(ch.islower() for ch in r) and len(r) > 1 and not r.startswith("I"):
            return r
        low = r.lower()
        low = re.sub(r"^i(?=x)", "l", low) if low.startswith("ix") and len(low) > 2 else low
        low = re.sub(r"l$", "i", low) if re.fullmatch(r"[xvi]+l", low) else low
        return low
    text = _ROMAN_OCR.sub(roman, text)
    text = re.sub(r"\bTsa\.", "Isa.", text)
    text = re.sub(r"\b[PF]s\.(?=\s?[ivxlc])", "Ps.", text)
    return text


def paragraphs(raw):
    """Blocks of text separated by blank lines, with lines joined and hyphenation repaired."""
    raw = raw.replace("\r", "")
    blocks = re.split(r"\n\s*\n", raw)
    out = []
    for b in blocks:
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in b.split("\n")]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        text = ""
        for ln in lines:
            if text.endswith("-") and ln[:1].islower():
                text = text[:-1] + ln
            elif text.endswith("- ") and ln[:1].islower():
                text = text[:-2] + ln
            else:
                text = (text + " " + ln) if text else ln
        out.append(text)
    return out


_JUNK = re.compile(r"[\^{}|\\~=<>@#$\u2122\u00a3\u00a2\u00ae\u00a9]|[a-z][A-Z]{2,}[a-z]|\)\.?[a-z]|[a-z]\)[a-z]")


def strip_garble(text):
    """Replace runs of unreadable tokens (OCR of Greek/Hebrew type) with a marker."""
    toks = text.split(" ")
    out, junk = [], 0
    for t in toks:
        if _JUNK.search(t) or (len(t) > 2 and sum(not c.isalnum() for c in t.strip(".,;:'\"()")) >= 2):
            junk += 1
            continue
        if junk:
            out.append("[...]" if junk >= 1 else "")
            junk = 0
        out.append(t)
    if junk:
        out.append("[...]")
    return " ".join(x for x in out if x)


def clean_marks(text):
    """OCR renders the pilcrow before each phrase note as '^', 'Tf', 'IT', "'I" etc."""
    text = re.sub(r"(?:(?<=\s)|^)(?:\^|Tf|IT|\*\[|%|'I|1\[)\s+(?=[A-Z])", "¶ ", text)
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    text = text.replace(" ,", ",")
    return re.sub(r"\s{2,}", " ", text).strip()


class KjvMatcher:
    """Fraction of a block's word pairs that occur in a KJV chapter."""

    def __init__(self, con):
        self.chapters = {}
        for vid, text in con.execute("SELECT b.verse_id, b.text FROM bible_text b JOIN works w ON w.id=b.work_id "
                                     "WHERE w.code='KJV'"):
            key = vid // 1000
            ws = re.findall(r"[a-z]+", text.lower().replace("[", "").replace("]", ""))
            s = self.chapters.setdefault(key, set())
            s.update(zip(ws, ws[1:]))

    def share(self, text, book, chapter):
        ws = re.findall(r"[a-z]+", text.lower())
        pairs = list(zip(ws, ws[1:]))
        if len(pairs) < 3:
            return 0.0
        grams = set()
        for c in (chapter - 1, chapter, chapter + 1):
            grams |= self.chapters.get(book * 1000 + c, set())
        return sum(1 for p in pairs if p in grams) / len(pairs)
