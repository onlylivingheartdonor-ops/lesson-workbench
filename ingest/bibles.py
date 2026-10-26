"""Ingest the four Bible translations (KJV, ASV, BBE, WEB) from eBible.org,
the canonical book/verse tables, and the KJV's Strong's-number word tags.

Run:  python3 -m ingest.bibles
"""

import re
import sys
import zipfile

from library import db
from library.fetch import fetch
from library.scripture import BOOKS, BOOK_NUM_BY_USFM, BOOK_NUM_BY_VPL, vid

EBIBLE = "https://ebible.org/Scriptures/"

BIBLES = [
    dict(code="KJV", ebible_id="eng-kjv2006", title="King James Version (Authorized Version)", short_title="KJV",
         original_date="1611; standard text of 1769",
         edition="eBible.org 'eng-kjv2006' (1769 Blayney text, protocanon only, Strong's numbers added), "
                 "text-only VPL edition; Strong's tags from the same edition's USFM files",
         authors=[("King James Version translators", "translator", dict(sort_name="King James translators",
                   born=None, died=None, description="The 47 scholars commissioned by King James I; 1769 standard "
                   "text edited by Benjamin Blayney."))],
         license_evidence="eBible.org catalog: Copyright='public domain', Redistributable=True. About page: "
                          "'You may copy the King James Version of the Holy Bible freely.' Note: Crown letters "
                          "patent restrict printing in the United Kingdom only; public domain elsewhere.",
         known_issues="UK Crown patent applies to printing/importing printed copies in the UK."),
    dict(code="ASV", ebible_id="eng-asv", title="American Standard Version (1901)", short_title="ASV",
         original_date="1901", edition="eBible.org 'eng-asv', text-only VPL edition",
         authors=[("American Revision Committee", "translator", dict(description="American members of the "
                   "committee that produced the Revised Version; published the ASV in 1901."))],
         license_evidence="eBible.org catalog: Copyright='public domain', Redistributable=True. About page: "
                          "'This public domain Bible translation is brought to you courtesy of eBible.org.'"),
    dict(code="BBE", ebible_id="engBBE", title="Bible in Basic English", short_title="BBE",
         original_date="1941 (NT), 1949 (OT); 1965 printing",
         edition="eBible.org 'engBBE', text-only VPL edition",
         authors=[("Samuel Henry Hooke", "translator", dict(sort_name="Hooke, Samuel Henry", born="1874",
                   died="1968", description="English biblical scholar who led the Bible in Basic English "
                   "translation using C. K. Ogden's 850-word Basic English vocabulary."))],
         license_evidence="eBible.org catalog: Copyright='public domain'. About page: 'printed in 1965 by "
                          "Cambridge Press ... Published without any copyright notice and distributed in America, "
                          "this work fell immediately and irretrievably into the Public Domain in the United States.'",
         known_issues="Public-domain status rests on US law (1965 publication without notice); may still be "
                      "under copyright in the UK and some other countries."),
    dict(code="WEB", ebible_id="engwebp", title="World English Bible", short_title="WEB",
         original_date="2000-2020 (ongoing revisions)",
         edition="eBible.org 'engwebp' (World English Bible, protocanon only, uses 'LORD' for the divine name), "
                 "text-only VPL edition",
         authors=[("Michael Paul Johnson", "editor", dict(sort_name="Johnson, Michael Paul",
                   description="Editor of the World English Bible, eBible.org."))],
         license_evidence="eBible.org about page: 'The World English Bible is in the Public Domain ... However, "
                          "\"World English Bible\" is a Trademark of eBible.org ... if you CHANGE the actual text "
                          "... you not call the result the World English Bible any more.'",
         known_issues="Name is a trademark: the text must not be altered if it is called 'World English Bible'. "
                      "Romans 16:25-27 appears at Romans 14:24-26 in this edition and was moved to the KJV "
                      "position."),
]

# Verses that this scheme renumbers to KJV positions: {code: {(book, ch, v): (book, ch, v)}}
REMAP = {"WEB": {(45, 14, 24): (45, 16, 25), (45, 14, 25): (45, 16, 26), (45, 14, 26): (45, 16, 27)}}

VPL_LINE = re.compile(r"^(\w{3}) (\d+):(\d+)\s?(.*)$")


def read_vpl(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith("_vpl.txt")][0]
    text = z.read(name).decode("utf-8-sig")
    for line in text.splitlines():
        m = VPL_LINE.match(line)
        if m:
            yield BOOK_NUM_BY_VPL[m.group(1)], int(m.group(2)), int(m.group(3)), m.group(4).strip()


def write_counts(kjv_path):
    counts = {}
    for b, c, v, _ in read_vpl(kjv_path):
        lst = counts.setdefault(b, [])
        while len(lst) < c:
            lst.append(0)
        lst[c - 1] = max(lst[c - 1], v)
    with open(db.ROOT + "/library/kjv_counts.py", "w") as f:
        f.write('"""KJV verses per chapter (generated from the eBible.org KJV text by ingest/bibles.py)."""\n\n'
                "KJV_VERSE_COUNTS = {\n")
        for b in sorted(counts):
            f.write(f"    {b}: {counts[b]},\n")
        f.write("}\n")
    return counts


