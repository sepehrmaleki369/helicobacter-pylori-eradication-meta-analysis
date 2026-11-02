# Helicobacter pylori eradication meta-analysis

Data and Python code for a systematic review of *Helicobacter pylori* eradication, including Bayesian hierarchical meta-analysis and machine-learning analyses.

## Data

The main dataset, [`data/clean_dataset.csv`](data/clean_dataset.csv), contains 140 treatment arms from 60 studies, covering 17,887 participants and 76 fields.

- [Data dictionary](data/data_dictionary.csv): descriptions of the dataset fields.
- [Study reference map](data/studies.csv): included studies and their references.
- [Bibliography](references.bib): study citations in BibTeX format.

## Repository contents

| Folder | Contents |
| --- | --- |
| `data/` | Extracted and processed study data |
| `scripts/` | Data processing, statistical analysis and machine-learning code |
| `models/` | Saved models and prediction arrays |
| `figures/` | Analysis figures |
| `reports/` | Analysis outputs and reports |
| `verification/` | Risk-of-bias assessment records |
| `docs/` | Technical and analysis documentation |
| `provenance/` | Data processing and verification records |

## Setup

```bash
git clone https://github.com/sepehrmaleki369/helicobacter-pylori-eradication-meta-analysis.git
cd helicobacter-pylori-eradication-meta-analysis
python3.13 -m pip install -r requirements.txt
```

Analysis scripts are in `scripts/`. See the [execution instructions](docs/REPRODUCIBILITY.md) for preparing an isolated analysis run.

Author and repository citation information is available in [`CITATION.cff`](CITATION.cff).
