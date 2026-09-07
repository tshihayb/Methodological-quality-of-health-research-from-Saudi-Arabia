# Methodological quality of health research from Saudi Arabia

Data and code for a cross-sectional meta-research study of 385 health research
papers with at least one Saudi-affiliated author, published in 2022.

The pipeline is here as code: sampling frame, screening, allocation of papers to
reviewers, calibration, dual review, adjudication, enrichment, scoring, the
stratified analyses, and the scripts that draw the tables and figures. The data
that ships is the analysis layer: the files the published displays actually
read.

**The paper itself is not here.** The manuscript, its drafts, the assembler that
builds it, the citation and renumbering tools and the submission planning are
all outside this repository. What is published is the method and the evidence
for the numbers, not the article, which is published by its journal.

The displays are not shipped either, because they do not need to be.
`reproduce.py` draws all 26 from the data here and collects them into
`displays/` under the names and formats the submission uses,
`Figure_1_PRISMA.png` through `Supplementary_Table_S3_caveat_register.xlsx`.
Each was checked against the submitted file before that claim was made: the
images byte for byte, the Word and Excel documents by content, since those
formats embed a timestamp and never match byte for byte. A committed copy could
drift from the code beside it; a rebuild cannot.

## The appraised papers cannot be identified here, deliberately

Every study in this sample carries at least one methodological flaw. A table
saying "PMID 12345678 has a confounding flaw its authors never acknowledged"
passes a verdict on identifiable researchers who did not consent to being
assessed and have no right of reply. The finding is about a literature, not
about individuals, and the data are released at that level.

**The surrogate covers 1,031 papers, not 385.** The screening ledger records
every paper that was looked at and whether it was included, so publishing it
with real identifiers would reveal the 385 as surely as the analysis dataset
would. Studies appear as `STUDY-0001` to `STUDY-1031`, spanning the 1,000
sampled records, the 18-paper top-up pool and the 13 calibration papers, which
are 2021 pilot studies outside the main sample. The order is randomised under a
fixed seed, so the numbering encodes neither the PubMed ordering nor the
screening sequence. The map back to real identifiers is generated outside this
repository and never committed.

Reviewers are `R1` to `R13`, never named, on the same contiguous numbering the
calibration figures use.

### Three rules, in the order they apply

The de-identification used to work by removing what it recognised as
identifying. That is a denylist, and a denylist fails quietly: twelve leak
classes were found in it, each after the release gate had already passed. The
last three were not shapes anyone could have listed in advance. A column called
`corr_author` held 366 corresponding-author surnames. A supplementary figure
named 116 institutions, 56 of which carried a single paper, in a bitmap no text
scanner could read. And the journal name had been dropped while publisher
country, an exact SJR value, a SCImago coverage span and a subfield were kept,
which recovers the journal from a public table: on that combination alone 304 of
the 385 studies were unique.

So the default is inverted.

1. **File allowlist.** A file ships only if the reproduction reads it. 46 data
   files ship; 402 do not, and `MANIFEST_WITHHELD.md` names every one of them
   with the reason.
2. **Column allowlist.** Within a file, a column ships only if some published
   script names it. Of the columns previously published, 73 per cent were read
   by nothing.
3. **k = 5.** No published category may carry fewer than five papers. Rarer
   values are merged into an explicit `Other`, which keeps the totals
   reconciling, rather than deleted. 33 institutions are named and the other 83
   are reported as one line; five sector types with eight papers between them
   merge; eight cities merge.

Rule 3 applies to quasi-identifiers only: attributes a reader can also observe
from PubMed, from SCImago or JCR, or from the paper's own front matter. It is
never applied to item responses or derived scores, because a rare answer option
is a finding rather than a leak, and suppressing it would change the study's
results.

## What a determined reader could still do

This is not anonymity in the strong sense, and the limit is worth stating
precisely rather than leaving to be discovered.

