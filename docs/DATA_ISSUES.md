# Data consistency issues found on 2 November 2026

The frozen dataset is preserved. See
`provenance/proposed_derived_field_corrections.csv` for the exact candidate edits.

| Study / arm | Field | Stored | Candidate | Evidence |
| --- | --- | --- | --- | --- |
| Ref 36, Tai 2019, EACM-Quadruple | Successes_ITT | 104 | 105 | Table 2 directly reports 105/120 = 87.5%; the abstract has 86.7%. |
| Ref 36, Tai 2019, EACM-Quadruple | ITT_Prop | 0.867 | 0.875 | Same Table 2 and the already corrected ITT_Rate. |
| Ref 50, Yadollahi 2022, HDDT-Dual | Successes_ITT | 88 | 83 | Current N=103 and reported ITT=80.6%; 83 is inferred from rounded rate, not printed as a numerator. |
| Ref 50, Yadollahi 2022, Concomitant-Quad | Successes_ITT | 88 | 93 | Current N=114 and reported ITT=81.6%; 93 is inferred from rounded rate, not printed as a numerator. |

The manual log documents the Tai rate correction and the two Yadollahi denominator
corrections; those edits did not propagate to all derived fields. The Tai Table 2
text and Yadollahi pp174-175/Flow Chart 1 were checked. The latter chart was also
visually inspected. These are proposed corrections, not new applied extractions.
The success-count fields feed the binomial analyses. A source-confirmed correction
requires affected inference, sensitivity analyses, tables and figures to be rerun.
Changing a CSV alone would leave the stored model/results inconsistent.

Missingness flags also retain earlier values: age has 10 actual missing values
but 34 flagged rows; compliance has 16 actual missing values but 60 flagged rows.
The amoxicillin daily-dose indicator matches its 13 missing rows. Those flags
must not be presented as current missing-value counts. No flag was changed.

The legacy RCT label does not establish eligibility: Ref 81 used odd/even
allocation, and 13 retained arms conflict with the historical 40-per-arm rule.
Those previously identified eligibility questions and screening-stage counts
remain unresolved. This audit does not make new clinical eligibility decisions.
