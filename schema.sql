-- Bible Lesson Workbench: reference library schema
--
-- Written in portable SQL (INTEGER / TEXT / REAL, plain foreign keys, no
-- SQLite-only column types) so it can move to PostgreSQL for the web app.
-- The one SQLite-specific piece, the full-text search index, lives in
-- search_index.sql and is rebuilt from these tables; PostgreSQL would use
-- tsvector columns instead.

-- What kind of reference a work is (Bible, commentary, dictionary ...)
CREATE TABLE reference_types (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT
);

CREATE TABLE authors (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    sort_name   TEXT,
    born        TEXT,
    died        TEXT,
    description TEXT
);

-- One row per work (a Bible translation, a commentary, a dictionary ...).
-- License and provenance fields are required by the content rules.
CREATE TABLE works (
    id                   INTEGER PRIMARY KEY,
    code                 TEXT NOT NULL UNIQUE,      -- short id, e.g. 'KJV', 'MHC'
    title                TEXT NOT NULL,
    short_title          TEXT,
    reference_type_id    INTEGER NOT NULL REFERENCES reference_types(id),
    original_date        TEXT,                      -- when the work was first published
    edition              TEXT,                      -- the specific digital edition used
    source_name          TEXT,                      -- e.g. 'eBible.org', 'CrossWire Bible Society'
    source_url           TEXT,
    license_status       TEXT NOT NULL,             -- e.g. 'Public Domain'
    license_evidence     TEXT,                      -- quotation / location of the license statement
    attribution_required INTEGER NOT NULL DEFAULT 0,
    attribution_text     TEXT,                      -- must be displayed if attribution_required = 1
    coverage             TEXT,                      -- e.g. 'Whole Bible', 'New Testament only'
    known_issues         TEXT,
    ingest_script        TEXT,
    date_ingested        TEXT
);

CREATE TABLE work_authors (
    work_id   INTEGER NOT NULL REFERENCES works(id),
    author_id INTEGER NOT NULL REFERENCES authors(id),
    role      TEXT NOT NULL DEFAULT 'author',
    position  INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (work_id, author_id)
);

-- Every raw file a work was built from, with checksum, so the library can
-- be re-fetched and verified.
CREATE TABLE provenance (
    id           INTEGER PRIMARY KEY,
    work_id      INTEGER NOT NULL REFERENCES works(id),
    file_name    TEXT NOT NULL,
    source_url   TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    bytes        INTEGER NOT NULL,
    notes        TEXT
);

-- ---------------------------------------------------------------------------
-- Canonical scripture scheme: 66 books, KJV chapter/verse numbering.
-- verse id = book * 1000000 + chapter * 1000 + verse (see library/scripture.py)
-- ---------------------------------------------------------------------------
CREATE TABLE books (
    id        INTEGER PRIMARY KEY,                  -- 1 = Genesis ... 66 = Revelation
    osis      TEXT NOT NULL UNIQUE,
    usfm      TEXT NOT NULL UNIQUE,
    name      TEXT NOT NULL UNIQUE,
    testament TEXT NOT NULL,                        -- 'OT' or 'NT'
    chapters  INTEGER NOT NULL
);

CREATE TABLE verses (
    id       INTEGER PRIMARY KEY,
    book_id  INTEGER NOT NULL REFERENCES books(id),
    chapter  INTEGER NOT NULL,
    verse    INTEGER NOT NULL
);

CREATE TABLE bible_text (
    work_id  INTEGER NOT NULL REFERENCES works(id),
    verse_id INTEGER NOT NULL REFERENCES verses(id),
    text     TEXT NOT NULL,
    PRIMARY KEY (work_id, verse_id)
);

