"""Link entries to subjects and subjects to each other.

Run after all works are ingested:   python3 -m ingest.tagging

Pass 1 - structural (method 'structural'):
  * verse_key overlap: a commentary note filed under a passage is linked to
    the Nave's topics that list verses of that passage.  Confidence rises when
    the passage is mostly covered by the topic, when the topic is specific
    (not a huge topic like "Jesus, the Christ"), and when the note's own text
    uses the topic's key word.
  * headword match: a dictionary/encyclopedia article whose headword is the
    same as a Nave's topic name ("Aaron", "Forgiveness of sin" = Nave's
    "Sin, Forgiveness of").

Pass 2 - machine-assisted (method 'ai'):
  Entries that pass 1 cannot reach (dictionary articles with no matching
  topic, book introductions, sermons) are scored against every topic by
  (a) TF-IDF text similarity to a topic profile built from Nave's own
  wording plus the dictionary articles that match it by headword, and
  (b) overlap between the verses the entry cites and the topic's verses.
  This is a statistical model, not a large language model; see the report.

Pass 3 - related subjects ('shared_verses', 'co_occurrence').

Links below the review threshold are marked 'needs_review' and queued in
review_queue instead of being silently accepted.  Manual links are kept.
"""

import math
import re
from collections import Counter, defaultdict

from library import db
from library.scripture import expand_range
from library.textmodel import TfIdf, build_postings, cosine_top, tokens

VERSE_KEY_DETAIL = "nave_verse_overlap_v2"
HEADWORD_DETAIL = "headword_match_v1"
REVIEWED = db.REVIEWED
AI_DETAIL = "name_density+tfidf_profile+citation_overlap_v3 (statistical; not an LLM)"
STRUCTURAL_REVIEW_BELOW = 0.45
AI_REVIEW_BELOW = 0.55
MAX_VERSE_KEY_LINKS = 10
MAX_AI_LINKS = 5
COMMON_WORD_SHARE = 0.15   # a word in more than 15% of entries counts as an everyday word

NAME_NOISE = {"general", "scriptures", "relating", "unclassified", "instances", "figurative", "the", "of"}
GENERIC = {"general", "scriptures", "relating", "unclassified", "instances", "figurative", "symbolical", "christ",
           "jesu", "people", "the"}


