# Project Brief: Bible Lesson Workbench (working title)

This file is the standing brief for every build session on this project. Read it in full before doing any work.

## Who you're working for

Dave is the product owner and designer. He does not write code and does not want to. Talk to him in plain English, report results in concrete terms (what exists now, what works, what doesn't), and never assume he'll read or edit code.

Working rules:
- Do not make unrequested changes. When Dave makes an observation, that is not a request.
- Deliver complete files, never abbreviated ones.
- Flag any file rename explicitly.
- Prefer fewer, more complete build passes over many small incremental ones.
- When there's a clear best technical answer with no behavior Dave would notice, just do it. When a choice affects what Dave or users see, ask him first, in plain text.
- Document known gaps and accuracy limits openly rather than hiding them.

## What the product is

An online, subscription-based lesson-building tool for lay Bible teachers (Sunday School teachers, small group leaders), not seminarians.

A teacher searches a large, deeply cross-linked public-domain reference library, collects pieces into a lesson, and exports the finished lesson as:
- a PowerPoint deck (.pptx)
- a student handout
- teacher's notes

The library is free elsewhere (Blue Letter Bible, StudyLight, Bible Hub). The product's value is the path from subject to assembled lesson to finished deck and handouts in one place, plus linking good enough that a search on one subject leads naturally to related subjects, verses, and authors.

Pricing intent: inexpensive monthly subscription. Content will be added and refined continually after launch.

## Decisions already made (do not reopen without Dave)

1. This is a new product, forked in concept from Dave's private "Graham Archive" app. It borrows that app's design ideas and tab structure but not its code. The archive itself stays private and untouched.
2. Stack: Python, with a real database. SQLite for the library-building phase; a hosted database (likely PostgreSQL) when the web app is built. Keep the schema portable between the two.
3. Delivery: online web app with accounts and a monthly subscription. No desktop installer.
4. Library: public-domain works only, organized and searchable by subject, scripture, author, and type of reference.
5. Lesson output: .pptx plus student and teacher pages. Python's PowerPoint library (python-pptx) is the expected tool.
6. Dave's own original Sunday School series will be added later as premium or featured content. His late father's personal teaching notes may be added later as a free legacy collection.

## Absolute content rules

- **Public domain or explicitly freely licensed only.** The original texts below are public domain, but some digitized editions online carry their own terms. Verify the terms of the specific edition you pull from, and record the source URL, edition, and license status for every work in a provenance table. If an edition's terms are unclear, stop and report it instead of including it.
- **Never include** any purchased or copyrighted curriculum. Specifically excluded: the Coleman curriculum, the 1985 Subject Matter series, the BTN utilization guide, the teacher-training workbook, and Alan Perkins' "The Grace of God." None of these should ever appear in this repository.
- Attribution-licensed material (for example, Creative Commons BY) is acceptable only if the attribution requirement is recorded and can be displayed in the app.

## Phase 1 (current): build the library

This is the work for the current build session(s). No website, accounts, or payments yet.

### Goal

One database containing the reference library, fully normalized and cross-linked, plus the scripts that built it, so it can be rebuilt or extended at any time.

### Sources, in priority order

Bibles (Dave already has clean files for these; ask him for them before re-downloading):
- KJV, ASV, BBE, WEB

Linking backbone (ingest these first, since everything else hangs on them):
- Nave's Topical Bible (subjects → verses)
- Treasury of Scripture Knowledge (verse → related verses)
- Strong's Concordance, Hebrew and Greek lexicons (verses → original words)

Commentaries (keyed to verses):
- Matthew Henry (complete)
- Adam Clarke
- John Gill
- Albert Barnes
- Jamieson-Fausset-Brown

Dictionaries and encyclopedias:
- Easton's Bible Dictionary
- Smith's Bible Dictionary
- International Standard Bible Encyclopedia (1915)

Sermons and devotional works (later in Phase 1 if time allows):
- Spurgeon's sermons
- E.M. Bounds on prayer
- J.C. Ryle, D.L. Moody (selected works)

If time runs short, finish fewer works completely rather than many partially.

### Data model requirements

At minimum:
- **Works:** title, author, reference type, edition, source URL, license status, date ingested.
- **Authors:** name, dates, short description.
- **Reference types:** Bible, commentary, dictionary, encyclopedia, topical index, cross-reference, lexicon, sermon, devotional.
- **Entries:** the actual content units (a commentary note, a dictionary article, a sermon section), each belonging to a work.
- **Scripture references:** normalized to a single canonical book/chapter/verse scheme with range support. Every entry that refers to scripture gets linked rows.
- **Subjects:** a hierarchy. Use Nave's subjects as the detailed level. Above them, a lay-friendly top-level category layer that Dave will define. Ask him before inventing top-level categories.
- **Entry–subject links:** each link records how it was made (structural from Nave's or another index, AI-assisted, or manual) and a confidence value.
- **Cross-references** (verse to verse) and **Strong's links** (verse to word).
- **Provenance** for everything, as described under content rules.

### Tagging approach ("not blindly")

1. **Structural links first.** Use the existing indexes (verse keys, Nave's, Treasury of Scripture Knowledge, Strong's) to link everything that can be linked without guessing.
2. **AI-assisted subject tagging second.** Tag entries that structural linking doesn't reach. Mark every AI-made link as such, with a confidence value.
3. **Spot checks.** Sample AI-tagged entries per work, check them, and report the measured accuracy. Low-confidence links go into a review list rather than being silently accepted.
4. **Related-subject links.** Derive subject-to-subject relationships (shared verses, co-occurrence across works) so a search on one subject can surface related ones.

### Phase 1 deliverables

- The database file.
- Ingestion scripts, one per source, rerunnable.
- A plain-English report for Dave covering: what was ingested, entry and link counts per work, measured tagging accuracy, known gaps, and any sources skipped and why.
- A simple command-line search test showing that a subject search (for example, "forgiveness") returns linked verses, commentary from several authors, dictionary articles, and related subjects.

### Practical notes

- Check network access first. If the session can't download source texts, report that immediately in plain English so Dave can change the session's network setting or supply the files.
- Keep raw downloaded sources out of version control if they are large. Store the processed database and scripts. Note in the report where raw files came from so they can be fetched again.
- Run and test everything before reporting it as done.

## Later phases (not now; for context only)

- **Phase 2:** Web app. Search and browse across the library by subject, scripture, author, and reference type, with related-subject navigation.
- **Phase 3:** Lesson builder. Collect items, arrange them, and edit into a lesson; export to .pptx, student handout, and teacher's notes.
- **Phase 4:** Accounts, monthly subscription payments, and hosting.
- **Ongoing:** Add Dave's original series and his father's legacy collection. Expand the library. Dave produces any lesson illustrations on his own image-generation setup; the server does not generate images.
