# Phase 1 Report: Library, Categories, Traditions and the First Lessons

Prepared for Dave, 27 October 2026. This replaces the earlier reports and covers everything since your last decisions.

## The short version

- **Link review:** done as you asked. All links on the 300 most-used topics were reviewed, and all other low-confidence links are now hidden from search and recorded as "unreviewed, hidden". One new problem since then is described under "Link review".
- **Categories:** your 24 categories are in, and every one of Nave's 5,322 topics is placed under at least one of them. Details are in `docs/CATEGORIES_DRAFT.md`.
- **Traditions:** your five traditions are approved in the database. Strong's and Nave's no longer count toward Methodist, and Jamieson-Fausset-Brown is credited section by section to its actual author.
- **New sources:**
  - Baptist: Maclaren's *Expositions of Holy Scripture* and Broadus on Matthew
  - Lutheran: Luther's Large Catechism, Luther on Galatians and on Genesis 1-3, the Augsburg Confession, Stump's explanation of the Small Catechism, and Gerberding
  - Pentecostal, all published before 1931: Woodworth-Etter, McPherson and Montgomery
- **Your four added contested points** are in, for 11 in all.
- **Lesson records:** the database now has tables for lessons, sections, scripture, quotes, blanks, questions, ratings, the monthly fix cycle and tradition perspective summaries.
- **First batch: 44 lessons**, each exported as slides, a student handout and teacher's notes:
  - 32 on uncontested topics;
  - 12 testing the tradition approach: Baptism and Spiritual Gifts Today, each with an all-views version and one version for each of the five traditions.

  The list and where to start are in `docs/LESSONS.md`.

**Please look at first:** the 12 contested-topic lessons, to judge whether each tradition's view reads fairly. Then one complete uncontested lesson, such as `lessons/output/forgiveness/`, to judge the format.

## Link review

- **Top 300 topics:** every low-confidence link was read and judged. That is 5,326 decisions in all: 1,406 accepted, 3,919 rejected and 1 corrected. About 26% of low-confidence links turned out to be right, which confirms they should not be shown unreviewed.
- **Everything else:** 17,208 low-confidence links are now **hidden** and marked "unreviewed, hidden", ready for a later pass. Search ignores them.
- **One thing you should know.** After the review, I found that Maclaren's expositions and the Lutheran doctrinal works had no subject links at all, because the tagger skipped those kinds of entries. I fixed this and re-ran the tagging, so they can now be found by subject. Re-running it had three effects:
  - **New unreviewed links:** about 2,370 new low-confidence links on the top-300 topics (1,175 from Maclaren, 658 from the ISBE, the rest scattered). They are hidden, so nothing wrong is shown, but those topics are no longer fully reviewed.
  - **Lost links:** about 1,186 earlier review decisions now refer to links the tagger no longer makes. Most were rejections, but about 180 links I had accepted dropped out.
  - **Maclaren's visible links are weaker:** in a sample of 25 of his high-confidence links I scored 66% right, against 82% for the other works. The misses are the old everyday-word problem, for example the topic "Mark" (the person) attached to expositions of Mark's Gospel.

  I can do a second review pass on the top-300 topics if you want one.

## Categories

All 24 are created, and all 5,322 topics are placed, 410 of them under more than one category.

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

Changes since last time:

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

**Lutheran sources excluded as unclear:** Graebner's 1939 Galatians translation (Gutenberg #1549), because a 1939 American book may still be in copyright. Also the modern Small Catechism text (#1670), whose translation date and terms were unclear.

Everything is recorded in `docs/PROVENANCE.md`. Per-work counts are in `docs/COUNTS.md`.

**Library totals:** 44 works, 97,862 entries (about 28.7 million words), 479,415 scripture links, 396,364 subject links and 47,796 related-subject links.

## Contested points

There are now 11 contested points. Your four additions are:

- women in church leadership
- spiritual gifts today ("Tongues" merged into it)
- creation and the age of the earth
- divorce and remarriage

Each is linked to the Nave's topics it touches, either the whole topic or part of one (for example, "Marriage" is partly contested because of divorce).

## The lessons

**Lesson records.** Every lesson is saved with the following:

- **Basic details:** topic, audience, length in minutes and the Bible translation used.
- **Version:** single, all-views, or one tradition's version.
- **Status and visibility:** draft, reviewed or shared; private until promoted.
- **Owner and origin:** who made it, and whether it was batch-made, generated live, or a user's private edited copy.
- **Sections:** in the template's order, with scripture, quotes, blanks, discussion questions and suggested answers.
- **Ratings:** a one-click reason for low ratings (empty for now).
- **The monthly fix-cycle queue** (empty for now).