def norm_name(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r",\s*the$", "", s.strip())
    s = re.sub(r"[^a-z0-9, ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip(" ,")


def name_variants(name):
    """'Sin, Forgiveness of' -> {'sin forgiveness of', 'forgiveness of sin'}"""
    n = norm_name(name)
    out = {n.replace(",", "")}
    parts = [p.strip() for p in n.split(",")]
    if len(parts) == 2:
        a, b = parts
        out.add(f"{b} {a}")              # "forgiveness of sin"
        out.add(a)                       # "sin" (weaker; only used for partial matching)
    return {re.sub(r"\s+", " ", o).strip() for o in out if o}


def main():
    started = db.now()
    con = db.connect()
    now = db.now()

    # ------------------------------------------------------------------ reset
    # Reviewed links are permanent (Dave's rule): a re-run never deletes or re-scores a link that a
    # reviewer has accepted, rejected or corrected, and INSERT OR IGNORE below cannot overwrite it.
    # ai_review.apply and spot_checks import re-create any reviewed link a work re-ingest removed.
    keep = ("method='manual' OR method_detail='nave_topic_entry' OR " + REVIEWED)
    con.execute(f"DELETE FROM spot_checks WHERE entry_subject_id IN (SELECT id FROM entry_subjects WHERE NOT ({keep}))")
    con.execute(f"DELETE FROM link_reviews WHERE entry_subject_id IN (SELECT id FROM entry_subjects WHERE NOT ({keep}))")
    con.execute("DELETE FROM review_queue")
    con.execute(f"DELETE FROM entry_subjects WHERE NOT ({keep})")
    con.execute("DELETE FROM subject_relations WHERE relation IN ('shared_verses', 'co_occurrence')")

    # ------------------------------------------------------------- topic data
    topics = {r[0]: r[1] for r in con.execute("SELECT id, name FROM subjects WHERE level='topic'")}
    parent = {r[0]: r[1] for r in con.execute("SELECT id, parent_id FROM subjects WHERE level='subtopic'")}
    topic_verses = defaultdict(set)
    profile_text = defaultdict(list)
    for sid, s, e, note in con.execute("SELECT subject_id, start_verse_id, end_verse_id, note FROM subject_scripture"):
        tid = parent.get(sid, sid)
        topic_verses[tid].update(expand_range(s, e, cap=200))
        if note:
            profile_text[tid].append(note)
    for sid, name in con.execute("SELECT id, name FROM subjects WHERE level='subtopic'"):
        profile_text[parent[sid]].append(name)
    verse_topics = defaultdict(list)
    for tid, vs in topic_verses.items():
        for v in vs:
            verse_topics[v].append(tid)
    topic_stems = {}
    for tid, name in topics.items():
        st = [t for t in tokens(re.sub(r"\(.*?\)", " ", name)) if t not in GENERIC]
        topic_stems[tid] = set(st)

    links = []      # (entry_id, subject_id, method, detail, confidence, evidence)

    # ------------------------------------------------- pass 1a: verse overlap
    q = """SELECT e.id, e.body, es.start_verse_id, es.end_verse_id, e.entry_type
           FROM entries e JOIN works w ON w.id = e.work_id JOIN reference_types rt ON rt.id = w.reference_type_id
           JOIN entry_scripture es ON es.entry_id = e.id AND es.relation = 'about'
           WHERE rt.code = 'commentary' AND e.entry_type IN ('commentary_note', 'chapter_intro')"""
    n_vk_entries = 0
    for eid, body, s, e, etype in con.execute(q):
        passage = expand_range(s, e, cap=200)
        if not passage:
            continue
        overlap = Counter()
        for v in passage:
            for tid in verse_topics.get(v, ()):
                overlap[tid] += 1
        if not overlap:
            continue
        n_vk_entries += 1
        toks = set(tokens(body))
        scored = []
        for tid, ov in overlap.items():
            cov = ov / len(passage)
            size = len(topic_verses[tid])
            spec = 1.0 / (1.0 + math.log10(1 + size / 20.0))
            stems = topic_stems.get(tid) or set()
            mention = (len(stems & toks) / len(stems)) if stems else 0.0
            if etype == "chapter_intro" and mention == 0 and size > 300:
                continue  # a whole chapter touches many broad topics; keep only ones the intro names
            conf = 0.25 + 0.20 * min(1.0, cov * 3) + 0.35 * mention + 0.20 * spec
            scored.append((round(conf, 3), tid, ov, mention))
        scored.sort(reverse=True)
        for conf, tid, ov, mention in scored[:MAX_VERSE_KEY_LINKS]:
            ev = f"{ov} of {len(passage)} verse(s) of this passage are in Nave's '{topics[tid]}'" + \
                 ("; topic word appears in the note" if mention >= 1 else "")
            links.append((eid, tid, "structural", VERSE_KEY_DETAIL, conf, ev))

    # ------------------------------------------------- pass 1b: headword match
    exact, partial = {}, defaultdict(set)
    for tid, name in topics.items():
        for i, var in enumerate(sorted(name_variants(name), key=len, reverse=True)):
            if "," not in norm_name(name) or var != norm_name(name).split(",")[0].strip():
                exact.setdefault(var, tid)
            else:
                partial[var].add(tid)
    q = """SELECT e.id, e.title, e.entry_type, w.code FROM entries e JOIN works w ON w.id = e.work_id
           JOIN reference_types rt ON rt.id = w.reference_type_id
           WHERE rt.code IN ('dictionary', 'encyclopedia') AND e.entry_type IN ('article', 'redirect')"""
    headword_linked = set()
    dict_profile = defaultdict(list)
    articles = list(con.execute(q))
    for eid, title, etype, code in articles:
        variants = name_variants(title)
        hit = next((exact[v] for v in variants if v in exact), None)
        if hit:
            links.append((eid, hit, "structural", HEADWORD_DETAIL, 0.95,
                          f"Headword '{title}' matches Nave's topic '{topics[hit]}'"))
            headword_linked.add(eid)
            if etype == "article":
                dict_profile[hit].append(eid)
            continue
        # "Forgiveness of sin" -> topic "Forgiveness"; "Aaron's rod" -> "Aaron"
        head = norm_name(title).split(",")[0]
        head = re.split(r"\s+(?:of|in|the|and)\s+|'s\s", head)[0].strip()
        hit = exact.get(head)
        if hit:
            links.append((eid, hit, "structural", HEADWORD_DETAIL, 0.70,
                          f"Headword '{title}' begins with Nave's topic '{topics[hit]}'"))
            headword_linked.add(eid)

    # ------------------------------------------------ pass 2: machine-assisted
    profiles = {}
    body_of = {}
    for tid in topics:
        profiles[tid] = [topics[tid]] * 3 + profile_text.get(tid, [])
    want = [eid for tid in dict_profile for eid in dict_profile[tid]]
    for i in range(0, len(want), 900):
        chunk = want[i:i + 900]
        for eid, body in con.execute(f"SELECT id, body FROM entries WHERE id IN ({','.join('?' * len(chunk))})", chunk):
            body_of[eid] = " ".join(body.split()[:400])
    for tid, eids in dict_profile.items():
        profiles[tid] += [body_of[e] for e in eids if e in body_of]
    topic_tokens = {tid: tokens(" ".join(parts)) for tid, parts in profiles.items()}

    q = """SELECT e.id, e.title, e.body FROM entries e JOIN works w ON w.id = e.work_id
           JOIN reference_types rt ON rt.id = w.reference_type_id
           WHERE (rt.code IN ('dictionary', 'encyclopedia') AND e.entry_type = 'article')
              OR (rt.code = 'commentary' AND e.entry_type IN ('book_intro', 'exposition'))
              OR rt.code IN ('sermon', 'devotional', 'doctrinal')"""
    targets = [(eid, title, body) for eid, title, body in con.execute(q) if eid not in headword_linked]
    target_tokens = {eid: tokens(body) for eid, _, body in targets}
    model = TfIdf()
    model.fit(list(topic_tokens.values()) + list(target_tokens.values()))
    topic_vecs = {tid: model.vector(t, top=150) for tid, t in topic_tokens.items()}
    postings = build_postings(topic_vecs)
    # Topic name words, for "does the entry actually talk about this topic?"
    name_stems = {}
    by_stem = defaultdict(set)
    for tid, name in topics.items():
        st = {t for t in tokens(re.sub(r"\(.*?\)", " ", name)) if t not in NAME_NOISE}
        if st:
            name_stems[tid] = st
            for t in st:
                by_stem[t].add(tid)
    # Topics named by an everyday word ("Work", "Way", "World", "Present") are only
    # trusted when the word is in the entry's title: such words occur everywhere.
    target_df = Counter()
    for toks in target_tokens.values():
        target_df.update(set(toks))
    common = {t for t, n in target_df.items() if n > COMMON_WORD_SHARE * max(1, len(target_tokens))}
    cites = defaultdict(set)
    ids = [eid for eid, _, _ in targets]
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        for eid, s, e in con.execute(f"SELECT entry_id, start_verse_id, end_verse_id FROM entry_scripture "
                                     f"WHERE relation='cites' AND entry_id IN ({','.join('?' * len(chunk))})", chunk):
            cites[eid].update(expand_range(s, e, cap=30))
    n_ai_entries = 0
    for eid, title, _ in targets:
        toks = target_tokens[eid]
        if not toks:
            continue
        tf = Counter(toks)
        title_toks = set(tokens(title))
        vec = model.vector(toks, top=60)
        cand = dict(cosine_top(vec, postings, k=40))
        cscore = Counter()
        cv = cites.get(eid, ())
        for v in cv:
            for tid in verse_topics.get(v, ()):
                cscore[tid] += 1.0 / math.log2(2 + len(verse_topics[v]))
        norm = math.sqrt(len(cv)) if cv else 1.0
        named = set()
        for t in tf:
            named |= by_stem.get(t, set())
        scored = []
        per_k = 1000.0 / len(toks)
        for tid in set(cand) | set(t for t, _ in cscore.most_common(40)) | named:
            stems = name_stems.get(tid)
            in_title = bool(stems) and stems <= title_toks
            density = (min(tf.get(t, 0) for t in stems) * per_k) if stems else 0.0
            cos = cand.get(tid, 0.0)
            cit = min(1.0, cscore.get(tid, 0.0) / norm)
            # The entry must show some sign of discussing the topic itself:
            # its name in the title, its name used repeatedly, or clearly similar wording.
            if not (in_title or density >= 2.0 or cos >= 0.25):
                continue
            if not in_title and stems and stems <= common:
                continue
            s = (0.35 * in_title + 0.30 * min(1.0, density / 8.0) + 0.25 * min(1.0, cos / 0.4)
                 + 0.10 * cit)
            if len(topic_verses.get(tid, ())) > 1000 and not in_title:
                s *= 0.6   # very broad topics ("God", "Jesus, the Christ") only when clearly central
            scored.append((s, tid, cos, cit, density, in_title))
        scored.sort(reverse=True)
        kept = 0
        for s, tid, cos, cit, density, in_title in scored[:MAX_AI_LINKS]:
            if kept and s < 0.6 * scored[0][0]:
                break
            conf = round(min(0.95, 0.2 + 0.8 * s), 3)
            if conf < 0.35:
                break
            links.append((eid, tid, "ai", AI_DETAIL, conf,
                          f"name in title: {'yes' if in_title else 'no'}; name used {density:.1f} times per 1,000 "
                          f"words; text similarity {cos:.2f}; citation overlap {cit:.2f}"))
            kept += 1
        if kept:
            n_ai_entries += 1

    # ------------------------------------------------------------ write links
    rows = []
    for eid, tid, method, detail, conf, ev in links:
        threshold = AI_REVIEW_BELOW if method == "ai" else STRUCTURAL_REVIEW_BELOW
        status = "needs_review" if conf < threshold else "unreviewed"
        rows.append((eid, tid, method, detail, conf, ev, status, now))
    con.executemany("INSERT OR IGNORE INTO entry_subjects(entry_id, subject_id, method, method_detail, confidence, "
                    "evidence, review_status, created_at) VALUES (?,?,?,?,?,?,?,?)", rows)
    con.execute("INSERT INTO review_queue(entry_subject_id, reason, created_at) "
                "SELECT id, 'confidence ' || confidence || ' below review threshold (' || method || ')', ? "
                "FROM entry_subjects WHERE review_status='needs_review'", (now,))

    # -------------------------------------------------- pass 3: related topics
    pair = Counter()
    for v, tids in verse_topics.items():
        if len(tids) > 60:
            tids = sorted(tids, key=lambda t: len(topic_verses[t]))[:60]
        tids = sorted(set(tids))
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                pair[(tids[i], tids[j])] += 1
    rel = defaultdict(list)
    for (a, b), n in pair.items():
        if n < 3:
            continue
        score = n / math.sqrt(len(topic_verses[a]) * len(topic_verses[b]))
        rel[a].append((score, b, n))
        rel[b].append((score, a, n))
    rel_rows = []
    for a, lst in rel.items():
        for score, b, n in sorted(lst, reverse=True)[:12]:
            rel_rows.append((a, b, "shared_verses", round(score, 4), n))

    # Co-occurrence: topics tied to the same entries, counted across works.
    by_entry = defaultdict(set)
    entry_work = {}
    for eid, tid, wid in con.execute("SELECT es.entry_id, es.subject_id, e.work_id FROM entry_subjects es "
                                     "JOIN entries e ON e.id = es.entry_id WHERE es.confidence >= 0.6 "
                                     "AND es.method_detail != 'nave_topic_entry'"):
        by_entry[eid].add(tid)
        entry_work[eid] = wid
    co = Counter()
    co_works = defaultdict(set)
    freq = Counter()
    for eid, tids in by_entry.items():
        tids = sorted(tids)
        freq.update(tids)
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                co[(tids[i], tids[j])] += 1
                co_works[(tids[i], tids[j])].add(entry_work[eid])
    rel = defaultdict(list)
    for (a, b), n in co.items():
        if n < 3 or len(co_works[(a, b)]) < 2:
            continue
        score = n / math.sqrt(freq[a] * freq[b])
        rel[a].append((score, b, n))
        rel[b].append((score, a, n))
    for a, lst in rel.items():
        for score, b, n in sorted(lst, reverse=True)[:12]:
            rel_rows.append((a, b, "co_occurrence", round(score, 4), n))
    con.executemany("INSERT OR IGNORE INTO subject_relations(subject_id, related_subject_id, relation, score, "
                    "evidence_count) VALUES (?,?,?,?,?)", rel_rows)

    out = dict(
        verse_key_entries=n_vk_entries, headword_entries=len(headword_linked), ai_entries=n_ai_entries,
        ai_candidates=len(targets),
        links=dict(con.execute("SELECT method || ':' || method_detail, COUNT(*) FROM entry_subjects GROUP BY 1").fetchall()),
        needs_review=con.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0],
        relations=dict(con.execute("SELECT relation, COUNT(*) FROM subject_relations GROUP BY 1").fetchall()))
    db.log_ingest(con, "ingest/tagging.py", None, started, out)
    con.commit()
    print(out)
    return out


if __name__ == "__main__":
    main()
