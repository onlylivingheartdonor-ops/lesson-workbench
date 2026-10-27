# Phase 1 Report: Library, Categories, Traditions and the First Lessons

Prepared for Dave, 27 October 2026. This replaces the earlier reports. The newest work, done on your last set of decisions, is marked **(new)**.

## The short version

- **Review decisions are now permanent (new).** The roughly 180 accepted links that dropped out are back. No future re-run of the tagger can overwrite or remove a reviewed decision, and a test proves it. Details are under "Link review".
- **Second review pass done (new):**
  - All 2,366 newly hidden links on the 300 most-used topics were read.
  - All of Maclaren's visible machine-made links were read: 3,955 of them, every one but a single duplicate.
  - The new accuracy numbers are under "Link review".
- **Your export decisions are in (new):**
  - **Translation:** the Bible is chosen at export from the four we have, and KJV is the default.
  - **File formats:** handouts and teacher's notes come as both Word and PDF.
  - **All-views lessons:** "Where Christians differ" is now in the teacher's notes, the student handout and on one slide.
  - **Ratings:** count after 5 votes.
  - **Category order:** left as it is.
  - **Lessons regenerated:** all 44 lessons have been re-exported in KJV.
- **Categories:** your 24 categories are in, and every one of Nave's 5,322 topics is placed under at least one of them. Details are in `docs/CATEGORIES_DRAFT.md`.
- **Traditions:** your five traditions are approved in the database. Strong's and Nave's no longer count toward Methodist, and Jamieson-Fausset-Brown is credited section by section to its actual author.
- **New sources:**
  - Baptist: Maclaren's *Expositions of Holy Scripture* and Broadus on Matthew
  - Lutheran: Luther's Large Catechism, Luther on Galatians and on Genesis 1-3, the Augsburg Confession, Stump's explanation of the Small Catechism, and Gerberding
  - Pentecostal, all published before 1931: Woodworth-Etter, McPherson and Montgomery
- **Your four added contested points** are in, for 11 in all.
- **First batch: 44 lessons**, each exported as slides, a student handout and teacher's notes:
  - 32 on uncontested topics;
  - 12 testing the tradition approach: Baptism and Spiritual Gifts Today, each with an all-views version and one version for each of the five traditions.

  The list and where to start are in `docs/LESSONS.md`.

**Please look at first:**

1. The 12 contested-topic lessons, to judge whether each tradition's view reads fairly. The all-views versions now show the five views on a slide and in the handout.
2. One complete uncontested lesson, such as `lessons/output/forgiveness/`, to judge the format.

## Link review

### Reviewed decisions are permanent (new)

**What went wrong before.** Re-running the tagger rebuilt its links from scratch. Any review decision on a link the tagger no longer made was left pointing at nothing.

**What changed.** A reviewed decision is now permanent:

- **A re-run cannot touch a reviewed link.** This covers accepted, rejected and corrected links, whether they were reviewed in the review list or a spot check. The tagger keeps them exactly as they are and never makes a new link on top of them.
- **If a reviewed link disappears anyway, it comes back.** This can happen when a book is re-imported and its entries are rebuilt. Every decision is stored in `review/ai_reviews.csv` together with the opening words of the entry it was about, and re-applying the decisions re-creates any missing link with its reviewed status. A rejected link is re-created as rejected, so the tagger can never bring it back as unreviewed.
- **The full rebuild checks every decision.** `build.py` now ends by confirming that every recorded decision is in effect, and it stops with an error if one is not.

**The test.** `python3 -m unittest tests.test_review_permanence -v` (about 90 seconds) runs on a copy of the database, so the real one is never touched.

1. It deletes 300 reviewed links of every kind: accepted, rejected and spot-checked.
2. It re-runs the whole tagger and confirms that every other reviewed link is unchanged.
3. It re-applies the decisions and confirms that all 300 come back with the same status, and that every recorded decision is in effect.

The test passes.

**What was restored:**

| Restored | Count |
|---|---|
| Accepted links that had dropped out | 171 |
| Rejected links, re-created as rejected so they stay out | 895 |
| Spot-checked links | 14 |
| Decisions whose entry no longer exists | 120 |

The 120 decisions in the last row (11 accepts, 109 rejects) were about Pentecostal entries that were renamed or split when those books were re-imported. They were made before decisions carried the entry's opening words, so they cannot be matched up again. Their entries are now covered by the second review pass below.

