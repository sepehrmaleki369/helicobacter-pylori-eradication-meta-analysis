# Predicting and explaining Helicobacter pylori eradication efficacy

A Bayesian hierarchical meta-analysis with machine-learning-assisted modelling.

This repository contains arm-level study data, Python analysis code, saved models, figures and supporting documentation for a systematic review of *Helicobacter pylori* eradication.

## Summary

The analytical dataset contains **140 treatment arms from 60 studies, covering 17,887 participants**. The analyses include random-effects meta-analysis, cluster-robust regression, Bayesian hierarchical logistic regression, supervised machine learning and feature-importance analysis.

## Repository contents

| Folder or file | Contents |
| --- | --- |
| `data/` | Extracted and processed arm-level datasets, data dictionary and study reference map |
| `scripts/` | Data processing and analysis scripts |
| `models/` | Saved models and prediction arrays |
| `figures/` | Analysis figures |
| `reports/` | Statistical and machine-learning outputs |
| `verification/` | Risk-of-bias assessment records |
| `docs/` | Technical and analysis documentation |
| `provenance/` | Data processing and verification records |
| `requirements.txt` | Python dependencies |
| `references.bib` | Study citations |

## Installation

Use Python 3.13.

```bash
git clone https://github.com/sepehrmaleki369/helicobacter-pylori-eradication-meta-analysis.git
cd helicobacter-pylori-eradication-meta-analysis
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Running the analyses

Use `scripts/run_analysis.py` to run an analysis with copies of the supplied data and model files. Each run requires a new output directory.

```bash
# Meta-analysis and cluster-robust regression
python scripts/run_analysis.py 07b_meta_analytic.py --work-dir outputs/meta-analysis

# Bayesian hierarchical analysis
python scripts/run_analysis.py 07c_bayesian_hierarchical.py --work-dir outputs/bayesian

# Machine-learning regression and classification
python scripts/run_analysis.py 07_model_building.py --work-dir outputs/machine-learning
```

Within each output directory, results are written to `project/report/`, `project/figures/` and `project/models/`, according to the selected script.

To prepare the inputs and check the selected script without fitting a model:

```bash
python scripts/run_analysis.py 07c_bayesian_hierarchical.py --work-dir outputs/check --prepare-only
```

The supplied `data/clean_dataset.csv` is the analysis input. Start with the analysis scripts below; regenerating it with `05_clean_and_features.py` replaces manual data edits.

## Analysis scripts

Run these through `scripts/run_analysis.py`, passing the script name and a new `--work-dir` as shown above. Each run starts with copies of the supplied datasets and saved models.

| Script | Analysis |
| --- | --- |
| `06_eda.py`, `06b_eda_extended.py` | Exploratory data analysis |
| `07_model_building.py` | Regression and classification models |
| `07b_meta_analytic.py` | Meta-analysis and cluster-robust regression |
| `07c_bayesian_hierarchical.py` | Bayesian hierarchical logistic regression |
| `07d_subgroup_sensitivity.py` | Subgroup and sensitivity analyses |
| `07e_feature_selection.py` | Feature selection |
| `07f_extended_models.py` | Extended regression models |
| `07g_classification_full.py` | Classification analyses |
| `08_feature_importance.py` | Permutation importance and SHAP analysis |
| `09_report.py` | Summary report and figures |
| `10_rob_clinician.py` | Risk-of-bias tables and figures |
| `10b_rob_sensitivity.py` | Risk-of-bias sensitivity analysis |

See [execution details](docs/REPRODUCIBILITY.md) for additional information about inputs and outputs.

## Data

[`data/clean_dataset.csv`](data/clean_dataset.csv) contains 140 rows and 76 fields. Each row represents a treatment arm, with regimen, dose, duration, sample size, eradication outcomes, participant characteristics and antimicrobial-resistance estimates.

- [Data dictionary](data/data_dictionary.csv): field definitions.
- [Study reference map](data/studies.csv): study identifiers and bibliographic details.
- [Bibliography](references.bib): references in BibTeX format.

Source article PDFs are obtained separately. The manuscript is maintained separately from this code and data repository.

## Citation

Author and repository citation information is available in [`CITATION.cff`](CITATION.cff).