Every stratifier this study examines is an attribute of a public paper. A row
carrying several of them at once is therefore close to unique however it is
encoded: 159 of the 310 scored papers have a unique combination of the eleven
published stratifiers, even though no single stratifier has a cell below 37
papers. Collapsing until the combination itself reached five would mean dropping
most of the stratifiers, which is the analysis.

What that costs an attacker is smaller than the headline. Only three of the
eleven attributes are cheap and reliable to compute for a candidate paper: team
size, journal quartile, and whether the first, last and corresponding authors
are Saudi. On those alone 20 papers are unique, and on team size with quartile
none are. The rest, task and design and sector composition and funding level,
are the variables this study needed two reviewers and an adjudicator to settle;
a machine pass on funding got 20 of them wrong at high confidence. An attacker
who can reproduce those has largely redone the study.

`tools/verify_k_anonymity.py` measures this on every build and holds it to a
ratchet: the figure may fall, never rise.

## Running it

```bash
python reproduce.py --list
```

```bash
python reproduce.py
```

Run from this directory. R 4.5.2 and Python 3.14 were used. SAS was retired from
the pipeline on 2026-08-31 and is not required.

**Every display in the paper rebuilds from what ships here**: Figures 1 to 6,
Tables 1 and 2, Supplementary Figures S1 to S14 and Supplementary Tables S1 to
S3. Three of them were at first believed impossible to publish, and each turned
out to be a question about inputs rather than about code. The caveat register is
computed, not curated. The author-countries figure needed four aggregates from
the per-paper country files, not the files. The journal-landscape figure counts
over one row per paper but never asks which paper, so those rows ship with the
study id removed and the order shuffled, which is what carried the linkage.

The stages before scoring are present as code and as their de-identified
outputs, but cannot be re-executed from a clean checkout, because they consume
the identifiable inputs this repository does not carry. They are here to be read
and audited rather than re-run.

One limit is worth stating plainly: **the sampling frame cannot be regenerated
even privately.** The query ran on 21 December 2023 and PubMed indexes
retrospectively, so re-running it returns a different frame and therefore a
different sample.

## The trap this repository had to work around

The pipeline contains rulings about particular studies rather than rules derived
from data. `code/lib/score_dataset_lib.R` names two per-protocol trials that
carry an unadjusted-confounding flag by adjudicator decision. **600 such
identifiers appear across the code.**

Copied unchanged beside de-identified data they match nothing and fail
**silently**: on the first build two studies quietly lost a validity flag and
the numbers drifted from the paper's, with no error raised. Every one is
therefore rewritten to its surrogate, and `verify_reproduces.py` runs the public
build and compares it row for row against the private one. That check is why
this repository can claim its numbers are the paper's numbers.

Code comments carried the same problem in a form no pattern could match. Three
papers were named by a trailing comment giving a PMC accession and a journal
title. The build now cuts every journal name, journal abbreviation and
institution name out of the code, driven by the study's own reference tables,
except where the same string is a value the data publishes on purpose.

## Tools

| | |
|---|---|
| `tools/build_public_repo.py` | builds `data/` and `code/` from the private originals under the three rules above |
| `tools/verify_no_identifiers.py` | gate 1: scans every publishable file for PMIDs, DOIs, ISSNs, PMC and trial ids, article URLs and reviewer names |
| `tools/verify_k_anonymity.py` | gate 2: measures how far the published attributes narrow the sample, and fails below k = 5 |
| `tools/verify_reproduces.py` | gate 3: proves the de-identified build reproduces the private scoring exactly |

All three exit non-zero on failure. **Run all three before every publish.**

⚠ The repository is rebuilt, never maintained in place. Editing a file inside it
is silently undone by the next build. Anything that must survive belongs in the
`PATCHES` dictionary in the builder.

## Availability of the full data

The complete dataset, including identifiers, is provided to the journal's
editors and peer reviewers as supplementary material for the purpose of review.
It is not distributed further.

## Citation and licence

Code is under the MIT licence (`LICENSE`). Data, documentation and figures are
under CC BY 4.0 (`LICENSE-DATA`). Citation details follow publication.