The minimum number of votes before ratings count is stored as a setting, currently a placeholder of 10. Please tell me the number you want.

**How the first batch was made.** I wrote each lesson myself, following the template exactly, after reading the library's commentary on its passage.

- **Every commentator quote is copied from a library entry.** The loader checks it word for word against that entry and refuses the lesson if it doesn't match. I tested this by changing a single word; the lesson was refused.
- **Credits name the entry's actual author.** For JFB that is the author of that section.
- **Scripture is printed from the KJV**, with paragraph breaks.

**Two choices I made that you'll see; please confirm or change them:**

1. **Translation.** Scripture is printed from the **King James Version**, because the commentators quote it and the handouts' blanks follow it. Each lesson records its translation, so switching a lesson to the World English Bible is a one-word change.
2. **File format.** Handouts and teacher's notes are **Word files (.docx)**, so teachers can edit them. Slides are .pptx. PDF copies are easy to add.

**Checks done.**

- All 44 lessons load with every quote verified and every scripture reference resolved.
- Each lesson's section timings add up to its stated length.
- I rendered sample slides, handouts and teacher's notes to images to check the layout.
- I also checked the short catechism phrases quoted inside two teacher's notes against the library, and corrected them to the library's exact wording.

**Things to know about the batch.**

- **Whose voices are quoted.** The uncontested lessons quote mostly Adam Clarke (78 quotes), Albert Barnes (47) and Matthew Henry (43), because they comment on every verse. Baptist voices (Spurgeon, Maclaren, Broadus) appear mainly in the contested lessons. Later batches can draw more on Maclaren and Spurgeon.
- **Hard passages get a teacher's note.** Where a passage brushes against a contested point, the lesson teaches the agreed ground and adds a note saying that Christians differ. Examples: 1 Corinthians 13:8 (tongues ceasing), Ephesians 2:8 (grace and faith), Psalm 103:3 (healing), John 14:3 (end times) and Acts 2:42 (breaking of bread).
- **The perspective summaries are my own wording, not quotations.** Each tradition's view is summarised fairly, with the texts it leans on (`ingest/data/perspectives.tsv`). The only quotation is a few words of the public-domain Westminster Confession. No modern denominational statement is quoted.
- **The tradition lessons quote each tradition's own writers.** For example, Luther and the Augsburg Confession for Lutherans, Broadus and Maclaren for Baptists, Clarke for Methodists, Henry and Barnes for Reformed, and Woodworth-Etter and Montgomery for Pentecostals. Where a tradition's own writer disagrees with its usual view, the teacher's note says so. For example, Barnes (Presbyterian) reads "tongues shall cease" as referring to heaven, and Maclaren (Baptist) says the same.

## Known gaps and accuracy limits (new)

- **Link review:** see the problem described under "Link review" above.
- **Spurgeon's scanned sermon volumes** include publishers' advertisements at the end of some entries. They should be trimmed in a later clean-up.
- **Barnes' New Testament notes** contain some placeholder entries that say "No entries in BARNES for this verse".
- **Text quality:** the OCR books (Broadus, Luther on Galatians, the three Pentecostal books, Barnes' Old Testament) read less cleanly than the Gutenberg books. They are fine for finding and reading, but need care before quoting.
- **Category accuracy** is measured on samples only; see the table above.

## What I need from you

1. **Review the 12 contested-topic lessons and `ingest/data/perspectives.tsv`.** Is each tradition's view fair?
2. **Translation and file format:** KJV and Word files, or something else?
3. **Should the all-views lessons put the five views on a slide and in the handout?** At present, following the brief, "Where Christians differ" appears only in the teacher's notes.
4. **The minimum number of ratings** before they count (placeholder: 10).
5. **The order of the 24 categories**, and the 198 uncertain placements in `review/category_review.csv` when you have time.
6. **Optional: a second review pass** on the roughly 2,370 newly hidden links on the top-300 topics.

## Where things are

- **The database:** `library.db`, stored compressed in `data/` (`python3 tools/restore_db.py` unpacks it). `python3 build.py --fresh` rebuilds everything, including categories and lessons.
- **Lessons:** source files are in `lessons/source/`; output files are in `lessons/output/<code>/`. `python3 -m ingest.lessons` reloads the lessons and `python3 tools/export_lessons.py` re-exports them.
- **Research helper:** `python3 tools/lesson_sources.py "Matthew 18:21-35" --topic Forgiveness` shows the library material behind a passage. I used it to write every lesson.
- **Search test:** `python3 search.py forgiveness` (outputs saved in `docs/search_test_*.txt`).
