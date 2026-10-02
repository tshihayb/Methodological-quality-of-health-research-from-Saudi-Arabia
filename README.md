# Methodological quality of health research from Saudi Arabia: data and code

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23045997.svg)](https://doi.org/10.5281/zenodo.23045997)

This repository holds the data and analysis code for a study that assessed the methodological
quality of health research from Saudi Arabia.

## The study in brief

We drew a random sample of 385 primary human health studies published in 2022 with at least one
Saudi-affiliated author, from the 5,558 records that a PubMed search for such studies returned.
Each study was classified by its aim: to describe, to predict, or to estimate a cause and effect.
Two of thirteen epidemiologists, calibrated beforehand to an appraisal instrument built for the
purpose (ITQAN), then appraised each study independently; where they disagreed, two members of the
study team adjudicated. The 310 descriptive and causal studies were assessed for five sources of
error (random error, selection bias, measurement bias, confounding and missing data) and for how
their authors reported and acknowledged them. The instrument puts no bias items to predictive
studies.

The protocol and every version of the instrument are on the Open Science Framework:
https://osf.io/gfcv3. The findings are reported in the accompanying article (reference to follow on
publication).

## What is in this repository

| Folder or file | What it holds |
|---|---|
| `data/` | the de-identified data: every appraisal answer, the scores, and the tables the figures are drawn from |
| `code/` | the scripts that score the appraisals, run the analyses and draw every figure and table |
| `docs/instrument/` | the appraisal instrument as the reviewers used it |
| `CODEBOOK.md` | what each data column means, and the question in the instrument it comes from |
| `outputs/tables/` | fifteen intermediate tables that some analyses start from |
| `reproduce.py` | one command that rebuilds every figure and table |
| `MANIFEST_WITHHELD.md` | every file and script held back, with the reason |
| `tools/` | the scripts that build this public version and check it before release |

The files most people will want:

| File | One row per |
|---|---|
| `data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv` | study (385): its type, Saudi authorship and every appraisal answer |
| `data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv` | study and question: the same answers, with how each was settled |
| `data/scoring/07_30_2026_scored_study.csv` | scored study (310): its overall scores |
| `data/scoring/07_30_2026_scored_domain.csv` | scored study and appraisal domain |
| `data/scoring/07_30_2026_scored_items_long.csv` | scored study and question |

In every file, the column named `PMID` holds the study's code in this repository (`STUDY-0001` to
`STUDY-1031`), not its PubMed number.

## How the studies are kept anonymous

Every study assessed for bias had at least one methodological weakness. The findings concern a body
of research, not individual authors, so no study is named.

- Each study appears only as a code. The codes cover every paper that was screened, not only the
  385, so the list of screened papers does not reveal which were included. The key linking codes to
  papers is not published.
- Reviewers appear only as R1 to R13.
- Titles, authors, DOIs and PubMed numbers are removed. Journals, institutions and countries are
  named only where at least five studies share them; the rest are grouped as "Other".
- Combinations of characteristics could still narrow down some studies. Please do not attempt to
  identify individual studies or reviewers.
- Files and scripts that would identify studies or people are held back and listed in
  `MANIFEST_WITHHELD.md`. None is needed to reproduce the published results. The complete, unmasked
  data and code are provided to the journal's editors and peer reviewers for the purpose of review,
  and are not distributed further.

## Reproducing the results

You need Python 3.14 and R 4.5.2 (the versions used), with R's `Rscript` on the PATH, and these
packages:

- Python: pandas, matplotlib, openpyxl, python-docx, Pillow, pypdf (and fontTools, optional, which
  checks that every character in the Word tables exists in the font)
- R: dplyr, tidyr, tibble, purrr, stringr, forcats, readxl, ggplot2, ggnewscale, patchwork, cowplot,
  RColorBrewer

Then, from this folder:

```
python reproduce.py --list    # each step and what it makes
python reproduce.py           # rebuild everything
```

A full run takes about an hour and a half on a laptop, most of it one sensitivity analysis. The
figures and tables appear in `displays/`, named as in the article; each was checked against the
version in the manuscript.

The earlier stages (screening, assigning studies to reviewers, adjudication) cannot be rerun from
here, because they need the identifiable records; their results are included as data. The PubMed
search that defined the sampling frame ran on 21 December 2023 and cannot be repeated exactly,
because PubMed keeps adding records, so the drawn sample is provided as data.

## How to cite

If you use the data, the code or the appraisal instrument, please cite:

> Alshihayb TS, Aburas A, Alattas M, Aldakhil R, Aldalooj E, Aldossri M,
> Alkharashi T, Almeshal N, Alnasser LA, Alsugeir D, Asiri A, Gazzaz A,
> Merdad R, Samargandy S, Albogami Y. Methodological quality of health research
> from Saudi Arabia: data and code [dataset]. Zenodo; 2026.
> https://doi.org/10.5281/zenodo.23045997

This DOI always points to the latest version. Please also cite the article once it is published.

## Licence

Code: MIT (`LICENSE`). Data, documentation and figures: CC BY 4.0 (`LICENSE-DATA`); please credit
the reference above.

## Questions

Please open an issue on this repository, or contact Talal S. Alshihayb (tshihayb@bu.edu,
shihaybt@ksau-hs.edu.sa).
