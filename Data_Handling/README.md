# 🔐 LimeSurvey Pseudonymization Script

## Overview

This script provides a **robust and reusable pipeline** for pseudonymizing LimeSurvey datasets.

It is designed for longitudinal research projects and ensures:
- removal of direct identifiers
- generation of persistent pseudonymous IDs (`pseudoID`)
- consistent blinding of study groups
- compatibility with evolving questionnaires (no script changes required)

---

## Key Features

- **Automatic pseudonymization**
  - removes personal identifiers (e.g., name, email, phone)
  - replaces them with a random `pseudoID`

- **Persistent mapping**
  - ensures the same participant always receives the same `pseudoID`
  - works across multiple time points (T1, T2, T3)

- **Study group blinding**
  - converts groups (e.g., IG / CG) into random numeric codes
  - prevents identification of intervention vs control group during analysis

- **Future-proof design**
  - automatically retains all new variables added to the dataset
  - no need to adapt the script when the questionnaire changes

---

## Input

- LimeSurvey export as:
  - `.csv`
  - `.xlsx`

- Must contain:
  - a unique participant identifier (default: `id`)

---

## Output

### 1. Analysis Dataset  
`survey_pseudonymized.csv`

- contains:
  - `pseudoID`
  - all survey variables
  - blinded `studyGroup`
- excludes:
  - all direct identifiers
  - original `id`

---

### 2. Sensitive Mapping File
`survey_mapping_sensitive.csv`

- contains:
  - original `id`
  - `pseudoID`
  - personal identifiers
  - original study group

**Important:**  
This file must be stored securely and must not be shared with analysts.

---

## How It Works

### 1. First Run (e.g., T1)
- generates:
  - new `pseudoID` for each participant
  - random numeric encoding of study groups
- creates:
  - mapping file (`survey_mapping_sensitive.csv`)

---

### 2. Subsequent Runs (T2, T3)
- loads existing mapping file
- reuses:
  - same `pseudoID`
  - same blinded study group
- adds:
  - new participants if present

---

## Configuration

Relevant parameters in the script:

```python
INPUT_FILE = "your_data.xlsx"
MAPPING_FILE = "survey_mapping_sensitive.csv"
PSEUDONYMIZED_OUTPUT = "survey_pseudonymized.csv"
ID_COLUMN = "id"
```

---

## Removed Identifiers
The script removes the following columns **if present:**

```python
DIRECT_IDENTIFIER_COLUMNS = [
    "Name",
    "Email",
    "email",
    "eMail",
    "eMailIG",
    "eMailKG",
    "PhoneSystem",
    "randomGroup",
]
```

---

## Study Group Blinding
Original values (e.g., IG, CG) are mapped to random numbers:

For example: 
**IG → 43  
CG → 57**

This mapping is:
  - stored in the sensitive file
  - consistent across all time points

---

## Usage

### 1. Prepare your data

- Export your survey data from LimeSurvey (or simulation)
- Supported formats:
  - `.csv`
  - `.xlsx`
- Place the file in the same directory as the script

---

### 2. Configure the script

Open `pseudonymize_limesurvey.py` and set the input file name (e.g., `your_data.xlsx`).

If needed, you can also adjust:
- the ID column (default: `id`)
- the study group column (default: `studyGroup`)

---

### 3. Run the script

Execute the script using Python from your terminal.

---

### 4. Outputs

After running the script, two files are created:

- `survey_pseudonymized.csv` → for analysis  
- `survey_mapping_sensitive.csv` → sensitive mapping

---

## Example Workflow (Longitudinal Study)

### Initial run (T1)

- Run the script on baseline data  
- A mapping file is created  
- PseudoIDs and blinded study groups are assigned  

---

### Follow-up runs (T2, T3)

- Replace the input file with the new dataset  
- Run the script again  
- Existing participants keep the same pseudoID  
- Study group blinding remains consistent  
- New participants are automatically added  

---

## Updating with New Data

The script is designed to handle updates seamlessly:

- New participants → automatically added to the mapping  
- Existing participants → matched via `id`  
- New variables → automatically included  

No changes to the script are required.

---

## Notes

- Always keep `survey_mapping_sensitive.csv` in the same directory  
  → it is required for consistent pseudonymization across time points  

- Do not delete or modify the mapping file between runs  

