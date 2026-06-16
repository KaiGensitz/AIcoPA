# Data handling and LimeSurvey pseudonymization

> **Synthetic demo data only:** any example CSV files committed under
> `Data_Handling/examples/synthetic/` or `Data_Handling/tests/fixtures/` are
> synthetic demo/test data. Legacy synthetic/template survey artifacts that were
> previously in the repository root have been moved to
> `Data_Handling/examples/synthetic/legacy_or_templates/`. These files must never
> be replaced with real participant data. Real LimeSurvey exports, mapping files,
> participant imports, pseudonymized outputs, and QC reports must be processed
> outside the repository or in ignored secure folders.

This folder contains a **pseudonymization workflow** for an active longitudinal
T1/T2/T3 LimeSurvey study. It is not a full anonymization or open-data release
pipeline. The sensitive mapping/contact workflow is intentionally retained while
follow-up invitations, reminders, withdrawals, and longitudinal linkage are
needed during the active study phase.

## Pseudonymization is not anonymization

Pseudonymization replaces direct identifiers with a stable `pseudoID` so that
T1/T2/T3 records can be linked for analysis. Because a sensitive mapping file
can reconnect `pseudoID` and survey tokens to names/emails, pseudonymized data
are still personal data. The default `processed/` analysis outputs are therefore
**not anonymous** and must be protected accordingly.

A future anonymized release pipeline should be separate from this workflow and
should remove or transform linkage IDs, exact dates, rare quasi-identifiers,
technical metadata, and free text according to a documented risk assessment.

## Sensitive and generated data

The following files are sensitive in real study use and are ignored by default:

- raw LimeSurvey exports;
- `sensitive/` mapping/contact/token files;
- participant import files for LimeSurvey invitations/reminders;
- `processed/` pseudonymized analysis outputs;
- `qc/` participant-level quality-control reports.

Mapping, contact, and token files must be stored separately from analysis data,
preferably outside this repository on encrypted institutional storage with
restricted access. Tokens are operational identifiers and are never included in
the default pseudonymized analysis output.

## Indirect identifiers and default exclusions

Exact dates, timestamps, LimeSurvey technical metadata, referrer URLs, response
`*Time` columns, and free-text variables may be indirect identifiers. The script
therefore excludes them from default analysis output unless explicitly allowed.
Unknown columns generate a review warning in demo mode and fail production mode by default.

`config/variable_classification.json` is a **minimal demo/template config**,
not a complete real-study T1/T2/T3 variable dictionary. Before processing real
exports, all real LimeSurvey analysis variables must be reviewed and added to
the config. Otherwise production mode will fail on unknown columns by default,
or reviewed unknown columns will be excluded from the default analysis output.

Variable handling is controlled by `config/variable_classification.json`:

- `analysis_allowlist`: variables allowed into default analysis output;
- `direct_identifier_columns`: direct/contact/linkage fields that must not enter
  analysis output;
- `technical_metadata_columns`: date/time/referrer fields excluded by default;
- `free_text_columns`: open-text fields excluded by default.

## Folder structure

```text
Data_Handling/
  config/                 # synthetic-safe configuration templates
  scripts/                # pseudonymization code
  examples/synthetic/     # committed synthetic examples only
  tests/                  # synthetic tests and fixtures
  sensitive/              # ignored mapping/contact/token outputs
  processed/              # ignored pseudonymized analysis outputs
  qc/                     # ignored QC reports
```

## Running the pseudonymization script

Example demo run with synthetic data:

```bash
python3 Data_Handling/scripts/pseudonymize_limesurvey.py \
  --mode demo \
  --wave T1 \
  --input Data_Handling/examples/synthetic/raw/synthetic_results-survey_T1.csv \
  --mapping Data_Handling/sensitive/survey_mapping_sensitive.csv \
  --participants-output Data_Handling/sensitive/survey_participants_import.csv \
  --analysis-output Data_Handling/processed/survey_pseudonymized_T1.csv \
  --qc-output Data_Handling/qc/attention_check_failures_T1.csv
```

For real data, use `--mode production` and secure non-repository paths where
possible. Production mode fails on unknown/unclassified columns by default; only
use `--allow-unknown-columns` after documenting that the excluded variables have
been reviewed. `--mode demo` is restricted to synthetic/test paths because it
uses deterministic IDs/tokens.

Risk flags:

- `--allow-technical-metadata` can reintroduce exact dates, timestamps, referrer
  URLs, and LimeSurvey timing metadata. Use it only after variable-level review.
- `--allow-free-text` can reintroduce participant-provided content that may
  contain names, locations, rare events, or other identifying details. Use it
  only after variable-level review and a documented handling decision.

## Attention checks

Attention-check columns and the default threshold are configured in
`config/attention_checks.json`. A 2/3 rule is supported by configuring three
columns and `"min_correct": 2`, or by passing `--attention-min-correct 2` for a
specific run. The script does not assume a 2/3 rule unless configured.
