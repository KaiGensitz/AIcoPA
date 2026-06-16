# Codex task: update AIcoPA real-study variable classification without original uploads

The original files could not be uploaded to Codex. Instead, use the extracted metadata files in this folder. They contain only codebook/LimeSurvey metadata and no participant values.

Files to use:
- codebook_variables_extracted.csv: variables from Codebook_V3.0.xlsx
- lss_questions_extracted.csv: questions parsed from limesurvey_survey_581821 (12).lss
- lss_likely_export_columns.csv: likely LimeSurvey export column names, including array notation like Habit[Habit1]
- codebook_lss_crosswalk.csv: proposed crosswalk and initial classification per export column
- lss_missing_from_codebook.csv: .lss variables that did not match the codebook
- codebook_not_found_in_lss.csv: codebook variables not found in the current .lss
- name_diff_crosswalk.csv: places where codebook variable name differs from likely export column name
- classification_records_from_codebook_lss.json: JSON version of the proposed records

Task:
Update and critically review Data_Handling/config/variable_classification_real_study_draft.json so that it works with actual LimeSurvey export column names, not only conceptual codebook names.

Important constraints:
- Do not infer or use participant values.
- Do not modify the pseudonymization script unless strictly necessary.
- Do not add a full anonymized release pipeline.
- Keep the file as a draft unless a human has reviewed all manual_review_needed=true variables.

Required behavior:
- Use limesurvey_export_name from the crosswalk as the operative column name in the classification.
- For array questions, use exact export-style names, for example Habit[Habit1], KIM[IntVer1], KIM[ACheck2], ZiMo[discat1], TAM[WA1], AlltagAbl[AufWa], EntfernPOI[BStel], UmgebTyp[Ver].
- Always drop direct identifiers/contact/linkage fields from default analysis: id, token, Name, firstname, lastname, email, eMailIG, eMailValidIG, eMailKG, eMailValidKG, match_key, name_key, email_key, refurl, SystemLink.
- Drop technical metadata by default: submitdate, startdate, datestamp, interviewtime and all *Time columns.
- Drop free text by default unless manually reviewed/anonymized.
- Treat Geb as quasi_identifier and recommend derived age/age group instead of raw birth date.
- Treat routine/context variables such as AlltagAbl[*], EntfernPOI[*], UmgebTyp[*], BeschaeftProz, UrlaubWochen, StressWochen as privacy-risky and manual-review variables, even if analytically relevant for ABM/persona context.
- Treat utmsource, utmmedium, utmcampaign, utmcontent as recruitment_metadata and exclude unless campaign analyses are planned.
- Use true attention check export names: ACheck1[ACheck1], KIM[ACheck2], ZiMo[ACheck3].
- Treat studyGroup as analysis-relevant only in blinded/recoded form; randomGroup remains operational/randomization metadata.
- Treat PAFlag, PASubgroup, METtotal, and AttentionCheckFlag as exclusion/QC or derived analysis variables and flag for manual review.
- Treat PhoneSystem as contact/operational or quasi_identifier and not default analysis unless justified.

Return/commit:
- Updated Data_Handling/config/variable_classification_real_study_draft.json
- Optional short supporting README note if needed
- A summary listing: variables in .lss missing from codebook; variables in codebook missing from .lss; variables where names differ; variables dropped but likely analytically needed; variables kept but privacy-risky.
