# H. pylori eradication: analysis artifacts and code

**Review snapshot — 2 November 2026. This package is not a final reproducibility release.**
It preserves the historical 60-study analysis and its original GitHub figure set.
A data audit found three stale eradication-success counts and one stale proportion.
No data correction or model refit has been applied. See [data issues](docs/DATA_ISSUES.md).

## What is included

- Four original data CSVs, including `data/clean_dataset.csv`: 140 treatment arms,
  60 studies, 17,887 patients and 76 fields.
- All 72 saved model/prediction artifacts, unchanged from the working project.
- The 26 historical scripts, plus a portable isolated-run helper and cached-metric verifier.
- A 76-field [data dictionary](data/data_dictionary.csv), a 60-study
  [reference map](data/studies.csv), and `references.bib`.
- Clinician RoB ratings for all 60 studies and the original returned workbook.
  Ref 29 harmonisation still needs clinical confirmation.
- The original 223-entry manual-correction log, saved reports, audited cached
  prediction metrics, model card and a SHA-256 file manifest.
- The documented new PubMed query and retrieval log. Screening of that update
  is incomplete and its records are not part of the 60-study analysis.

All 60 included source-report PDFs are available in the local project.
Source PDFs and full extracted article texts are not redistributed. The manuscript
is maintained separately. Old model reports and figures can contain superseded
validation claims; retaining them is not verification of those claims.

## Check the packaged artifacts without fitting models

```bash
python3.13 -m pip install -r requirements.txt
python3.13 scripts/verify_cached_results.py --report /tmp/hpylori_release_check.json
```

The verifier checks file hashes, cohort identity, target/group order and 72
non-Bayesian cached metrics. **Exit code 2 is expected while the documented
four derived-field inconsistencies remain.** It does not change inputs or fit models.

## Prepare an isolated historical analysis run

```bash
python3.13 scripts/run_historical_analysis.py 07c_bayesian_hierarchical.py \
  --work-dir /tmp/hpylori_bayes_review --prepare-only
```

The helper copies the frozen inputs and replaces the old workstation path prefix
in memory. Omit `--prepare-only` to execute the selected historical script in a
new working directory. This retains the original statistical methods, including
known limitations; it does not fix them. See [reproducibility notes](docs/REPRODUCIBILITY.md).
Do not regenerate the published clean dataset with script 05: that would discard
manual corrections and can reintroduce excluded reports.

## What is not established

- Fresh end-to-end reproduction from source PDFs; exact saved Bayesian posterior
  draws and per-fold fitting logs were not located.
- Genuine held-out-study Bayesian validation, nested feature-selection validation
  or external clinical validation. BART prediction caches are failure fallbacks.
- Final eligibility, reconciled historical screening stages or complete screening
  of the newly documented PubMed update.
- A final published PROSPERO number or a publication DOI.

The missingness flags for age and compliance also describe an earlier data state.
The model card explains the prediction limitations. This is an exploratory
arm-level analysis, not a validated clinical decision tool.

## Licensing and citation

The earlier README declared MIT for code and CC-BY 4.0 for extracted data, but
no corresponding license files were present. [Licensing status](docs/LICENSING_STATUS.md)
records that gap; this preparation does not invent a new permission grant.
Use `CITATION.cff` for the supplied author names and repository address. The work
is an unpublished manuscript; no journal or DOI is fabricated.

## Repository and access

Code, extracted arm-level data and supporting documentation are hosted at
[https://github.com/sepehrmaleki369/helicobacter-pylori-eradication-meta-analysis](https://github.com/sepehrmaleki369/helicobacter-pylori-eradication-meta-analysis). This public repository is a new upload of existing project
material on 2 November 2026. The upload date records repository publication;
original study, analysis, search and registration timing remains separate.
See [re-upload notice](REUPLOAD_NOTICE.md). The code and frozen data were not
corrected or refitted for this upload.
