# Top-level subject categories (approved)

**Status: approved by Dave, with his changes (24 categories). Every one of Nave's 5,322 topics is now placed under at least one category.** (This file keeps its old name, `CATEGORIES_DRAFT.md`, so links to it still work.)

A topic can sit under more than one category; 410 topics do (for example "Love" is under both *God* and *Christian Character*).

| # | Category | What a teacher would look for here | Topics |
|---|---|---|---|
| 1 | God | Who God is and what he is like | 91 |
| 2 | Jesus Christ | His life, death, resurrection, and who he is | 64 |
| 3 | The Holy Spirit | The Spirit's work and gifts | 10 |
| 4 | The Bible | God's Word, and reading and studying it | 44 |
| 5 | Salvation and Grace | How God saves, and what it means to be saved | 59 |
| 6 | Prayer and Worship | Praying, praising, giving thanks, the Lord's Day | 83 |
| 7 | Christian Character | Virtues and how believers should live | 164 |
| 8 | Sin and Temptation | What goes wrong, and resisting it | 309 |
| 9 | Suffering, Comfort and Hope | Hard times, grief, illness, death and comfort | 100 |
| 10 | Family and Relationships | Marriage, parents and children, friends and neighbours | 76 |
| 11 | The Church | The church, its leaders, its ordinances and its life together | 61 |
| 12 | Sharing the Faith *(new)* | Witnessing, evangelism and missions | 14 |
| 13 | Work, Money and Giving | Work, wealth and poverty, generosity | 115 |
| 14 | Heaven, Hell and the End Times | Life after death, judgment, the last days | 39 |
| 15 | Angels and Satan | The unseen spiritual world | 32 |
| 16 | Prophecy and Promises | God's promises, covenants and prophecies | 28 |
| 17 | Old Testament Worship and Law | The Law, tabernacle, temple, priests, sacrifices and feasts | 165 |
| 18 | Government and Justice | Kings and rulers, justice, war and peace | 246 |
| 19 | Everyday Life in Bible Times | Customs, food, clothing, farming, animals, money | 877 |
| 20 | Old Testament People *(split)* | People and peoples of the Old Testament | 1,798 |
| 21 | New Testament People *(split)* | People of the New Testament | 254 |
| 22 | Places of the Bible | Cities, lands, mountains, rivers and other named places | 1,038 |
| 23 | Books of the Bible *(new)* | The books of the Bible and their writers | 42 |
| 24 | Holidays and Seasons *(new)* | Christmas, Easter, Pentecost, Thanksgiving and the biblical feasts | 38 |

The order above is the order the app will show unless you change it. I placed "Sharing the Faith" next to "The Church" and the two other new categories at the end; please move them if you'd like.

## How topics were placed

1. **Structural rules (2,256 placements, people and places).** Nave's own first line for a name ("Son of Shimhi", "A city of Italy") says whether a topic is a person, a people or a place. People go to Old or New Testament People by where most of their verses fall. A fresh spot check of 100 rule-placed topics found 95 right. The 5 wrong ones (subjects like "Regicide" that the rules took for people) were corrected by hand, and a further search corrected 10 more.
2. **Placed by me, Claude, reading each topic (3,491 placements).** Everything else was read and placed one by one. 198 placements I was unsure of are marked with a lower confidence and listed in `review/category_review.csv` for you to check.
3. **Your changes.** Edit `ingest/data/category_placements.tsv` (one line per topic). A line you add or change can be marked `manual`, and it always overrides the automatic placement.

## Gaps to know about

- **Books of the Bible:** Nave's has topics for only about 40 of the 66 books, and many of those are the writer (e.g. "Isaiah" the prophet). I placed the writer topics here too. In the web app this category will work best by linking to each book's introduction in the commentaries, which the library has for every book.
- **Holidays and Seasons:** Nave's has no "Christmas" or "Easter" topic. I placed the nearest topics (Incarnation, Resurrection, Advent, Pentecost, Thanksgiving, Passover, the feasts, Mary, Bethlehem, the Magi, and others), plus the Christmas, Easter and Thanksgiving lessons.
- **The Holy Spirit** has only 10 topics, because Nave's gathers most teaching on the Spirit under one large "Holy Spirit" topic.
