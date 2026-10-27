# Project Brief: Bible Lesson Workbench (working title)

This file is the standing brief for every build session on this project. Read it in full before doing any work. It was updated after the first Phase 1 report; sections marked (NEW) or (UPDATED) reflect decisions made since.

## Who you're working for

Dave is the product owner and designer. He does not write code and does not want to. Talk to him in plain English, report results in concrete terms (what exists now, what works, what doesn't), and never assume he'll read or edit code.

Working rules:
- Do not make unrequested changes. When Dave makes an observation, that is not a request.
- Deliver complete files, never abbreviated ones.
- Flag any file rename explicitly.
- Prefer fewer, more complete build passes over many small incremental ones.
- When there's a clear best technical answer with no behavior Dave would notice, just do it. When a choice affects what Dave or users see, ask him first, in plain text.
- Document known gaps and accuracy limits openly rather than hiding them.
- You are an AI language model. Where a task calls for reading, judging, or writing text (reviewing tags, writing lessons), do it yourself; you don't need an outside AI service.

## What the product is

An online, subscription-based lesson-building tool for lay Bible teachers (Sunday School teachers, small group leaders), not seminarians.

A teacher searches a large, deeply cross-linked public-domain reference library, finds or generates a lesson, and exports the finished lesson as:
- a PowerPoint deck (.pptx)
- a student handout
- teacher's notes

The library is free elsewhere (Blue Letter Bible, StudyLight, Bible Hub). The product's value is:
- the path from subject to finished lesson, deck, and handouts in one place
- linking good enough that a search on one subject leads naturally to related subjects, verses, and authors
- synthesized, ready-to-teach lessons built from the library
- honest handling of where Christian traditions agree and differ

Pricing intent: inexpensive monthly subscription. Content will be added and refined continually after launch.

## Decisions already made (do not reopen without Dave)

1. This is a new product, forked in concept from Dave's private "Graham Archive" app. It borrows that app's design ideas and tab structure but not its code. The archive itself stays private and untouched.
2. Stack: Python, with a real database. SQLite for the library-building phase; a hosted database (likely PostgreSQL) when the web app is built. Keep the schema portable between the two.
3. Delivery: online web app with accounts and a monthly subscription. No desktop installer.
4. Library: public-domain works only, organized and searchable by subject, scripture, author, reference type, and tradition.
5. Lesson output: .pptx plus student and teacher pages. Python's PowerPoint library (python-pptx) is the expected tool.
6. Dave's own original Sunday School series will be added later as premium or featured content. His late father's personal teaching notes may be added later as a free legacy collection.

## Absolute content rules

- **Public domain or explicitly freely licensed only.** The original texts are public domain, but some digitized editions online carry their own terms. Verify the terms of the specific edition you pull from, and record the source URL, edition, and license status for every work in a provenance table. If an edition's terms are unclear, stop and report it instead of including it.
- **Never include** any purchased or copyrighted curriculum. Specifically excluded: the Coleman curriculum, the 1985 Subject Matter series, the BTN utilization guide, the teacher-training workbook, and Alan Perkins' "The Grace of God." None of these should ever appear in this repository.
- **No share-alike licensed material.** It could impose obligations on the product's data.
- Attribution-licensed material (for example, Creative Commons BY) is acceptable only if the attribution requirement is recorded and can be displayed in the app.
- **Modern denominational statements** (for example, the Catechism of the Catholic Church) are copyrighted. Summarize their positions fairly in original words; do not quote them at length. Older confessions that are public domain (for example, Westminster, the 1689 London Baptist Confession) may be quoted.

## Doctrinal approach (NEW)

The product does not take a denominational side.

- **Where Christians broadly agree** (the core of the historic creeds: God, Christ, the resurrection, salvation by grace), teach it plainly.
- **Where Christians genuinely differ** (for example baptism, predestination, end times, spiritual gifts, the Lord's Supper), do not pick a side. Present the main views fairly, state plainly that Christians differ, and attribute each view to its tradition.
- Every lesson must be grounded in Scripture and the library. Quoted commentators must be quoted accurately and credited.

### Traditions

- Tag every author in the library with their tradition (for example: Matthew Henry, Presbyterian/Puritan; Adam Clarke, Methodist/Arminian; Jamieson-Fausset-Brown, Scottish Presbyterian; Albert Barnes, American Presbyterian; Spurgeon, Reformed Baptist; Moody, nondenominational evangelical). Record these tags in the database and list them in the report so Dave can confirm them.
- Start with a small set of traditions, about five. **Propose the set to Dave and wait for his approval** before generating any tradition-specific content.

### Tradition filter (behavior to support in the data model now; built in the web app later)

- **No tradition selected:** the user sees everything, including where traditions agree and differ.
- **Tradition selected:** on contested points, the user sees only their tradition's view. The "Where Christians differ" section is hidden unless the user explicitly turns it on.
- The filter applies to commentary and to contested points only. Scripture, and commentary on points where traditions agree, is never hidden by the filter.
- Consequence: lessons on contested topics need a version per approved tradition, plus the all-views version. Lessons on uncontested topics need only one version.

## Lesson template (NEW)

Every synthesized lesson has these sections, in this order:

1. **Title and big idea:** one sentence the class should walk out remembering.
2. **Opening:** a question or short story to draw people in.
3. **Scripture:** the main passage, printed out.
4. **Background:** who, when, and why it matters, drawn from the dictionaries and commentaries.
5. **Teaching points:** usually three, each with supporting verses and an accurately quoted, credited commentator.
6. **Where Christians differ:** included only when the topic is contested.
7. **Discussion questions.**
8. **Application:** what to do this week.
9. **Closing prayer.**

How the sections map to the three outputs:
- **Slides:** title, scripture, teaching points, and discussion questions.
- **Student handout:** scripture, an outline with fill-in blanks, discussion questions, and application.
- **Teacher's notes:** everything, including background, commentator quotes, suggested timing, and answers to the blanks and questions.

Each lesson records its topic, audience (for example adults or teens), and approximate length in minutes.

## Lesson lifecycle (NEW; data model now, web features later)

- **Every generated lesson is saved,** including ones generated live in the app later. Before generating something new, the app shows existing lessons on the same topic so a saved one can be reused.
- **Status levels:** draft (AI-generated, unreviewed), reviewed (Dave approved), and shared (available to all users). Live-generated lessons are private to the user who made them until reviewed and promoted.
- **User edits are private.** A user's edited copy of a lesson belongs to that user and is never shared with others.
- **Ratings:** users rate lessons. A low rating asks for a one-click reason (doctrinally off, too shallow, wrong for my age group, errors in references, other). Ratings are shown and acted on only after a minimum number of votes.
- **Monthly fix cycle:** a scheduled pass pulls low-rated lessons, reads the reasons, and drafts fixes for Dave to approve. High-rated unreviewed lessons are flagged for Dave to review and promote first.

## Phase 1 (current): build the library and the first lessons

No website, accounts, or payments yet.

### Phase 1 status after the first report (UPDATED)

Done: the four Bibles; Nave's, Treasury of Scripture Knowledge, and Strong's; Matthew Henry, Adam Clarke, Jamieson-Fausset-Brown, and Barnes (New Testament); Easton's, Smith's, and the ISBE; 15 books by Bounds, Ryle, Moody, and Spurgeon; scripture-quotation detection; the "forgiveness" search test.

Decisions on the open questions:
1. **Top-level categories:** draft a list for Dave to edit. Audience is lay Bible teachers, not seminarians; use plain, everyday category names. Show Dave the draft before placing topics under it.
2. **John Gill:** skip entirely.
3. **Spurgeon's sermons and Barnes' Old Testament notes:** do not contact CCEL. Use public-domain scanned volumes from archive.org and clean up the text. For Spurgeon, start with a selection of his best-known sermons, not the full set.
4. **Share-alike Greek dictionary:** no. Fill the 31 missing Strong's numbers from Thayer's Greek Lexicon (1889, public domain), if available.
5. **CCEL-derived CrossWire editions** (Henry, Nave's, Easton's, JFB): keep for now, but mark each one in the provenance table as "replace before launch," and note candidate independent sources in the report.
6. **Low-confidence subject links:** review them yourself in batches (accept, reject, or fix each) and record them as AI-reviewed. Start with links attached to the most-used topics. Report the new accuracy numbers.

### Remaining library work, in priority order

1. Top-level category draft for Dave.
2. Author tradition tags.
3. AI review of low-confidence links.
4. Thayer's gap fill.
5. Spurgeon selection and Barnes Old Testament from archive.org.

### First lessons (NEW)

After the library work above, and only once Dave has approved the category list and the tradition set:

1. Add the lesson structures above to the database: lessons, lesson sections, status, audience, length, tradition version, and ratings (empty for now).
2. Generate a first batch of a few dozen lessons, not hundreds, on the most-used uncontested topics, following the template exactly and drawing on the library's links. Dave will review each one.
3. Generate a small number of contested-topic lessons (all-views version plus one version per approved tradition) as a test of the tradition approach.
4. Export each lesson to .pptx, a student handout, and teacher's notes, so Dave can review the real output, not just text. Keep slide design plain and clean; Dave will refine the visual design later.

### Data model requirements

At minimum:
- **Works:** title, author, reference type, edition, source URL, license status, date ingested, and a "replace before launch" flag.
- **Authors:** name, dates, short description, tradition.
- **Reference types:** Bible, commentary, dictionary, encyclopedia, topical index, cross-reference, lexicon, sermon, devotional.
- **Entries:** the actual content units (a commentary note, a dictionary article, a sermon section), each belonging to a work.
- **Scripture references:** normalized to a single canonical book/chapter/verse scheme with range support. Every entry that refers to scripture gets linked rows. Leave room for Apocrypha books (later phase).
- **Subjects:** a hierarchy. Nave's subjects as the detailed level; above them, the lay-friendly top-level categories Dave approves. Each subject records whether it is contested among traditions.
- **Entry–subject links:** each link records how it was made (structural, statistical, AI-reviewed, or manual) and a confidence value.
- **Cross-references** (verse to verse) and **Strong's links** (verse to word).
- **Traditions:** the approved set, linked to authors and to tradition-specific lesson versions and perspective summaries.
- **Lessons:** as described under the template and lifecycle sections.
- **Provenance** for everything, as described under content rules.

### Tagging approach ("not blindly")

1. **Structural links first.** Use the existing indexes (verse keys, Nave's, Treasury of Scripture Knowledge, Strong's) to link everything that can be linked without guessing.
2. **Machine-assisted tagging second.** Tag entries that structural linking doesn't reach. Mark every such link with its method and a confidence value.
3. **AI review.** Read and judge low-confidence links directly rather than accepting or discarding them blindly.
4. **Spot checks.** Sample tagged entries per work, check them, and report measured accuracy. Anything still uncertain goes into a review list.
5. **Related-subject links.** Derive subject-to-subject relationships (shared verses, co-occurrence across works) so a search on one subject can surface related ones.

### Phase 1 deliverables

- The database file.
- Ingestion scripts, one per source, rerunnable.
- The first batch of lessons, exported as .pptx, student handouts, and teacher's notes.
- A plain-English report for Dave covering: what was ingested, entry and link counts per work, measured tagging accuracy, author tradition tags, known gaps, sources skipped and why, and the lesson batch with anything he should look at first.
- The command-line search test, kept working.

### Practical notes

- Network access is confirmed (eBible.org, CrossWire, Project Gutenberg, CCEL, archive.org).
- Keep raw downloaded sources out of version control if they are large. Store the processed database and scripts. Note in the report where raw files came from so they can be fetched again.
- Run and test everything before reporting it as done.

## Later phases (not now; for context only)

- **Phase 2:** Web app. Search and browse across the library by subject, scripture, author, reference type, and tradition, with related-subject navigation and the tradition filter.
- **Phase 3:** Lesson builder. Browse saved lessons, generate new ones live (saved automatically), edit privately, and export to .pptx, student handout, and teacher's notes. Ratings and the monthly fix cycle.
- **Phase 4:** Accounts, monthly subscription payments, terms of service (saved generated lessons can be reused across the service; users' personal edits stay private), and hosting.
- **Later additions:** the Apocrypha (public-domain translations such as the 1611 KJV Apocrypha and Brenton's Septuagint, clearly labeled by which traditions include which books); a Perspectives feature showing about five traditions' views on a topic or text, written as fair, original summaries; Dave's original series; his father's legacy collection; continual library expansion. Dave produces any lesson illustrations on his own image-generation setup; the server does not generate images.
