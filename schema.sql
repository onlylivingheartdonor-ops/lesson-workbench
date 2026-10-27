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
    description TEXT,
    tradition      TEXT,   -- descriptive tag, e.g. 'Methodist (Wesleyan/Arminian)'; NULL for translation committees
    tradition_note TEXT    -- why the tag was assigned
);

-- The small set of traditions used by the tradition filter.  status is
-- 'proposed' until Dave approves the set, then 'approved'.
CREATE TABLE traditions (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'proposed',
    sort_order  INTEGER
);

-- Which filter tradition(s) an author's views count toward.
CREATE TABLE author_traditions (
    author_id    INTEGER NOT NULL REFERENCES authors(id),
    tradition_id INTEGER NOT NULL REFERENCES traditions(id),
    note         TEXT,
    PRIMARY KEY (author_id, tradition_id)
);

-- For multi-author works where different authors wrote different books (JFB):
-- entries about Bible books book_from..book_to belong to this author.
CREATE TABLE section_authors (
    work_id   INTEGER NOT NULL REFERENCES works(id),
    author_id INTEGER NOT NULL REFERENCES authors(id),
    book_from INTEGER NOT NULL,
    book_to   INTEGER NOT NULL,
    source    TEXT,
    PRIMARY KEY (work_id, book_from)
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
    launch_status        TEXT,                      -- e.g. 'replace before launch' (see launch_note)
    launch_note          TEXT,                      -- why, and candidate replacement sources
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
    description    TEXT,
    contested      INTEGER NOT NULL DEFAULT 0  -- 1 = Christian traditions genuinely differ on this subject
);

