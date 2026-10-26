# Phase 1 Report: The Reference Library

Prepared for Dave, 26 October 2026.

## The short version

The library is built and working. One database now holds 4 Bibles, the three linking indexes (Nave's, the Treasury of Scripture Knowledge, Strong's Hebrew and Greek), 4 of the 5 commentaries, all 3 dictionaries and encyclopedias, and 15 books of sermons and devotional writing by Bounds, Ryle, Moody and Spurgeon. Every work is public domain, and each one has its source, edition and license evidence recorded.

A subject search works the way you described. Searching "forgiveness" returns:

- 46 linked verses
- 260 commentary notes from Henry, Clarke, Barnes and Jamieson-Fausset-Brown
- the ISBE and Easton's articles
- Moody's chapter on forgiveness
- the key Greek word (*aphiemi*, "to forgive")
- related subjects: Enemy, Justification, Mercy, Good for Evil, Retaliation and others

The full outputs are in `docs/search_test_forgiveness.txt`, `docs/search_test_prayer.txt` and `docs/search_test_matthew_6_14.txt`.

**Two things I need from you:**

1. **The top-level subject categories.** Per your instructions I have not invented them. The database has a place ready for them (a "category" level above Nave's 5,322 topics). What I need is in "What I need from you" below.
2. **Decisions on four gaps:** John Gill, Spurgeon's sermons, Barnes' Old Testament notes, and one share-alike Strong's file. Details are under "Sources skipped and why".

## What was ingested

| Work | What it is | What's in the database |
|---|---|---|
| **King James Version** | Bible | 31,102 verses, plus 348,884 links from KJV words to Strong's numbers |
| **American Standard Version (1901)** | Bible | 31,086 verses (16 verses the ASV leaves out on purpose, e.g. Matthew 17:21) |
| **Bible in Basic English** | Bible | 31,102 verses |
| **World English Bible** | Bible | 31,098 verses (4 left out on purpose). This edition uses "LORD", not "Yahweh". |
| **Nave's Topical Bible** | Subject index | 5,322 topics, 14,139 sub-headings, 77,908 topic-to-verse links, 7,272 "See also" links |
| **Treasury of Scripture Knowledge** | Cross-references | 380,163 verse-to-verse references covering 29,359 verses |
| **Strong's Hebrew and Greek** | Word dictionaries | 8,674 Hebrew and 5,741 Greek entries |
| **Matthew Henry (Complete)** | Commentary | 5,355 sections plus chapter introductions, whole Bible |
| **Adam Clarke** | Commentary | 21,051 notes, whole Bible |
| **Albert Barnes** | Commentary | 7,543 notes and introductions, **New Testament only** (see gaps) |
| **Jamieson-Fausset-Brown** | Commentary | 16,895 notes, whole Bible |
| **Easton's Bible Dictionary** | Dictionary | 3,963 articles |
| **Smith's Bible Dictionary** | Dictionary | 4,639 articles |
| **ISBE (1915)** | Encyclopedia | 9,349 articles |
| **E. M. Bounds** | Devotional | Power Through Prayer, Purpose in Prayer, The Essentials of Prayer, The Reality of Prayer, Prayer and Praying Men |
| **J. C. Ryle** | Devotional | Practical Religion, The Cross |
| **D. L. Moody** | Sermons | The Way to God, Secret Power, Weighed and Wanting, Prevailing Prayer, The Overcoming Life, Sovereign Grace |
| **C. H. Spurgeon** | Devotional | Around the Wicket Gate, Gleanings among the Sheaves (short excerpts from his sermons) |

**Totals:**

- 89,036 entries (notes, articles, chapters)
- 436,363 scripture links from those entries
- 353,680 links from entries to subjects
- 46,712 links between related subjects

Every verse of the Bible has at least one commentary note filed under it.

Per-work counts of entries, scripture links, subject links and review-list items are in `docs/COUNTS.md`. The provenance table (source URL, edition, license evidence and file checksums for every work) is in `docs/PROVENANCE.md`.

## How the linking works

Everything uses one verse-numbering scheme: 66 books, with chapter and verse numbers as in the KJV. A note "on Matthew 6:14-15" and a Nave's reference to "Mt 6:14" both point at the same verses. The WEB places Romans 16:25-27 at the end of Romans 14; I moved those verses back to the usual place.

1. **Structural links first, made without guessing.**
   - Commentary notes are linked to the passage they are filed under.
   - Every scripture reference written inside a note or article is linked to its verse.
   - A commentary note is linked to a Nave's topic when Nave's lists that note's verse under the topic.
   - A dictionary article is linked to the Nave's topic with the same name, e.g. Easton's "Forgiveness of sin" with Nave's "Sin, Forgiveness of".
   - For the sermons, which mostly quote scripture without giving the reference, I added a quotation finder. When a passage repeats 9 or more words of a KJV verse word-for-word, it is linked to that verse. This found 1,632 quotations.
2. **Machine-assisted tagging second.** It covers what structural linking cannot reach: about 6,000 dictionary articles with no matching topic, Barnes' book introductions, and the sermons and devotional books. It scores each entry against every Nave's topic using three things: whether the topic's name appears in the entry's title, how often the name appears in the text, and how similar the wording is to Nave's own wording.
   - **This is a statistical method, not an AI language model.** This session had no AI service account to call, so it could not use one.
   - Every link made this way is marked as such and carries its confidence value.
3. **Review list.** 16,616 links below the confidence threshold are marked "awaiting review" instead of being accepted. You can open the list in a spreadsheet: `review/review_queue.csv`. The search tool labels these links as low confidence.
4. **Related subjects** are derived three ways:
   - Nave's own "See also" pointers: 7,272
   - topics whose verse lists overlap: 20,344
   - topics that the same commentary notes and articles keep being linked to, counted only when at least two different works agree: 19,096

## Measured tagging accuracy

I spot-checked random samples from every work. The samples were taken from both the high-confidence and low-confidence links. For each link I asked: "Would a teacher looking up this subject want this entry?" A link scored correct (1), partly right (½) or wrong (0).

**Important: these checks were done by me, Claude, reading each sample, not by a person.** Please treat them as a first measurement. It's worth having you (or a helper) spot-check 20-30 links yourself.

I ran two rounds. Round 1 found real problems, which I fixed. Round 2 then used a fresh random sample, so the final numbers are not measured on the same cases I tuned against.

| Kind of link | Round 1 | Round 2 (current) |
|---|---|---|
| Headword match (dictionary article ↔ same-named topic) | 94% (18 checked) | **100%** (18) |
| Verse-based, high-confidence band | 85% (24) | **94%** (24) |
| Verse-based, low-confidence band | 58% (18) | **65%** (24) |
| Machine-assisted, high-confidence band | 47% (38) | **82%** (36) |
| Machine-assisted, low-confidence band | 32% (46) | **36%** (36). These are the ones held in the review list. |

| Scripture references | Result (current) |
|---|---|
| References read from plain text | **98%** (25 checked, after the fix described below) |
| Quotations matched to KJV verses | **100%** (25) |
| References whose markup I corrected (sample, see below) | **18 of 18** corrections were right |

Spot-check results by work are in `review/accuracy.json`. The verdicts themselves, which you can read or correct, are in `review/spot_checks.csv` (round 2), `review/spot_checks_round1.csv` and `review/scripture_link_checks.csv`.

What the numbers mean in practice:

- **High-confidence links are good enough to show teachers** (82-100%).
- **Low-confidence links are often wrong.** That is why they wait in the review list and are labelled in search results.
- **The verse-based links are only as good as their verse.** A note on a verse that Nave's files under a topic usually is about that topic. Occasionally the verse is listed for a minor detail (e.g. "Women" for 1 Kings 18).

## Problems found and fixed during the build

- **Wrong references in the source markup.** Some editions tag shorthand references to the wrong book. In Easton's, the "11" in "Rev. 1:8, 11" is tagged as Genesis 1:11; JFB tags "Ge 1:1, 2" as 2 Corinthians 1:2. I re-read such references from their visible text. This corrected 796 references in Easton's, 1,287 in JFB, 360 in ISBE and 6 in Henry. Smith's hand-written references were trusted as given.
- **Roman numerals.** My plain-text reference reader was mistaking words for Roman numerals ("Daniel **i**s touched" read as Daniel chapter 1). The spot check caught it. It is fixed, and a fresh check scored 98%.
- **Barnes edition quirks.** I skipped 26 duplicated verse notes that the edition places in the wrong slots, and 21 "No specific Barnes text on this verse" placeholders.
- **Title-only introductions.** Some "introduction" slots in Henry and JFB held only the book's title line. These were dropped, because the tagger was guessing on them.
- **Nave's.** "Phm 1:10-18" was split across the markup and read as the whole of Philemon. It is fixed, along with all one-chapter books (Jude 14 = Jude 1:14).

## Known gaps and accuracy limits

- **Barnes covers the New Testament only.** The edition I used has no Old Testament notes. Barnes' Revelation introduction is also missing from that edition.
- **Strong's Greek is missing 31 numbers that the KJV uses**, e.g. G3778 *houtos*, "this". The Hebrew dictionary has no Hebrew script, only transliteration (*'elohiym*).
- **Machine-assisted tags are weakest for everyday-word topics.** Nave's has topics named "Work", "Way", "World" and "Present", and these get attached to texts that merely use the word. Most such links are in the low-confidence band.
- **Very short dictionary entries** (one-line name entries) are sometimes tagged to a neighbouring person or place from the same verse list. This usually happens in the low-confidence band.
- **121 dictionary articles and 56 commentary notes have no subject link.** They are still findable by scripture.
- **No full-text word search index yet.** The search tool works from the subject and scripture links. A word-search index is a Phase 2 web-app task.
- **Bounds' "Preacher and Prayer" was not added.** It is an earlier edition of the same text as "Power Through Prayer".
- **License notes worth knowing** (all recorded in the provenance table):
  - **KJV:** public domain everywhere except the United Kingdom, where the Crown controls printing.
  - **BBE:** public domain in the US (published in 1965 without a copyright notice); possibly still protected in the UK.
  - **WEB:** public domain, but "World English Bible" is a trademark. We must not alter the text if we call it the WEB.
  - **Project Gutenberg books:** public domain in the US; other countries not checked.
