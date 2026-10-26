# lesson-workbench

Bible Lesson Workbench (working title). Phase 1: the public-domain reference library.

- **Report for Dave:** [docs/REPORT.md](docs/REPORT.md). Covers what was ingested, measured accuracy, gaps and open questions.
- **Provenance of every work:** [docs/PROVENANCE.md](docs/PROVENANCE.md)
- **Counts per work:** [docs/COUNTS.md](docs/COUNTS.md)

## Quick start

```
python3 tools/restore_db.py          # unpack library.db from data/ (no downloads)
python3 search.py forgiveness        # subject search test
python3 search.py --verse "John 3:16"
```

To rebuild from the original sources instead (downloads about 75 MB into `raw/`, about 2½ minutes):

```
python3 build.py --fresh
python3 tools/package_db.py          # refresh the compressed copy in data/
python3 tools/write_provenance.py    # refresh docs/PROVENANCE.md and docs/COUNTS.md
```

Only the Python standard library is needed.

## Layout

| Path | What it is |
|---|---|
| `schema.sql` | Database design (portable to PostgreSQL) |
| `library/` | Shared code: scripture scheme and reference parsing, SWORD module reader, markup cleanup, text model |
| `ingest/` | One rerunnable script per source, plus `tagging.py` (subject links) and `spot_checks.py` |
| `build.py` | Runs every ingest step in order |
| `search.py` | Command-line search test |
| `review/` | Spot-check samples and verdicts, `accuracy.json`, and the low-confidence review list (`review_queue.csv`) |
| `data/` | The built database, compressed and split into parts under GitHub's file-size limit |
| `raw/` | Downloaded source files (not in version control) |