**A bug I found and fixed during the second pass.** A few works have two different entries under the same key, for example the four parts of one Maclaren sermon. When I decided on the second of such a pair, the decision was wrongly skipped as already made. Decisions now also check the entry's opening words. This affected two links; both are now recorded.

### Second review pass (new)

**Hidden links on the 300 most-used topics:** all 2,366 were read and judged.

- **680 accepted (29%)** and made visible.
- **1,686 rejected.**

These links were rightly hidden: fewer than a third were right, much like the 26% on the first pass. The most common miss was a dictionary article that just uses the topic's word. For example, 162 ISBE word articles were tied to the topic "Translation" (Enoch and Elijah being taken up) only because they contain the phrase "the translation of".

**Maclaren's visible links:** all 3,955 were read and judged.

- **3,109 were right (79%)** and are kept.
- **846 were wrong** and are now rejected, so they no longer show.

The earlier sample of 25 had suggested 66%; the full count is better. The misses are title puns:

- "Luke" or "Mark" (the people) on expositions of their Gospels;
- "Day" on sermons about "that day";
- "Man" on "the Son of Man";
- "Measure" on "the measure of grace";
- "Graces" on sermons about the grace of God.

Every Maclaren machine link is now reviewed except one: a sermon stored twice with identical text. That duplicate should be removed in the clean-up.

### Overall numbers

| | Count |
|---|---|
| Review decisions recorded, all passes | 11,647 (5,195 accepted, 6,451 rejected, 1 corrected) |
| Low-confidence links on the 300 most-used topics still unreviewed | 0 |
| Low-confidence links on other topics, hidden and waiting for a later pass | 14,842 |
| Visible links that have not been reviewed one by one | 365,614 |

Those visible links come from the structural indexes and from high-confidence matching. Earlier spot checks put them at about 82% right, except Maclaren's, which are now all reviewed.

## Categories

All 24 are created, and all 5,322 topics are placed, 410 of them under more than one category. As you decided, the order of the categories stays as it is for now.

