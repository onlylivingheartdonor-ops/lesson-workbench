# The first batch of lessons

44 lessons, all status **draft** (written by me, Claude, from the library; not yet reviewed by you). Each has these files in `lessons/output/<code>/`:

- `<code>-slides.pptx`: title, scripture, teaching points and discussion questions
- `<code>-handout.docx` and `.pdf`: scripture, an outline with fill-in blanks, discussion questions and "This week"
- `<code>-teacher.docx` and `.pdf`: everything, including background, commentator quotes with credits, suggested timing, the blanks' answers and suggested answers to the questions

All are for adults, about 45 minutes. Scripture is printed from the King James Version, as you decided. Another of the library's Bibles (ASV, BBE or WEB) can be chosen at export; see "How to change a lesson" below.

## 32 lessons on uncontested topics

| Lesson | Title | Passage | Category |
|---|---|---|---|
| prayer | Teach Us to Pray | Matthew 6:5-15 | Prayer and Worship |
| faith | Faith That Pleases God | Hebrews 11:1-10 | Salvation and Grace |
| forgiveness | Forgiven People Forgive | Matthew 18:21-35 | Salvation and Grace |
| love | The More Excellent Way | 1 Corinthians 13 | Christian Character |
| grace | Saved by Grace | Ephesians 2:1-10 | Salvation and Grace |
| praise | Forget Not All His Benefits | Psalm 103:1-13 | Prayer and Worship |
| suffering | Treasure in Clay Jars | 2 Corinthians 4:7-18 | Suffering, Comfort and Hope |
| joy | Rejoice in the Lord Always | Philippians 4:4-13 | Christian Character |
| repentance | Coming Home to the Father | Luke 15:11-24 | Salvation and Grace |
| humility | The Mind of Christ | Philippians 2:1-11 | Christian Character |
| temptation | It Is Written | Matthew 4:1-11 | Sin and Temptation |
| worship | Worship in Spirit and in Truth | John 4:19-26 | Prayer and Worship |
| thankfulness | Where Are the Nine? | Luke 17:11-19 | Prayer and Worship; Holidays (Thanksgiving) |
| word-of-god | Thy Word Is a Lamp | Psalm 119:97-105 | The Bible |
| obedience | To Obey Is Better Than Sacrifice | 1 Samuel 15:13-23 | Christian Character |
| wisdom | Trust in the Lord with All Your Heart | Proverbs 3:1-12 | Christian Character |
| hypocrisy | Clean Inside and Out | Matthew 23:23-28 | Sin and Temptation |
| pride | God Be Merciful to Me a Sinner | Luke 18:9-14 | Sin and Temptation |
| heaven | A Place Prepared | John 14:1-6 | Heaven, Hell and the End Times |
| resurrection | But Now Is Christ Risen | 1 Corinthians 15:12-22 | Jesus Christ; Holidays (Easter) |
| anger | Be Angry, and Sin Not | Ephesians 4:25-32 | Sin and Temptation |
| covetousness | Rich Toward God | Luke 12:13-21 | Work, Money and Giving |
| giving | God Loves a Cheerful Giver | 2 Corinthians 9:6-15 | Work, Money and Giving |
| courage | Be Strong and of a Good Courage | Joshua 1:1-9 | Christian Character |
| children | Teach Them Diligently | Deuteronomy 6:4-9 | Family and Relationships |
| integrity | Faithful in Everything | Daniel 6:1-10 | Christian Character |
| first-love | Return to Your First Love | Revelation 2:1-7 | Sin and Temptation |
| fellowship | They Continued Stedfastly | Acts 2:42-47 | The Church |
| testimony | Come, See a Man | John 4:28-42 | Sharing the Faith |
| neighbor | Who Is My Neighbour? | Luke 10:25-37 | Family and Relationships |
| christmas | Good Tidings of Great Joy | Luke 2:1-20 | Jesus Christ; Holidays (Christmas) |
| intercession | Standing in the Gap | Genesis 18:20-33 | Prayer and Worship |

## 12 lessons on two contested points (the tradition test)

| Family | Versions |
|---|---|
| **Baptized into Christ** (baptism; Matthew 28:18-20, Romans 6:3-4) | `baptism` (all views), `baptism--baptist`, `--wesleyan`, `--reformed`, `--lutheran`, `--pentecostal` |
| **Gifts of the Spirit** (spiritual gifts today; 1 Corinthians 12:1-11) | `spiritual-gifts` (all views), `spiritual-gifts--baptist`, `--wesleyan`, `--reformed`, `--lutheran`, `--pentecostal` |

How the versions work:

- Teaching points 1 and 2 are the **shared ground**, word for word the same in every version.
- In the **all-views** version, teaching point 3 is also shared, and "Where Christians differ" lays out all five views, each described as its own members would describe it.
- In each **tradition** version, teaching point 3 teaches that tradition's view, quoting its own writers (for example Luther's Large Catechism and the Augsburg Confession for the Lutheran baptism lesson). "Where Christians differ" is still stored with the lesson but marked **hidden unless the user turns it on**.
- **Where "Where Christians differ" appears**, as you decided:
  - **All-views version:** in the teacher's notes, the student handout and on one slide. The slide gives each tradition's view in one line; the handout gives each view in full.
  - **Tradition versions:** only in the teacher's notes, marked as hidden by default, because the class does not see it unless the user turns it on.

## What to look at first

1. **The two contested families**, especially the five tradition versions of each. Do the views read fairly to members of each tradition? The summaries, and the one-line versions on the all-views slide, are in `ingest/data/perspectives.tsv`.
2. **One finished set of files**, for example `lessons/output/forgiveness/`, to judge the plain design of the slides and handouts.
3. **The quotes.** Every quote is checked word for word against the library, and the loader refuses a lesson otherwise. What a check cannot judge is whether a quote is well chosen and fairly used in context.

## How to change a lesson

Each lesson is a plain-text file in `lessons/source/` (the format is described in `lessons/README.md`). After editing, run `python3 -m ingest.lessons` and then `python3 tools/export_lessons.py <code>`. To print the scripture from another Bible, add `--translation ASV`, `BBE` or `WEB`; those files get the translation in their names (for example `forgiveness-handout-WEB.pdf`), so the KJV files stay as they are. The lessons were written against the KJV wording, so a fill-in blank that echoes a KJV phrase may not match another translation word for word. The two contested families are generated by `lessons/tools/make_baptism.py` and `make_spiritual_gifts.py`, so shared sections stay identical. Edit those scripts rather than the generated files.
