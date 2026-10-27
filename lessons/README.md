# Lessons

`source/` holds one plain-text file per lesson version. `python3 -m ingest.lessons` checks them and loads
them into the database; `python3 tools/export_lessons.py` turns each one into slides (.pptx), a student
handout (.docx) and teacher's notes (.docx) under `output/`.

## File format

```
code: forgiveness                 # unique; tradition versions are <family>--<tradition>
family: forgiveness               # versions of one lesson share this
version: single                   # single | all_views | tradition:<code>
issue: baptism                    # contested lessons only (code from ingest/data/contested_topics.tsv)
title: ...
big_idea: one sentence the class should walk out remembering
topic: Forgiveness                # the main Nave's topic
also: Mercy; Debtor               # other Nave's topics the lesson covers
audience: adults
minutes: 45
translation: KJV                  # Bible printed in the handout and slides
passage: Matthew 18:21-35

== opening | 4                    # section | suggested minutes | heading (teaching points)
Text...
note: shown only in the teacher's notes

== scripture | 4
== background | 5
== point | 7 | Heading of the teaching point
Text...
verses: Luke 17:3-4; Colossians 3:13
quote: <entry id> | exact words copied from that library entry
blank: Sentence with ____ for the student handout | answer

== differ | 6                     # contested lessons only
view: baptist                     # pulls that tradition's summary from ingest/data/perspectives.tsv
== questions | 8
q: Question? | suggested answer for the teacher
== application | 3
== prayer | 2
```

The loader refuses a file whose quote is not word for word in the cited entry, whose references
do not resolve, whose sections are out of the template's order, or whose "Where Christians differ"
section appears on an uncontested lesson (or is missing from a contested one).
