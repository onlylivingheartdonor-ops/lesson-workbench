"""Ingest Nave's Topical Bible (CrossWire 'Nave' module).

Creates:
  * subjects  - one 'topic' per Nave's heading (5,300+) and one 'subtopic' per
                arrow sub-heading ("FORGIVENESS -> Of enemies")
  * subject_scripture - every verse reference, attached to the most specific
                subject, with Nave's line text as a note
  * subject_relations - Nave's own "See ..." cross-references ('see_also')
  * entries  - each topic's full text as a 'topic' entry (so it is searchable),
               linked structurally to its subject

Run:  python3 -m ingest.naves
"""

import re

from library import db
from library.crosswire import MODULE_PAGE, edition, get_module, license_evidence
from library.markup import RefStats, extract_refs, nice_name, to_text

MOD = "Nave"
CODE = "NAVE"
def sentence_case(s):
    s = s.strip()
    if s.isupper():
        s = s.lower()
    return s[:1].upper() + s[1:]


def split_lines(defn):
    """Yield (kind, markup) lines: kind 'head' for arrow sub-headings, 'item' otherwise."""
    # Make every <lb/> and <item> start a new line.
    s = re.sub(r"<item>", "\n<<ITEM>>", defn)
    s = re.sub(r"<lb/>", "\n<<LB>>", s)
    s = re.sub(r"</?(?:list|item|def)>", "", s)
    for raw in s.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        is_item = raw.startswith("<<ITEM>>")
        raw = raw.replace("<<ITEM>>", "").replace("<<LB>>", "").strip()
        if not raw:
            continue
        if raw.startswith("→"):
            yield "head", raw.lstrip("→").strip()
        elif not is_item and re.match(r"^\d+\.\s", raw):
            yield "head", raw  # numbered persons/places ("1. A son of Ephraim ...")
        else:
            yield "item", raw


def line_label(markup):
    text = to_text(re.sub(r"<ref\b[^>]*>.*?</ref>", " ", markup))
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?:[\s,;.]|:\d+(?:-\d+)?)+$", "", text)   # leftover separators / ":10-18" tails
    text = re.sub(r"\s*[,;](?:\s*[,;:])+\s*", "; ", text)
    text = re.sub(r"^[\s,;:.]+", "", text)
    text = re.sub(r"\s+([,;:.])", r"\1", text)
    return text.replace("' s ", "'s ")