| How topics were placed | Placements | Measured accuracy |
|---|---|---|
| Structural rules (people and places, from Nave's own descriptions) | 2,256 | 95 of 100 right on a fresh sample. The 5 wrong ones, plus 10 more found by a further check, were corrected. |
| Placed by me, reading each topic | 3,491 | 58 of 60 clearly right on a sample (2 debatable). These are my own placements, so this check is not independent. |
| Marked uncertain, for you to check | 198 | listed in `review/category_review.csv` |

You can change any placement in `ingest/data/category_placements.tsv`. Your changes always win over the automatic ones.

Gaps:

- **Books of the Bible:** Nave's has topics for only some books.
- **Holidays and Seasons:** Nave's has no "Christmas" or "Easter" topics, so I used the nearest ones (Incarnation, Resurrection and so on).

## Traditions and author tags

The approved set: Baptist, Methodist/Wesleyan, Presbyterian/Reformed, Lutheran, Pentecostal/Charismatic. Every author's tag is listed in `docs/TRADITIONS_PROPOSAL.md`, now marked approved.

- **Strong's and Nave's** are outside the filter.
- **Jamieson-Fausset-Brown** is credited by section, from the title pages of the 1866 edition:
  - Genesis to Esther: Robert Jamieson
  - Job to Malachi: A. R. Fausset
  - Matthew to Romans: David Brown
  - 1 Corinthians to Revelation: A. R. Fausset

  Fausset was an Anglican, so his sections (about 10,500 notes) sit outside the filter, like Ryle's.
- **New authors are tagged:** Maclaren and Broadus (Baptist); Luther, Melanchthon, Gerberding and Stump (Lutheran); Woodworth-Etter, McPherson and Montgomery (Pentecostal). Translators and editors are left untagged.

## New sources added

| Work | Source | What's in | Limits |
|---|---|---|---|
| Maclaren, *Expositions of Holy Scripture* | Project Gutenberg, 15 volumes | 1,378 expositions (2,497 entries) on 57 books | The Gutenberg set has no volumes for Song of Solomon, Lamentations, Joel, Obadiah, Nahum, Philemon, 2 and 3 John, or Jude. 9 expositions could not be tied to a passage and are findable by subject only. |
| Broadus, *Commentary on Matthew* (1886) | archive.org scan | 571 entries; 71% of Matthew's verses fall inside a note | It is a scanned book: the text has OCR errors (split words, stray marks), so I quote it only where the text is clean. One spot-checked note was filed under the wrong verse. |
| Luther, *Large Catechism* (Bente and Dau, 1921) | Project Gutenberg | 39 sections | |
| Stump, *Explanation of Luther's Small Catechism* | Project Gutenberg | 147 sections | |
| *Augsburg Confession* | Project Gutenberg | 30 articles | |
| Gerberding, *The Way of Salvation in the Lutheran Church* | Project Gutenberg | 35 chapters | |
| Luther on Genesis 1-3 (Lenker, 1904) | Project Gutenberg | 100 sections | |
| Luther on Galatians (Philadelphia, 1891) | archive.org scan | 267 entries, 133 of 149 verses | OCR text, cleaned automatically |
| Woodworth-Etter, *Signs and Wonders* (1916) | archive.org scan | 153 entries | OCR; mostly testimonies and meeting reports |
| McPherson, *This Is That* (c1921) | archive.org scan | 128 entries | OCR. The later part of the book is a collection, partly of other people's testimonies, whose chapter titles could not all be matched; it is filed as "Later chapters". I avoided quoting from it unless the words were clearly hers. |
| Montgomery, *Secrets of Victory* (1921) | archive.org scan | 44 entries in 26 chapters | OCR |

**Lutheran sources excluded as unclear:**

- Graebner's 1939 Galatians translation (Gutenberg #1549), because a 1939 American book may still be in copyright.
- The modern Small Catechism text (#1670), whose translation date and terms were unclear.

Everything is recorded in `docs/PROVENANCE.md`. Per-work counts are in `docs/COUNTS.md`.

**Library totals:**

- 44 works
- 97,862 entries (about 28.7 million words)
- 479,415 scripture links
- 397,444 subject links (376,235 of them shown in search)
- 47,796 related-subject links

## Contested points

There are now 11 contested points. Your four additions are:

- women in church leadership
- spiritual gifts today ("Tongues" merged into it)
- creation and the age of the earth
- divorce and remarriage

Each is linked to the Nave's topics it touches, either the whole topic or part of one (for example, "Marriage" is partly contested because of divorce).

## The lessons

**Lesson records.** Every lesson is saved with the following:

- **Basic details:** topic, audience, length in minutes and the Bible translation it was written against.
- **Version:** single, all-views, or one tradition's version.
- **Status and visibility:** draft, reviewed or shared; private until promoted.
- **Owner and origin:** who made it, and whether it was batch-made, generated live, or a user's private edited copy.
- **Sections:** in the template's order, with scripture, quotes, blanks, discussion questions and suggested answers.
- **Ratings:** a one-click reason for low ratings (empty for now). Ratings count once a lesson has **5 votes**, as you decided; this is stored as a setting.
- **The monthly fix-cycle queue** (empty for now).

### Your export decisions (new)

**Translation.** The Bible is chosen when a lesson is exported, from the four in the library. KJV is the default.

| Bible | How to export |
|---|---|
| King James Version | `python3 tools/export_lessons.py` |
| American Standard Version | `python3 tools/export_lessons.py --translation ASV` |
| Bible in Basic English | `python3 tools/export_lessons.py --translation BBE` |
| World English Bible | `python3 tools/export_lessons.py --translation WEB` |

KJV files have plain names. Other translations add the translation to the file name, for example `prayer-handout-WEB.docx`, so they never overwrite the KJV files. All 44 lessons have been regenerated in KJV.

One limit to know: the lessons were written against the KJV wording. A fill-in blank or a teacher's note that echoes a KJV phrase ("forgive us our debts") may not match another translation word for word. The web app's live generator will need to write against the chosen translation.

**File formats.** Each lesson folder now has:

| File | Format |
|---|---|
| Slides | .pptx |
| Student handout | .docx and .pdf |
| Teacher's notes | .docx and .pdf |

The PDFs are made from the Word files by LibreOffice, so they look the same.

**"Where Christians differ" in the all-views lessons.** It now appears in three places:

- **Teacher's notes:** the full section, as before.
- **Student handout:** the agreed ground, then each tradition's view in full.
- **One slide:** each tradition's view in a single line.

I wrote the one-line summaries myself, from each view's longer summary; they are in the new last column of `ingest/data/perspectives.tsv`.

In each tradition's own version, the section stays out of the handout and slides, because it is hidden there unless the user turns it on. It remains in the teacher's notes, marked as hidden by default.

### How the first batch was made

I wrote each lesson myself, following the template exactly, after reading the library's commentary on its passage.

- **Every commentator quote is copied from a library entry.** The loader checks it word for word against that entry and refuses the lesson if it doesn't match. I tested this by changing a single word; the lesson was refused.
- **Credits name the entry's actual author.** For JFB that is the author of that section.
- **Scripture is printed from the chosen Bible** (KJV by default), with paragraph breaks.

### Checks done

- All 44 lessons load with every quote verified and every scripture reference resolved.
- Each lesson's section timings add up to its stated length.
- I rendered sample slides, handouts and teacher's notes to images to check the layout, including the new "Where Christians differ" slide and handout page.
- I exported a sample lesson in each of the other three translations to check the scripture prints correctly.
- I also checked the short catechism phrases quoted inside two teacher's notes against the library, and corrected them to the library's exact wording.

### Things to know about the batch

- **Whose voices are quoted.** The uncontested lessons quote mostly Adam Clarke (78 quotes), Albert Barnes (47) and Matthew Henry (43), because they comment on every verse. Baptist voices (Spurgeon, Maclaren, Broadus) appear mainly in the contested lessons. Later batches can draw more on Maclaren and Spurgeon.
- **Hard passages get a teacher's note.** Where a passage brushes against a contested point, the lesson teaches the agreed ground and adds a note saying that Christians differ. Examples: 1 Corinthians 13:8 (tongues ceasing), Ephesians 2:8 (grace and faith), Psalm 103:3 (healing), John 14:3 (end times) and Acts 2:42 (breaking of bread).
- **The perspective summaries are my own wording, not quotations.** Each tradition's view is summarised fairly, with the texts it leans on (`ingest/data/perspectives.tsv`). The only quotation is a few words of the public-domain Westminster Confession. No modern denominational statement is quoted.
- **The tradition lessons quote each tradition's own writers.** For example, Luther and the Augsburg Confession for Lutherans, Broadus and Maclaren for Baptists, Clarke for Methodists, Henry and Barnes for Reformed, and Woodworth-Etter and Montgomery for Pentecostals. Where a tradition's own writer disagrees with its usual view, the teacher's note says so. For example, Barnes (Presbyterian) reads "tongues shall cease" as referring to heaven, and Maclaren (Baptist) says the same.

## Known gaps and accuracy limits

- **Links on less-used topics:** 14,842 low-confidence links outside the 300 most-used topics are hidden and unreviewed. They can be reviewed in later passes, most-used topics first.
- **Visible links on works other than Maclaren** are measured by samples only, at about 82% right.
- **120 old review decisions** no longer match an entry (see "What was restored").
- **One Maclaren sermon is stored twice** with identical text; one copy's link to "Christ" is unreviewed.
- **Other translations:** lesson wording follows the KJV (see "Translation" above).
- **Spurgeon's scanned sermon volumes** include publishers' advertisements at the end of some entries. They should be trimmed in a later clean-up.
- **Barnes' New Testament notes** contain some placeholder entries that say "No entries in BARNES for this verse".
- **Text quality:** the OCR books read less cleanly than the Gutenberg books. They are fine for finding and reading, but need care before quoting. These are Broadus, Luther on Galatians, the three Pentecostal books and Barnes' Old Testament.
- **Category accuracy** is measured on samples only; see the table above.

## What I need from you

1. **Review the 12 contested-topic lessons and `ingest/data/perspectives.tsv`.** Is each tradition's view fair, including the new one-line versions on the slide?
2. **The 198 uncertain category placements** in `review/category_review.csv`, when you have time.
3. **Optional:** a review pass on the hidden links of the next most-used topics, beyond the top 300.

## Where things are

- **The database:** `library.db`, stored compressed in `data/` (`python3 tools/restore_db.py` unpacks it). `python3 build.py --fresh` rebuilds everything, including categories and lessons, and ends by checking that every review decision is in effect.
- **Review decisions:** `review/ai_reviews.csv` (review list) and `review/spot_checks.csv` (spot checks). `python3 -m ingest.ai_review verify` checks they are all in effect.
- **Lessons:** source files are in `lessons/source/`; output files are in `lessons/output/<code>/`. `python3 -m ingest.lessons` reloads the lessons and `python3 tools/export_lessons.py` re-exports them (add `--translation ASV`, `BBE` or `WEB` for another Bible, or `--no-pdf` to skip the PDFs).
- **Research helper:** `python3 tools/lesson_sources.py "Matthew 18:21-35" --topic Forgiveness` shows the library material behind a passage. I used it to write every lesson.
- **Search test:** `python3 search.py forgiveness` (outputs saved in `docs/search_test_*.txt`).
