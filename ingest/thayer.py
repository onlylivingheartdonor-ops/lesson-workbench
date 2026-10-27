"""Fill the Strong's Greek numbers missing from the CrossWire Strong's Greek
dictionary with entries from Thayer's Greek-English Lexicon (1889).

The 31 entries in ingest/data/thayer_supplement.tsv were transcribed by hand
from the University of Toronto scan of the 1889 American Book Company printing
(archive.org item greekenglishlexi00grimuoft): the OCR garbles Greek, so the
Greek headwords were supplied by the transcriber and the English definitions
were cleaned line by line against the scan.  Very long articles are excerpted
(marked "[Excerpt.]").  "KJV usage" is computed from the KJV word tags.

Run after ingest.strongs:   python3 -m ingest.thayer
"""

import csv
import os

from library import db
from library.fetch import fetch

ITEM = "greekenglishlexi00grimuoft"
URL = f"https://archive.org/download/{ITEM}/greekenglishlexi00grimuoft_djvu.txt"
DATA = os.path.join(db.ROOT, "ingest", "data", "thayer_supplement.tsv")
CODE = "THAYER-SUPP"


def main():
    started = db.now()
    fetched = fetch(URL, "archive", f"{ITEM}.txt")
    con = db.connect()
    wid = db.upsert_work(
        con, CODE, "Thayer's Greek-English Lexicon of the New Testament (supplement to Strong's Greek)", "lexicon",
        [("Joseph Henry Thayer", "translator and editor", dict(
            sort_name="Thayer, Joseph Henry", born="1828", died="1901",
            description="American New Testament scholar (Harvard); translated and enlarged Grimm's Wilke's "
                        "Clavis Novi Testamenti as A Greek-English Lexicon of the New Testament (1886/1889)."))],
        "Public Domain", short_title="Thayer's (supplement)", original_date="1889 (corrected edition)",
        edition="A Greek-English Lexicon of the New Testament, being Grimm's Wilke's Clavis Novi Testamenti, "
                "New York: American Book Company, 1889; University of Toronto scan on archive.org "
                f"({ITEM}); 31 entries hand-transcribed from the OCR text",
        source_name="Internet Archive (University of Toronto Libraries scan)",
        source_url=f"https://archive.org/details/{ITEM}",
        license_evidence="Published in New York in 1889, so in the public domain in the United States; the "
                         "archive.org record marks it NOT_IN_COPYRIGHT.",
        coverage="31 Strong's Greek numbers used in the KJV but missing from the CrossWire Strong's Greek module",
        known_issues="Excerpts only for long articles; Greek headwords supplied by the transcriber because the "
                     "scan's OCR does not read Greek; Greek words inside definitions are given in "
                     "transliteration or omitted.",
        ingest_script="ingest/thayer.py")
    db.add_provenance(con, wid, fetched)
    w = db.EntryWriter(con, wid)
    rows = list(csv.DictReader(open(DATA, encoding="utf-8"), delimiter="\t"))
    strongs_rows = []
    for r in rows:
        if con.execute("SELECT 1 FROM strongs WHERE number=? AND entry_id IN "
                       "(SELECT id FROM entries WHERE work_id != ?)", (r["number"], wid)).fetchone():
            continue  # Strong's itself now has it
        usage = ", ".join(f"{word} ({n})" for word, n in con.execute(
            "SELECT lower(word), COUNT(*) FROM verse_words WHERE strongs=? GROUP BY lower(word) "
            "ORDER BY 2 DESC LIMIT 8", (r["number"],)))
        title = f"{r['number']} {r['transliteration']} ({r['lemma']})"
        body = r["definition"] + (f"\n\nKJV renderings (from the KJV's Strong's tags): {usage}" if usage else "")
        eid = w.add("lexicon", r["number"], title, body)
        strongs_rows.append((r["number"], "Greek", r["lemma"], r["transliteration"], None, r["definition"],
                             usage or None, eid))
    w.flush()
    con.executemany("INSERT OR REPLACE INTO strongs(number, language, lemma, transliteration, pronunciation, "
                    "definition, kjv_usage, entry_id) VALUES (?,?,?,?,?,?,?,?)", strongs_rows)
    missing = con.execute("SELECT COUNT(DISTINCT strongs) FROM verse_words WHERE strongs LIKE 'G%' "
                          "AND strongs NOT IN (SELECT number FROM strongs)").fetchone()[0]
    out = dict(entries=w.n_entries, greek_numbers_still_missing=missing)
    db.log_ingest(con, "ingest/thayer.py", CODE, started, out)
    con.commit()
    print(out)
    return out


if __name__ == "__main__":
    main()
