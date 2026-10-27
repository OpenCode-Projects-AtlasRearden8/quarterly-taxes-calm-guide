# Quarterly Taxes Calm Guide

> **Education only.** This guide explains US self-employment paperwork concepts in plain
> English. It is **not** tax, legal, accounting, or financial advice, and it makes **no
> promises about numbers**. Tax rules change and differ from person to person. Always
> verify current details with the official IRS and your state tax agency, and talk to a
> qualified professional before acting on anything here.

A calm, beginner-friendly paperwork manual for US self-employed people and single-member
LLC owners (and the generally curious). It explains the **estimated-tax rhythm**, how to
think about **set-aside percentages**, **what receipts to keep**, **1099s decoded**, a
**simple quarterly ritual**, and **when to call a professional** — plus printable
worksheets (due-date calendar, panic-meter checklists) and a plain-English glossary.

Ships as markdown in [`docs/`](docs/) and as a static HTML site built locally by a
zero-dependency Python build script. No accounts, no network required, nothing published.

## At a glance

| What | Where |
| --- | --- |
| Start here / map of the guide | [`docs/00-start-here.md`](docs/00-start-here.md) |
| Estimated-tax rhythm explained | [`docs/01-estimated-tax-rhythm.md`](docs/01-estimated-tax-rhythm.md) |
| Set-aside percentages (think, don't memorize) | [`docs/02-set-aside-percentages.md`](docs/02-set-aside-percentages.md) |
| What receipts to keep | [`docs/03-receipts-what-to-keep.md`](docs/03-receipts-what-to-keep.md) |
| 1099s decoded | [`docs/04-1099s-decoded.md`](docs/04-1099s-decoded.md) |
| A simple quarterly ritual | [`docs/05-quarterly-ritual.md`](docs/05-quarterly-ritual.md) |
| When to call a professional | [`docs/06-when-to-call-a-professional.md`](docs/06-when-to-call-a-professional.md) |
| Due-date calendar worksheet | [`docs/worksheets/due-date-calendar.md`](docs/worksheets/due-date-calendar.md) |
| Panic-meter checklists (ADHD-friendly) | [`docs/worksheets/panic-meter.md`](docs/worksheets/panic-meter.md) |
| Plain-English glossary | [`docs/glossary.md`](docs/glossary.md) |

## How to run (local-first)

Requires only Python 3 (3.9+ recommended). Everything runs on your machine.

```bash
# Build the static site (regenerates ./site from ./docs)
python3 build.py

# Look at it locally (no publishing, just your own browser)
python3 -m http.server 8000 --directory site
# then open http://localhost:8000 in your browser

# Run the test suite (builds into a temp dir and checks pages, links, disclaimers)
python3 -m unittest discover -s tests -v

# Or do both in one go
./verify.sh
```

## Repo layout

```
.
├── LICENSE                     MIT license
├── README.md                   you are here
├── STATUS.md                   what was built, how to run, verification, known gaps
├── build.py                    markdown -> static HTML site (pure stdlib, no deps)
├── verify.sh                   build + tests convenience script
├── assets/
│   └── styles.css              stylesheet copied into the generated site
├── docs/                       the manual (markdown, the source of truth)
│   ├── 00-start-here.md
│   ├── 01-estimated-tax-rhythm.md
│   ├── 02-set-aside-percentages.md
│   ├── 03-receipts-what-to-keep.md
│   ├── 04-1099s-decoded.md
│   ├── 05-quarterly-ritual.md
│   ├── 06-when-to-call-a-professional.md
│   ├── worksheets/
│   │   ├── due-date-calendar.md
│   │   └── panic-meter.md
│   └── glossary.md
├── site/                       generated static HTML (rebuild anytime)
└── tests/                      unittest suite (site output, links, disclaimers, hygiene)
```

## Companion guides (we don't repeat each other)

This guide is one of a series of plain-English, education-only manuals:

- **`llc-first-year-handbook`** — forming and running your LLC: entity choices, EINs,
  operating agreements, bank accounts, bookkeeping setup basics.
- **`cashflow-simple-ledger`** — tracking money in and out: a simple ledger habit and
  how to read your own numbers.
- **`quarterly-taxes-calm-guide`** (this one) — the tax-paperwork *rhythm*: estimated
  payments, set-asides, receipts, 1099s, and the quarterly ritual.

Boundaries on purpose: forming the company lives in the LLC handbook; how to record
money lives in the ledger guide; how to pay the government on schedule lives here.

## Credits

Built and maintained by **Asdale Dynamics, LLC** as part of its plain-English,
low-energy, ADHD-friendly life-admin guide series. Licensed under the MIT license —
see [`LICENSE`](LICENSE).
