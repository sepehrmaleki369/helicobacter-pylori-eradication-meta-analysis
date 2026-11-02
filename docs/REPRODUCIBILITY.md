# Reproducibility boundaries and execution

The frozen input is `data/clean_dataset.csv`, not a regenerated output of script 05.
The repository was checked against the working project: all four original data
CSVs and all 72 saved model artifacts are byte-identical. The raw upstream CSVs
represent historical construction stages, not interchangeable final cohorts.

Twenty-two historical scripts contain 55 absolute workstation-path literals.
`scripts/run_historical_analysis.py` provides a portable entry point without
changing the historical scripts. It copies data/models/RoB inputs into a new
working directory using the original project subdirectory layout, then substitutes
only the old root prefix in the code in memory. Published inputs stay untouched.
The `--prepare-only` mode checks compilation and prepares input copies without
sampling or fitting. This mode has been tested; fresh inference has not been run.

Original PDF/text extraction needs lawfully obtained source reports. They are
not in this package. The data dictionary and `data/studies.csv` identify reports.
The supplied clinician workbook is copied into an isolated run when needed.
Manuscript-export scripts require the separately maintained LaTeX manuscript and
are not supported by the analysis launcher.

The original reports may contain invalid Bayesian LOSO labels, a classification
unit error, globally selected RFE performance, and BART fallback results. The
cached-metric audit in `reports/prediction_reporting_2026-11-02.json` and the
model card document these limits. `verify_cached_results.py` recomputes 72
non-Bayesian metrics from the existing six pairs of prediction arrays. It does
not reproduce or independently validate the historical fitting runs.

Full Bayesian posterior draws and per-fold identity/convergence logs were not
found. Saved prediction arrays and the text report do not replace those objects.
The data audit found stale derived fields: correcting them requires verification
and refitting affected analyses. Historical missingness flags also need a decision.
Do not claim that the restored manuscript's statistics have all been reproduced.
