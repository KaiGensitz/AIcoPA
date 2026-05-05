# LimeSurvey Pseudonymization Script

## Overview

This script provides a robust and reusable pipeline for pseudonymizing LimeSurvey datasets in longitudinal studies (T1–T3).

It ensures:
- removal of direct identifiers  
- generation of persistent pseudonymous IDs (pseudoID)  
- generation of separate access tokens (token) for follow-up surveys  
- consistent blinding of study groups  
- compatibility with evolving questionnaires
- automated attention check handling (T2/T3)

---

## Key Features

### Automatic pseudonymization
- removes personal identifiers (e.g., name, email, phone)  
- replaces them with a random pseudoID (analysis identifier)  

---

### Persistent participant tracking
- participants are matched across time points using:  
  - Name (primary identifier)  
  - E-Mail (fallback if duplicate names exist)  
- ensures:  
  - same participant → same pseudoID across T1–T3  

---

### Separate token generation
- generates a random token independent of pseudoID  
- used for:  
  - LimeSurvey Participant List (T2, T3)  
- ensures:  
  - token is always different from pseudoID  

---

### LimeSurvey-compatible participant export
The sensitive mapping file includes:
- firstname  
- lastname  
- email  
- token  
- attribute_1 (studyGroup)  
- attribute_2 (PhoneSystem)
- attribute_3 (Invitation Date -> Submitdate T1/T2 + 12 Weeks)
- attribute_4 (Reminder1 Date -> Invite + 3 Days)
- attribute_5 (Reminder2 Date -> Invite + 7 Days)
- attribute_6 (Reminder3 Date -> Invite + 11 Days)

→ can be directly used for T2/T3 participant import  

---

### Study group blinding
- converts groups (e.g., IG / CG) into random numeric codes  
- prevents identification during analysis  

---

### Attention check handling (T2/T3)
- evaluates predefined attention check items
- correct = response starting with "3"
- at least one correct answer required

If not passed: all survey variables are set to NA and a 
separate report file is created listing all failed cases

---

### Future-proof design
- automatically retains all new variables  
- no script changes required when questionnaire evolves  

---

## Input

- LimeSurvey export as:
  - CSV  
  - XLSX  

- Must contain:
  - Name (required)  

- Optional:
  - eMailIG / eMailKG (used as fallback identifier)  

---

## Output

### 1. Analysis Dataset  
survey_pseudonymized.csv  

Contains:
- pseudoID  
- all survey variables  
- blinded studyGroup
- attention check indicators

Excludes:
- all direct identifiers  
- matching keys (name/email)  
- original id  

---

### 2. Sensitive Mapping File  
survey_mapping_sensitive.csv  

Contains:
- internal matching key (match_key)  
- pseudoID (analysis identifier)  
- token (LimeSurvey access code)  
- firstname, lastname, email  
- attribute_1 (studyGroup)  
- attribute_2 (PhoneSystem)
- attribute_3 (Invitation Date -> Submitdate T1/T2 + 12 Weeks)
- attribute_4 (Reminder1 Date -> Invite + 3 Days)
- attribute_5 (Reminder2 Date -> Invite + 7 Days)
- attribute_6 (Reminder3 Date -> Invite + 11 Days)
- original identifiers  

Important:  
This file must be stored securely and never shared with analysts.  

---
### 3. Attention Check Report
attention_check_failures.csv

Contains:
- pseudoID
- studyGroup
- timePoint
- number of passed attention checks
- failure flag
- raw attention check responses

---

## How It Works

### First Run (T1)
- generates:
  - pseudoID (random)  
  - token (separate random code)  
  - blinded study group  
- builds:
  - matching key (Name + optional Email)  
- creates:
  - mapping file  

---

### Subsequent Runs (T2, T3)
- loads existing mapping file  
- matches participants via:
  - Name  
  - Email (if duplicates exist)  
- reuses:
  - same pseudoID  
  - same token  
  - same blinded study group  
- adds:
  - new participants automatically  

---

## Participant Matching Logic

Participants are matched using:

1. Unique Name  
   name::max muster  

2. Duplicate Name → fallback to email  
   name_email::max muster::max@mail.com  

If:
- same name AND  
- no email available  

→ the script stops with an error  

---

## Configuration

Relevant parameters in the script:
- input file name  
- mapping file name  
- output file name
- attention check settings (true/false, columns, correct value, threshold)

---

## Removed Identifiers

The following columns are removed if present:
- Name  
- eMailIG  
- eMailKG  
- PhoneSystem  
- randomGroup  

---

## Study Group Blinding

Example:
- IG → 43  
- CG → 57  

- mapping stored in sensitive file  
- consistent across all waves  

---

## LimeSurvey Integration

The mapping file can be used directly as participant import file:

- firstname → participant name  
- lastname → participant name  
- email → contact  
- token → access code  
- attribute_1 → studyGroup  
- attribute_2 → PhoneSystem  

---

## Usage

### 1. Prepare data
- export from LimeSurvey  
- place file in script directory  

---

### 2. Configure script
- set input file  
- adjust column names if needed  

---

### 3. Run script
- execute with Python  

---

### 4. Outputs
- survey_pseudonymized.csv → analysis  
- survey_mapping_sensitive.csv → sensitive mapping  

---

## Updating with New Data

- new participants → added automatically  
- existing participants → matched via name/email  
- new variables → included automatically  

---

## Important Notes

- keep survey_mapping_sensitive.csv unchanged between runs  
- do not share the mapping file
- attention check filtering only applies if enabled in the script
- matching depends on:
  - consistent spelling of names  
  - availability of email for duplicates  
