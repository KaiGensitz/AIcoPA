# AIcoPA Simulation Pipeline

Synthetic data generation pipeline for a longitudinal cross-over physical activity intervention study.


---

## Documentation overview

Simulation execution and setup: simulation_run_procedure.md  
Mapping to survey format (LimeSurvey): mapping_procedure.md  
Validation checks and expected outputs: simulation_validation_checks.md  
Technical implementation details: simulation_architecture_reference.md  
Study design and assumptions: simulation_study_protocol.md  
Function-level explanations (UID format): function_explanations_uid.md  

---

## Workflow summary diagram

Simulation → Mapping → Validation

---

### Requirements
- R (>= 4.2)
- Packages:
install.packages(c("dplyr", "tidyr", "MASS", "readxl", "openxlsx", "lme4"))

## Quick start

Run full pipeline in order:

1. Simulation  

    source("simulation_script.R")

    Output file: AIcoPA_simulation_v2_5_itemdata.csv

2. Mapping (LimeSurvey format)  

    source("mapping_script.R")

    Output file: AIcoPA_simulation_v2_5_export_like_template.xlsx

3. Validation  

    source("simulation_check.R")

---

## Study design

Sample size: N = 200  
Time points: T1, T2, T3  
Design: cross-over intervention  

### Intervention logic

- IG: intervention at T1 → effect at T2  
- CG: intervention at T2 → effect at T3  
- Carryover effect for IG at T3  

This allows modeling of time-dependent treatment effects and group-by-time interactions.

---

## Simulation components

### Latent constructs

- habit  
- intention  
- attitude  
- social norms (injunctive & descriptive)  
- perceived behavioral control  
- autonomous motivation  
- planning  
- self-control  

### Outcomes

- steps per day  
- weekly MET minutes  
- survey-based physical activity:  
  - days/week  
  - minutes/session  

### Additional components

- sociodemographic effects (age, gender, income, prior app use)  
- TAM variables (only during intervention phases)  
- missingness:  
  - ~10% dropout across time points  

---

## Person-level structure

Latent baseline traits are generated using a multivariate normal distribution.

- Stable individual differences across participants  
- Correlation structure based on theory/meta-analytic assumptions  
- Ensures realistic covariance between psychological constructs  

---

## Mapping (LimeSurvey compatibility)

The mapping step transforms simulated data into a LimeSurvey-compatible format:

- Wide format with item naming conventions  
- Structure matches survey export template  
- Includes:
  - timePoint  
  - studyGroup  
  - item-level responses  
  - metadata fields  

Output file: AIcoPA_simulation_v2_5_export_like_template.xlsx

---

## Validation

Validation script checks:

- Data completeness  
- Distribution plausibility  
- Missingness patterns (~10%)  
- Correct group × time structure  
- Consistency of carryover effects  

---

## Key outputs

Simulation:

- AIcoPA_simulation_v2_5_itemdata.csv  

Mapping:

- AIcoPA_simulation_v2_5_export_like_template.xlsx  

Validation:

- Console output with diagnostics  
- Optional summary statistics  

---

## High-priority failure checks

- Simulation script not executed before mapping  
- Missing variables in mapping template  
- Inconsistent timePoint or studyGroup coding  
- Unrealistic distributions (e.g., no variance)  
- Missing output files after each stage  

---

## Notes

- Run scripts strictly in order:  
  simulation → mapping → validation  

- Always use latest output files for downstream steps  

- Changes to constructs or items require updates in:
  - simulation_script.R  
  - mapping_script.R  

- Covariates and latent structures are explicitly modeled and should be kept consistent across time points  