-- Points where Christian traditions genuinely differ, and the Nave's topics each one
-- touches: scope 'whole' (the topic itself is disputed; subjects.contested = 1) or
-- 'part' (mostly common ground; only the disputed point needs "Where Christians differ").
CREATE TABLE contested_issues (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT
);
CREATE TABLE contested_issue_topics (
    issue_id   INTEGER NOT NULL REFERENCES contested_issues(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    scope      TEXT NOT NULL,
    PRIMARY KEY (issue_id, subject_id)
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
    review_status TEXT NOT NULL DEFAULT 'unreviewed',  -- 'unreviewed', 'needs_review', 'accepted', 'rejected',
                                                       -- 'ai_accepted', 'ai_rejected' (see link_reviews)
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

-- Decisions from reviewing links on the review list (by an AI reviewer or a person).
--   decision 'accept' | 'reject' | 'fix' (link was wrong; new_subject_id is the right subject)
CREATE TABLE link_reviews (
    id               INTEGER PRIMARY KEY,
    entry_subject_id INTEGER NOT NULL REFERENCES entry_subjects(id),
    decision         TEXT NOT NULL,
    new_subject_id   INTEGER REFERENCES subjects(id),
    reviewer         TEXT NOT NULL,
    reviewed_at      TEXT NOT NULL,
    notes            TEXT
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
CREATE INDEX ix_link_reviews_es ON link_reviews(entry_subject_id);
CREATE INDEX ix_provenance_work ON provenance(work_id);
CREATE INDEX ix_bible_text_verse ON bible_text(verse_id);

-- The author actually responsible for each entry: the section author where a work
-- is divided by Bible book (section_authors), otherwise every author of the work.
CREATE VIEW entry_authors AS
    SELECT e.id AS entry_id, sa.author_id
    FROM entries e
    JOIN entry_scripture es ON es.entry_id = e.id AND es.relation = 'about'
    JOIN section_authors sa ON sa.work_id = e.work_id
         AND es.start_verse_id / 1000000 BETWEEN sa.book_from AND sa.book_to
    GROUP BY e.id, sa.author_id
    UNION
    SELECT e.id, wa.author_id
    FROM entries e JOIN work_authors wa ON wa.work_id = e.work_id
    WHERE NOT EXISTS (SELECT 1 FROM section_authors sa WHERE sa.work_id = e.work_id);

-- ---------------------------------------------------------------------------
-- Lessons (Phase 1: data model and the first batch; web features come later)
-- ---------------------------------------------------------------------------

-- Fair, original-words summaries of each approved tradition's view on a contested point.
-- Used by the "Where Christians differ" section and by tradition-specific lesson versions.
CREATE TABLE perspective_summaries (
    id           INTEGER PRIMARY KEY,
    issue_id     INTEGER NOT NULL REFERENCES contested_issues(id),
    tradition_id INTEGER NOT NULL REFERENCES traditions(id),
    summary      TEXT NOT NULL,
    key_texts    TEXT,               -- scripture references the tradition leans on
    status       TEXT NOT NULL DEFAULT 'draft',   -- 'draft', 'reviewed'
    UNIQUE (issue_id, tradition_id)
);

-- One row per lesson version. Versions of one lesson share a family_code: an uncontested
-- lesson has one version ('single'); a contested one has an 'all_views' version and one
-- 'tradition' version per approved tradition.
CREATE TABLE lessons (
    id               INTEGER PRIMARY KEY,
    code             TEXT NOT NULL UNIQUE,     -- e.g. 'forgiveness', 'baptism--lutheran'
    family_code      TEXT NOT NULL,
    version_kind     TEXT NOT NULL,            -- 'single', 'all_views', 'tradition'
    tradition_id     INTEGER REFERENCES traditions(id),     -- set for 'tradition' versions
    contested_issue_id INTEGER REFERENCES contested_issues(id),
    title            TEXT NOT NULL,
    big_idea         TEXT NOT NULL,
    topic_subject_id INTEGER NOT NULL REFERENCES subjects(id),   -- the main Nave's topic
    audience         TEXT NOT NULL,            -- 'adults', 'teens', ...
    length_minutes   INTEGER NOT NULL,
    translation_work_id INTEGER NOT NULL REFERENCES works(id),   -- Bible used for printed scripture
    status           TEXT NOT NULL DEFAULT 'draft',   -- 'draft' (AI, unreviewed), 'reviewed', 'shared'
    visibility       TEXT NOT NULL DEFAULT 'private', -- 'private' until reviewed and promoted
    origin           TEXT NOT NULL,            -- 'batch' (Phase 1), 'live' (generated in the app), 'user_edit'
    owner_user_id    INTEGER,                  -- NULL for library lessons; the user for live and edited ones
    parent_lesson_id INTEGER REFERENCES lessons(id),   -- for a user's private edited copy
    generated_by     TEXT NOT NULL,            -- 'ai' or 'dave' or 'user'
    source_file      TEXT,                     -- lessons/source/<code>.txt for batch lessons
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    reviewed_at      TEXT,
    review_note      TEXT
);
CREATE INDEX ix_lessons_topic ON lessons(topic_subject_id, status);
CREATE INDEX ix_lessons_family ON lessons(family_code);

-- Other topics a lesson covers (so "show existing lessons on this topic" finds it).
CREATE TABLE lesson_topics (
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    PRIMARY KEY (lesson_id, subject_id)
);

-- The template sections, in order. kind is one of: 'opening', 'scripture', 'background',
-- 'teaching_point', 'differ', 'questions', 'application', 'prayer'. (Title and big idea live
-- on the lesson row.) default_hidden marks a "Where Christians differ" section in a tradition
-- version: hidden unless the user turns it on.
CREATE TABLE lesson_sections (
    id             INTEGER PRIMARY KEY,
    lesson_id      INTEGER NOT NULL REFERENCES lessons(id),
    kind           TEXT NOT NULL,
    position       INTEGER NOT NULL,
    heading        TEXT,
    body           TEXT NOT NULL,
    minutes        INTEGER,              -- suggested timing, for the teacher's notes
    teacher_note   TEXT,                 -- extra notes shown only in the teacher's notes
    default_hidden INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_lesson_sections_lesson ON lesson_sections(lesson_id, position);

-- Scripture used by a lesson: the main passage, and the supporting verses of each teaching point.
CREATE TABLE lesson_scripture (
    id             INTEGER PRIMARY KEY,
    lesson_id      INTEGER NOT NULL REFERENCES lessons(id),
    section_id     INTEGER REFERENCES lesson_sections(id),
    role           TEXT NOT NULL,        -- 'main', 'supporting'
    start_verse_id INTEGER NOT NULL,
    end_verse_id   INTEGER NOT NULL,
    ref_text       TEXT NOT NULL
);
CREATE INDEX ix_lesson_scripture_lesson ON lesson_scripture(lesson_id);
CREATE INDEX ix_lesson_scripture_range ON lesson_scripture(start_verse_id, end_verse_id);

-- Commentator quotations. quote_text must appear word for word in the entry's text
-- (the loader refuses a lesson whose quote it cannot find); author_id is the entry's
-- actual author (for Jamieson-Fausset-Brown, the author of that section).
CREATE TABLE lesson_quotes (
    id         INTEGER PRIMARY KEY,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    section_id INTEGER NOT NULL REFERENCES lesson_sections(id),
    entry_id   INTEGER NOT NULL REFERENCES entries(id),
    author_id  INTEGER REFERENCES authors(id),
    quote_text TEXT NOT NULL,
    credit     TEXT NOT NULL             -- e.g. 'Matthew Henry, Commentary on the Whole Bible, on Matthew 18:21-35'
);

-- Fill-in blanks for the student handout outline, with the answers for the teacher.
CREATE TABLE lesson_blanks (
    id         INTEGER PRIMARY KEY,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    section_id INTEGER NOT NULL REFERENCES lesson_sections(id),
    position   INTEGER NOT NULL,
    sentence   TEXT NOT NULL,            -- with ____ where the blank goes
    answer     TEXT NOT NULL
);

-- Discussion questions, with suggested answers for the teacher.
CREATE TABLE lesson_questions (
    id        INTEGER PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    position  INTEGER NOT NULL,
    question  TEXT NOT NULL,
    answer    TEXT
);

-- Users' ratings (empty until the web app). A low rating asks for a one-click reason.
CREATE TABLE lesson_ratings (
    id         INTEGER PRIMARY KEY,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    user_id    INTEGER NOT NULL,
    stars      INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
    reason     TEXT CHECK (reason IN ('doctrinally_off', 'too_shallow', 'wrong_age_group',
                                      'reference_errors', 'other')),
    comment    TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (lesson_id, user_id)
);

-- The monthly fix cycle (empty until the web app): low-rated lessons with their reasons and a
-- drafted fix for Dave; high-rated unreviewed lessons flagged for review and promotion.
CREATE TABLE lesson_fix_cycle (
    id              INTEGER PRIMARY KEY,
    run_month       TEXT NOT NULL,       -- 'YYYY-MM'
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id),
    kind            TEXT NOT NULL,       -- 'low_rated_fix', 'high_rated_review'
    reason_counts   TEXT,                -- JSON: {"too_shallow": 4, ...}
    draft_lesson_id INTEGER REFERENCES lessons(id),
    status          TEXT NOT NULL DEFAULT 'open',   -- 'open', 'approved', 'rejected'
    decided_at      TEXT
);

-- Settings the lesson features read (e.g. the minimum number of ratings before they count).
CREATE TABLE app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    note  TEXT
);