def main():
    started = db.now()
    fetched, conf, reader = get_module(MOD)
    con = db.connect()
    wid = db.upsert_work(
        con, CODE, "Nave's Topical Bible", "topical_index",
        [("Orville J. Nave", "author", dict(sort_name="Nave, Orville James", born="1841", died="1917",
          description="American Methodist minister and US Army chaplain; compiled the Topical Bible "
                      "(1896) over fourteen years."))],
        "Public Domain", short_title="Nave's", original_date="1896", edition=edition(MOD, conf),
        source_name="CrossWire Bible Society", source_url=MODULE_PAGE + MOD,
        license_evidence=license_evidence(MOD, conf), coverage="Whole Bible; 5,300+ topics",
        ingest_script="ingest/naves.py")
    db.add_provenance(con, wid, fetched)

    # Remove previous Nave subjects (and anything hanging off them).
    sub_ids = "SELECT id FROM subjects WHERE source_work_id=?"
    for t in ("subject_relations WHERE subject_id IN ({0}) OR related_subject_id IN ({0})",):
        con.execute("DELETE FROM " + t.format(sub_ids), (wid, wid))
    con.execute(f"DELETE FROM category_topics WHERE topic_id IN ({sub_ids})", (wid,))
    con.execute(f"DELETE FROM spot_checks WHERE entry_subject_id IN (SELECT id FROM entry_subjects WHERE subject_id IN ({sub_ids}))", (wid,))
    con.execute(f"DELETE FROM review_queue WHERE entry_subject_id IN (SELECT id FROM entry_subjects WHERE subject_id IN ({sub_ids}))", (wid,))
    con.execute(f"DELETE FROM link_reviews WHERE entry_subject_id IN (SELECT id FROM entry_subjects WHERE subject_id IN ({sub_ids}) OR id IN (SELECT id FROM entry_subjects WHERE subject_id IN ({sub_ids})))", (wid, wid))
    con.execute(f"DELETE FROM link_reviews WHERE new_subject_id IN ({sub_ids})", (wid,))
    con.execute(f"DELETE FROM entry_subjects WHERE subject_id IN ({sub_ids})", (wid,))
    con.execute("UPDATE subjects SET parent_id=NULL WHERE source_work_id=?", (wid,))
    con.execute("DELETE FROM subjects WHERE source_work_id=?", (wid,))

    stats = RefStats()
    writer = db.EntryWriter(con, wid)
    topic_ids = {}
    see_also = []
    scripture_rows = []
    slugs = set()
    n_sub = 0
    topic_links = []

    def new_subject(name, level, parent, key):
        base = db.slugify(name if parent is None else f"{parent[1]} {name}")
        slug, i = base, 2
        while slug in slugs:
            slug, i = f"{base}-{i}", i + 1
        slugs.add(slug)
        sid = con.execute("INSERT INTO subjects(name, slug, level, parent_id, source_work_id, source_key) "
                          "VALUES (?,?,?,?,?,?)", (name, slug, level, parent[0] if parent else None, wid, key)).lastrowid
        return sid, name

    for key, body in reader():
        m = re.search(r"<def>(.*)</def>", body, re.S)
        if not m:
            continue
        topic_key = key.strip()
        topic = new_subject(nice_name(topic_key), "topic", None, topic_key)
        topic_ids[topic_key] = topic[0]
        current = topic
        pos = 0
        entry_refs = []
        for kind, line in split_lines(m.group(1)):
            label = line_label(line)
            if kind == "head" and re.match(r"^See\b", label or "See"):
                kind = "item"  # "-> See OTHER TOPIC" is a pointer, not a sub-heading
            if kind == "head":
                head_label = re.split(r"\s{2,}|(?<=[a-z])\s(?=[A-Z][a-z]{0,3}\s\d)", label)[0] if label else label
                current = new_subject(sentence_case(head_label or label)[:200], "subtopic", topic,
                                      f"{topic_key} / {label[:120]}")
                n_sub += 1
            for tm in re.finditer(r'<ref\s+target="Nave:([^"]+)"', line):
                see_also.append((topic[0], tm.group(1).strip()))
            refs = extract_refs(line, stats=stats, free_text=False)
            for s, e, method, txt in refs:
                pos += 1
                scripture_rows.append((current[0], s, e, sentence_case(label)[:300] or None, wid, pos))
                entry_refs.append((s, e, "cites", method, txt))
        text = to_text(m.group(1).replace("→", "\n→ "))
        eid = writer.add("topic", topic_key, nice_name(topic_key), text, entry_refs)
        topic_links.append((eid, topic[0], "structural", "nave_topic_entry", 1.0, "Entry is the Nave's topic itself",
                            "accepted", db.now()))
        if len(scripture_rows) > 5000:
            writer.flush()
            con.executemany("INSERT INTO subject_scripture(subject_id, start_verse_id, end_verse_id, note, "
                            "source_work_id, position) VALUES (?,?,?,?,?,?)", scripture_rows)
            scripture_rows = []
    writer.flush()
    con.executemany("INSERT INTO subject_scripture(subject_id, start_verse_id, end_verse_id, note, source_work_id, "
                    "position) VALUES (?,?,?,?,?,?)", scripture_rows)
    con.executemany("INSERT INTO entry_subjects(entry_id, subject_id, method, method_detail, confidence, evidence, "
                    "review_status, created_at) VALUES (?,?,?,?,?,?,?,?)", topic_links)

    # "See ..." cross-references between topics.
    n_see, unresolved_see = 0, []
    def resolve_topic(target):
        t = target.upper().strip()
        for cand in (t, t + "S", t + "ES", t[:-1] if t.endswith("S") else None, t[:-2] if t.endswith("ES") else None):
            if cand and cand in topic_ids:
                return topic_ids[cand]
        stems = {t, t[:-1] if t.endswith("S") else t}
        starts = sorted((k for k in topic_ids for st in stems
                         if k.startswith(st + ",") or k.startswith(st + " (") or k.startswith(st + " AND ")
                         or k.startswith(st + " OF ")), key=len)
        return topic_ids[starts[0]] if starts else None

    for src, target in see_also:
        tgt = resolve_topic(target)
        if not tgt:
            unresolved_see.append(target)
            continue
        if tgt == src:
            continue
        for a, b in ((src, tgt), (tgt, src)):
            cur = con.execute("INSERT OR IGNORE INTO subject_relations(subject_id, related_subject_id, relation, "
                              "score, evidence_count) VALUES (?,?,?,?,?)", (a, b, "see_also", 1.0, 1))
            n_see += cur.rowcount

    out = dict(topics=len(topic_ids), subtopics=n_sub,
               verse_links=con.execute("SELECT COUNT(*) FROM subject_scripture WHERE source_work_id=?", (wid,)).fetchone()[0],
               see_also_links=n_see, see_also_unresolved=len(unresolved_see), **stats.as_dict())
    db.log_ingest(con, "ingest/naves.py", CODE, started, out)
    con.commit()
    print(out)
    return out


if __name__ == "__main__":
    main()
