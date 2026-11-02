# Figure captions (manuscript draft)

## Main figures

### Figure 1. Study selection and analytic pipeline (PRISMA)
PRISMA-style flow diagram showing the identification, screening, eligibility assessment, and inclusion of studies. From ~96 records identified through PubMed across five search queries, 92 were screened after deduplication, 78 underwent full-text review, and 63 studies (146 arms) met eligibility criteria. After exclusion of arms without intention-to-treat outcome data and protocol/microbiome studies, 144 arms from 62 unique studies (18,468 total patients) entered the analysis. The bottom row summarises the analytical layers applied to the final cohort: weighted ElasticNet machine learning, binomial GLM with cluster-robust standard errors, Bayesian hierarchical regression with random study intercept, and subgroup/sensitivity/heterogeneity analyses.

### Figure 2. Bayesian hierarchical posterior effect sizes
Posterior odds ratios (95% highest density intervals) from a Bayesian binomial logistic GLM with random intercept by study (n=144 arms, 62 studies). Fixed effects: vonoprazan, tegoprazan, regimen structure (dual/quadruple/bismuth/clarithromycin), duration, antibiotic resistance rates (CLR, MTZ, AMX), region (East Asia), age, compliance, susceptibility-guided flag, and CLR×CLR-resistance interaction. Effects with 95% HDI excluding OR = 1.0 are highlighted (purple). Study-level intercept SD: σ_study = 0.51 [0.40, 0.64]. MCMC: 4 chains × 1500 draws (1000 tune), nutpie Rust sampler; max r̂ = 1.010, min ESS = 611.

### Figure 3. Subgroup forest plot — vonoprazan effect by stratum
Stratified vonoprazan-vs-comparator odds ratios estimated from the binomial GLM with cluster-robust standard errors (cluster = study Ref). Strata: all arms (n=142), East Asia only, non-East Asia, high CLR resistance region (≥30%), low CLR resistance region (<30%), multicenter vs single-centre. Vertical red dashed line = OR = 1 (no effect). The vonoprazan effect is concentrated in high-resistance environments (OR 1.90 [1.47, 2.44]) and is absent in low-CLR settings (OR 0.98 [0.64, 1.51]). The interaction term Vonoprazan × High_CLR_Region had OR = 1.92 [1.29, 2.87], p = 0.0013.

### Figure 4. Calibration of marginal predictions across model classes
Decile-binned calibration plot comparing marginalised predictions from the Bayesian hierarchical model (purple) against Tier-1 ElasticNet leave-one-study-out predictions (blue). Marginal predictions integrate over the study random intercept and represent the model's expectation for a new study not present in the training set. Bayesian hierarchical achieves calibration slope = 1.016 (target = 1.0) and intercept = −0.029 (target = 0); Brier score = 0.0084 on proportion scale. This indicates the model is well-calibrated for out-of-sample studies — a clinically meaningful property even when raw R² is modest.

### Figure 5. SHAP attributions for the final predictive model
SHAP (SHapley Additive exPlanations) summary plot for the headline predictive model: Recursive Feature Elimination top-10 features + Random Forest, sample-size-weighted (n=144). Features are ranked by mean |SHAP|. The dominant driver is the pharmacological-mismatch interaction term CLR_use × CLR_resistance (clarithromycin used in a high-resistance environment), followed by background resistance rates and the standard-PPI vs P-CAB contrast (Is_Standard_PPI). The signs are biologically interpretable: mismatched drug-resistance combinations and standard PPI use reduce predicted eradication, while quadruple therapy and high background resistance (in the presence of P-CABs that overcome it) raise it.

---

## Supplementary figures

### Supplementary Figure S1. Funnel plot and Egger test
Funnel plot of vonoprazan log odds ratios versus inverse standard error across the 18 paired vonoprazan-vs-comparator studies. Egger's regression intercept = 0.139 (p = 0.88), indicating **no detectable small-study or publication bias**.

### Supplementary Figure S2. Sensitivity analyses
Robustness of the vonoprazan odds ratio under sequential exclusions: quality-flagged arms, susceptibility-guided arms, regional-estimate resistance arms, and small (N_ITT<50) arms. The effect remains in the range OR ≈ 1.6–1.7 across all scenarios, indicating no single subset drives the headline finding.

### Supplementary Figure S3. Predictive model comparison
LOSO R² (left) and LOO R² (right) across nine model families: Bayesian hierarchical (marginal), Gaussian Process, RandomForest, ElasticNet, LightGBM, sklearn GradientBoost, BART, and XGBoost. Bayesian hierarchical dominates the LOSO honest-generalisation comparison; the gap between LOO and LOSO across models reflects within-study correlation that only the random-intercept-by-study structure captures.

### Supplementary Figure S4. Pearson correlation matrix of numeric predictors
Correlation matrix of all numeric candidate features and outcomes (ITT_Rate, PP_Rate). Used during feature engineering to detect collinearity (e.g., the Is_Vonoprazan / Is_Standard_PPI inverse relationship that drove RFE's substitution).

### Overview dashboard
Six-panel summary figure combining: (A) regimen breakdown, (B) ITT rate by treatment type, (C) P-CAB vs standard PPI, (D) SHAP feature importance, (E) cross-validated model performance, (F) regional resistance profile. Used for at-a-glance project summary and presentations.