-- ---------------------------------------------------------------------------
-- Entries: the content units of non-Bible works (a commentary note, a
-- dictionary article, a lexicon entry, a Nave's topic, a sermon section).
-- ---------------------------------------------------------------------------
CREATE TABLE entries (
    id          INTEGER PRIMARY KEY,
    work_id     INTEGER NOT NULL REFERENCES works(id),
    entry_type  TEXT NOT NULL,       -- 'commentary_note', 'chapter_intro', 'book_intro',
                                     -- 'article', 'lexicon', 'topic', 'sermon', 'section'
    entry_key   TEXT NOT NULL,       -- stable key within the work (verse range, headword ...)
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,       -- plain text, paragraphs separated by blank lines
    word_count  INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL,
    parent_id   INTEGER REFERENCES entries(id)
);

-- Scripture linked to an entry.
--   relation 'about' = the entry is a note on / article about this passage
--   relation 'cites' = the passage is cited inside the entry
--   method   'verse_key'     = from the work's own verse indexing
--            'source_markup' = from reference markup in the source edition
--            'text_parse'    = recognized in plain text by library/scripture.py
--            'quotation_match' = the entry quotes 8+ consecutive words of this KJV verse
CREATE TABLE entry_scripture (
    id             INTEGER PRIMARY KEY,
    entry_id       INTEGER NOT NULL REFERENCES entries(id),
    start_verse_id INTEGER NOT NULL,
    end_verse_id   INTEGER NOT NULL,
    relation       TEXT NOT NULL,
    method         TEXT NOT NULL,
    ref_text       TEXT
);

-- ---------------------------------------------------------------------------
-- Subjects: level 'category' (lay-friendly top layer, defined by Dave),
-- 'topic' (Nave's topics) and 'subtopic' (Nave's sub-headings).
-- ---------------------------------------------------------------------------
CREATE TABLE subjects (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    slug           TEXT NOT NULL UNIQUE,
    level          TEXT NOT NULL,
    parent_id      INTEGER REFERENCES subjects(id),
    source_work_id INTEGER REFERENCES works(id),
    source_key     TEXT,
    description    TEXT
);

-- Which top-level categories a Nave's topic sits under (many-to-many).
CREATE TABLE category_topics (
    category_id INTEGER NOT NULL REFERENCES subjects(id),
    topic_id    INTEGER NOT NULL REFERENCES subjects(id),
    method      TEXT NOT NULL,       -- 'manual', 'ai', 'structural'
    confidence  REAL NOT NULL,
    PRIMARY KEY (category_id, topic_id)
);

-- Subject -> verses (from Nave's).
CREATE TABLE subject_scripture (
    id             INTEGER PRIMARY KEY,
    subject_id     INTEGER NOT NULL REFERENCES subjects(id),
    start_verse_id INTEGER NOT NULL,
    end_verse_id   INTEGER NOT NULL,
    note           TEXT,             -- Nave's line text, e.g. 'Joseph forgives his brothers'
    source_work_id INTEGER NOT NULL REFERENCES works(id),
    position       INTEGER NOT NULL
);

-- Entry -> subject links, each recording how it was made and how sure it is.
--   method 'structural' = derived from an index (Nave's verse lists, headword match)
--          'ai'         = machine-assisted guess (see method_detail)
--          'manual'     = a person made or confirmed it
CREATE TABLE entry_subjects (
    id            INTEGER PRIMARY KEY,
    entry_id      INTEGER NOT NULL REFERENCES entries(id),
    subject_id    INTEGER NOT NULL REFERENCES subjects(id),
    method        TEXT NOT NULL,
    method_detail TEXT NOT NULL,
    confidence    REAL NOT NULL,
    evidence      TEXT,
    review_status TEXT NOT NULL DEFAULT 'unreviewed',  -- 'unreviewed', 'needs_review', 'accepted', 'rejected'
    created_at    TEXT NOT NULL,
    UNIQUE (entry_id, subject_id)
);

-- Subject -> subject relationships for "related subjects" navigation.
--   'see_also'     = Nave's own "See ..." cross-reference (structural)
--   'shared_verses'= topics whose verse lists overlap
--   'co_occurrence'= topics linked to the same entries across works
CREATE TABLE subject_relations (
    subject_id         INTEGER NOT NULL REFERENCES subjects(id),
    related_subject_id INTEGER NOT NULL REFERENCES subjects(id),
    relation           TEXT NOT NULL,
    score              REAL NOT NULL,
    evidence_count     INTEGER NOT NULL,
    PRIMARY KEY (subject_id, related_subject_id, relation)
);

-- Verse -> verse cross-references (Treasury of Scripture Knowledge).
CREATE TABLE cross_references (
    id                INTEGER PRIMARY KEY,
    from_verse_id     INTEGER NOT NULL,
    to_start_verse_id INTEGER NOT NULL,
    to_end_verse_id   INTEGER NOT NULL,
    keyword           TEXT,          -- the word/phrase of the verse the reference hangs on
    source_work_id    INTEGER NOT NULL REFERENCES works(id),
    position          INTEGER NOT NULL
);

-- Strong's lexicon (one row per Strong's number, e.g. 'H430', 'G863').
CREATE TABLE strongs (
    number          TEXT PRIMARY KEY,
    language        TEXT NOT NULL,   -- 'Hebrew' or 'Greek'
    lemma           TEXT,
    transliteration TEXT,
    pronunciation   TEXT,
    definition      TEXT,
    kjv_usage       TEXT,
    entry_id        INTEGER REFERENCES entries(id)
);

-- Verse -> original word (Strong's-tagged words of the KJV).
CREATE TABLE verse_words (
    work_id  INTEGER NOT NULL REFERENCES works(id),
    verse_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    word     TEXT NOT NULL,
    strongs  TEXT NOT NULL,
    PRIMARY KEY (work_id, verse_id, position, strongs)
);

-- Low-confidence or disputed links waiting for a person to look at them.
CREATE TABLE review_queue (
    id               INTEGER PRIMARY KEY,
    entry_subject_id INTEGER NOT NULL REFERENCES entry_subjects(id),
    reason           TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

-- Results of tagging spot checks.
CREATE TABLE spot_checks (
    id               INTEGER PRIMARY KEY,
    entry_subject_id INTEGER NOT NULL REFERENCES entry_subjects(id),
    verdict          TEXT NOT NULL,  -- 'correct', 'partly', 'wrong'
    checker          TEXT NOT NULL,
    checked_at       TEXT NOT NULL,
    notes            TEXT
);

CREATE TABLE ingest_log (
    id          INTEGER PRIMARY KEY,
    script      TEXT NOT NULL,
    work_code   TEXT,
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    stats       TEXT
);

CREATE INDEX ix_verses_book ON verses(book_id, chapter, verse);
CREATE INDEX ix_entries_work ON entries(work_id, sort_order);
CREATE INDEX ix_entries_key ON entries(work_id, entry_key);
CREATE INDEX ix_entry_scripture_range ON entry_scripture(start_verse_id, end_verse_id);
CREATE INDEX ix_entry_scripture_entry ON entry_scripture(entry_id);
CREATE INDEX ix_subjects_name ON subjects(name);
CREATE INDEX ix_subjects_parent ON subjects(parent_id);
CREATE INDEX ix_subject_scripture_range ON subject_scripture(start_verse_id, end_verse_id);
CREATE INDEX ix_subject_scripture_subject ON subject_scripture(subject_id);
CREATE INDEX ix_entry_subjects_subject ON entry_subjects(subject_id, confidence);
CREATE INDEX ix_entry_subjects_entry ON entry_subjects(entry_id);
CREATE INDEX ix_cross_from ON cross_references(from_verse_id);
CREATE INDEX ix_cross_to ON cross_references(to_start_verse_id);
CREATE INDEX ix_verse_words_strongs ON verse_words(strongs);
CREATE INDEX ix_subject_relations_rel ON subject_relations(related_subject_id);
-- Indexes on foreign keys so reruns (which delete a work's old rows) stay fast.
CREATE INDEX ix_entries_parent ON entries(parent_id);
CREATE INDEX ix_strongs_entry ON strongs(entry_id);
CREATE INDEX ix_review_queue_es ON review_queue(entry_subject_id);
CREATE INDEX ix_spot_checks_es ON spot_checks(entry_subject_id);
CREATE INDEX ix_provenance_work ON provenance(work_id);
CREATE INDEX ix_bible_text_verse ON bible_text(verse_id);