- **One editorial chain to be aware of.** Several CrossWire modules (Henry, Nave's, Easton's, JFB) say they were prepared from CCEL's texts. CrossWire distributes them as public domain, and a faithful transcription of a public-domain book is not itself copyrightable in the US. CCEL's current website, however, asks for permission for commercial use of *its own* editions. I judged the CrossWire editions acceptable, but this is your call. If you'd rather be cautious, those four works can be swapped for other sources.

## Sources skipped and why

| Source | Why | What would fix it |
|---|---|---|
| **John Gill's Exposition** | No downloadable edition with clear terms was reachable. It isn't in CrossWire or CCEL, and sacred-texts.com blocks automated downloads. Other sites (StudyLight, Bible Hub) show Gill on their own websites, but their terms for copying are unclear. | Point me to a file you're comfortable with, or approve a specific source. |
| **Spurgeon's sermons (the 63-volume set)** | The only complete digital edition I found is CCEL's. CCEL's policy allows "personal, educational, or non-profit purposes" and asks for permission for commercial use. A subscription product is commercial, so I stopped, as your rules require. Only two small Spurgeon books from Project Gutenberg are included. | Ask CCEL for permission, or let me look for scanned volumes on archive.org (lower text quality, needs more cleanup). |
| **Barnes' Old Testament notes** | Not in the CrossWire edition. CCEL has some volumes (Job, Psalms, Isaiah, Daniel), but under the same CCEL terms. | Same as above. |
| **Open Scriptures Strong's Greek (would fill the 31 missing numbers and add Greek script)** | Its license is CC-BY-SA ("share-alike"). That requires attribution, and may require releasing our own derived data under the same license. Your rules allow attribution licenses only when the attribution is recorded and displayed; share-alike adds more than that, so I left the decision to you. | Your yes/no. |

## What I need from you

1. **Top-level categories.** Tell me the lay-friendly categories you want above Nave's topics, for example the handful a Sunday School teacher would think in. Once you give me the list, I'll place Nave's 5,322 topics under them. Each placement will be marked with how it was made, and uncertain ones will go to the review list. If it helps, I can draft a proposed list for you to edit, but I haven't made one without your go-ahead.
2. **Gill, Spurgeon, Barnes OT, and the CC-BY-SA file:** a decision on each, per the table above.
3. **Optional:** a short human spot-check of the review list, or of `review/spot_checks.csv`, so the accuracy numbers have a person's judgement behind them too.

## Where things are (for whoever builds Phase 2)

- `library.db` is the database. It is stored compressed in `data/` (in 45 MB parts, because GitHub won't take larger files). `python3 tools/restore_db.py` unpacks it.
- `python3 build.py --fresh` rebuilds everything from the original sources in about 2½ minutes. It downloads the raw files into `raw/` on first use.
- `python3 search.py forgiveness` is the search test. `python3 search.py --verse "John 3:16"` looks up a passage.
- `ingest/` holds one script per source. Each one can be rerun on its own and replaces only its own works.
- `schema.sql` is the database design, written to move to PostgreSQL later.
