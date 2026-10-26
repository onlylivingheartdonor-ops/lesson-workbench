"""Ingest Strong's Hebrew and Greek dictionaries (CrossWire StrongsHebrew,
StrongsGreek modules) into `strongs` and as lexicon entries.

Run:  python3 -m ingest.strongs   (after ingest.bibles, which supplies the verse->word links)
"""

import re

from library import db
from library.crosswire import MODULE_PAGE, edition, get_module, license_evidence
from library.markup import to_text

STRONG = ("James Strong", "author", dict(sort_name="Strong, James", born="1822", died="1894",
          description="American Methodist scholar; compiled Strong's Exhaustive Concordance (1890), whose "
                      "numbered Hebrew and Greek dictionaries are the standard key to original-language words."))


def parse_greek(key, body):
    num = int(re.sub(r"\D", "", key) or 0)
    lemma = re.search(r"<orth>([^<]*)</orth>", body)
    translit = re.search(r'<orth[^>]*type="trans"[^>]*>([^<]*)</orth>', body)
    pron = re.search(r"<pron[^>]*>\{?([^<}]*)\}?</pron>", body)
    d = re.search(r"<def>(.*?)</def>", body, re.S)
    definition = to_text(d.group(1) if d else body)
    definition = re.sub(r"\n?see GREEK for \d+", "", definition).strip()
    definition = re.sub(r"\s+", " ", definition)
    usage = None
    if ":--" in definition:
        definition, usage = definition.split(":--", 1)
    elif "--" in definition:
        definition, usage = definition.rsplit("--", 1)
    return num, (lemma.group(1).strip() if lemma else None), (translit.group(1).strip() if translit else None), \
        (pron.group(1).strip() if pron else None), definition.strip(" ;"), (usage.strip(" .") if usage else None)


def parse_hebrew(key, body):
    num = int(re.sub(r"\D", "", key) or 0)
    text = body.replace("\r", "")
    lines = text.strip("\n").split("\n")
    head = lines[0].split()
    translit = head[1] if len(head) > 1 else None
    pron = head[2] if len(head) > 2 else None
    rest = re.sub(r"\s+", " ", " ".join(lines[1:])).strip()
    usage = None
    if ":--" in rest:
        rest, usage = rest.split(":--", 1)
    return num, None, translit, pron, rest.strip(" ;"), (usage.strip(" .") if usage else None)


WORKS = [
    ("StrongsHebrew", "STRONGS-H", "Strong's Hebrew Dictionary", "H", "Hebrew", parse_hebrew,
     "Old Testament (Hebrew and Aramaic words, H1-H8674)",
     "This edition gives the Hebrew words in transliteration only (no Hebrew script)."),
    ("StrongsGreek", "STRONGS-G", "Strong's Greek Dictionary", "G", "Greek", parse_greek,
     "New Testament (Greek words, G1-G5624)", None),
]


def main():
    started = db.now()
    con = db.connect()
    out = {}
    for mod, code, title, prefix, lang, parser, coverage, issues in WORKS:
        fetched, conf, reader = get_module(mod)
        wid = db.upsert_work(con, code, title, "lexicon", [STRONG], "Public Domain", short_title=f"Strong's {lang}",
                             original_date="1890", edition=edition(mod, conf), source_name="CrossWire Bible Society",
                             source_url=MODULE_PAGE + mod, license_evidence=license_evidence(mod, conf),
                             coverage=coverage, known_issues=issues, ingest_script="ingest/strongs.py")
        db.add_provenance(con, wid, fetched)
        con.execute("DELETE FROM strongs WHERE language=?", (lang,))
        w = db.EntryWriter(con, wid)
        rows = []
        for key, body in reader():
            num, lemma, translit, pron, definition, usage = parser(key, body)
            if num == 0:
                continue  # front matter
            number = f"{prefix}{num}"
            title_txt = f"{number} {translit or ''}".strip() + (f" ({lemma})" if lemma else "")
            text = definition + (f"\n\nKJV usage: {usage}" if usage else "")
            eid = w.add("lexicon", number, title_txt, text)
            rows.append((number, lang, lemma, translit, pron, definition, usage, eid))
        w.flush()
        con.executemany("INSERT OR REPLACE INTO strongs(number, language, lemma, transliteration, pronunciation, "
                        "definition, kjv_usage, entry_id) VALUES (?,?,?,?,?,?,?,?)", rows)
        linked = con.execute("SELECT COUNT(DISTINCT strongs) FROM verse_words WHERE strongs LIKE ? "
                             "AND strongs IN (SELECT number FROM strongs)", (prefix + "%",)).fetchone()[0]
        unknown = con.execute("SELECT COUNT(DISTINCT strongs) FROM verse_words WHERE strongs LIKE ? "
                              "AND strongs NOT IN (SELECT number FROM strongs)", (prefix + "%",)).fetchone()[0]
        out[code] = dict(entries=w.n_entries, numbers_used_in_kjv_and_defined=linked,
                         numbers_used_in_kjv_not_in_lexicon=unknown)
        db.log_ingest(con, "ingest/strongs.py", code, started, out[code])
    con.commit()
    for k, v in out.items():
        print(k, v)
    return out


if __name__ == "__main__":
    main()