_W = re.compile(r"\\\+?w\s+([^|\\]*)\|([^\\]*?)\\\+?w\*")
_STRONG = re.compile(r'strong="([^"]+)"')


def strongs_words(usfm_zip):
    """Yield (verse_id, position, word, strongs) from eBible USFM with \\w word|strong="H0430"\\w* tags."""
    z = zipfile.ZipFile(usfm_zip)
    for name in sorted(z.namelist()):
        if not name.endswith(".usfm"):
            continue
        text = z.read(name).decode("utf-8-sig")
        book = None
        m = re.search(r"^\\id (\w+)", text, re.M)
        if m:
            book = BOOK_NUM_BY_USFM.get(m.group(1))
        if not book:
            continue
        # Walk verse by verse (verses can span lines).
        body = re.sub(r"\\f .*?\\f\*", "", text, flags=re.S)
        for cm in re.finditer(r"\\c (\d+)(.*?)(?=\\c \d+|\Z)", body, re.S):
            chapter = int(cm.group(1))
            for vm in re.finditer(r"\\v (\d+)\s(.*?)(?=\\v \d+\s|\Z)", cm.group(2), re.S):
                verse = int(vm.group(1))
                pos = 0
                for wm in _W.finditer(vm.group(2)):
                    pos += 1
                    word = wm.group(1).strip()
                    for num in _STRONG.findall(wm.group(2)):
                        for n in num.split():
                            n = n.strip()
                            mm = re.match(r"([HG])0*(\d+)([a-z]?)$", n)
                            if mm:
                                yield vid(book, chapter, verse), pos, word, f"{mm.group(1)}{mm.group(2)}{mm.group(3)}"


def main():
    started = db.now()
    files = {b["code"]: fetch(EBIBLE + b["ebible_id"] + "_vpl.zip", "ebible") for b in BIBLES}
    usfm = fetch(EBIBLE + "eng-kjv2006_usfm.zip", "ebible")
    counts = write_counts(files["KJV"]["path"])

    con = db.connect()
    # Canonical books and verses (KJV numbering).
    con.execute("DELETE FROM verses")
    con.execute("DELETE FROM books")
    con.executemany("INSERT INTO books(id, osis, usfm, name, testament, chapters) VALUES (?,?,?,?,?,?)",
                    [(n, osis, usfm_code, name, "OT" if n < 40 else "NT", len(counts[n]))
                     for n, osis, usfm_code, _, name, _ in BOOKS])
    con.executemany("INSERT INTO verses(id, book_id, chapter, verse) VALUES (?,?,?,?)",
                    [(vid(b, c, v), b, c, v) for b in sorted(counts) for c, n in enumerate(counts[b], 1)
                     for v in range(1, n + 1)])
    valid = {r[0] for r in con.execute("SELECT id FROM verses")}

    stats = {}
    for b in BIBLES:
        code = b["code"]
        wid = db.upsert_work(con, code, b["title"], "bible", b["authors"], "Public Domain",
                             short_title=b["short_title"], original_date=b["original_date"], edition=b["edition"],
                             source_name="eBible.org", source_url=f"https://ebible.org/{b['ebible_id']}/",
                             license_evidence=b["license_evidence"], coverage="Old and New Testaments (66 books)",
                             known_issues=b.get("known_issues"), ingest_script="ingest/bibles.py")
        db.add_provenance(con, wid, files[code])
        remap = REMAP.get(code, {})
        rows, skipped_empty, off_scheme = {}, 0, []
        for bk, c, v, t in read_vpl(files[code]["path"]):
            bk, c, v = remap.get((bk, c, v), (bk, c, v))
            if not t:
                skipped_empty += 1
                continue
            key = vid(bk, c, v)
            if key not in valid:
                off_scheme.append(f"{bk}:{c}:{v}")
                continue
            rows[key] = t
        con.executemany("INSERT INTO bible_text(work_id, verse_id, text) VALUES (?,?,?)",
                        [(wid, k, t) for k, t in sorted(rows.items())])
        missing = len(valid) - len(rows)
        stats[code] = dict(verses=len(rows), empty_in_source=skipped_empty, outside_kjv_scheme=off_scheme,
                           kjv_verses_without_text=missing)
        if code == "KJV":
            db.add_provenance(con, wid, usfm, notes="Strong's number tags (verse_words)")
            words = list(strongs_words(usfm["path"]))
            con.executemany("INSERT OR IGNORE INTO verse_words(work_id, verse_id, position, word, strongs) "
                            "VALUES (?,?,?,?,?)", [(wid,) + w for w in words if w[0] in valid])
            stats[code]["strongs_word_links"] = con.execute(
                "SELECT COUNT(*) FROM verse_words WHERE work_id=?", (wid,)).fetchone()[0]
        db.log_ingest(con, "ingest/bibles.py", code, started, stats[code])
    con.commit()
    for k, v in stats.items():
        print(k, v)
    return stats


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
