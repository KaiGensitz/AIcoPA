
import os
import random
import string
from pathlib import Path

import pandas as pd

# =========================================================
# CONFIG section - adjust as needed for your specific survey export and requirements
# =========================================================

# Ensure paths work relative to the script location
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

# Input file (.csv or .xlsx)
INPUT_FILE = "results-survey581821 (5).csv"

# Persistent sensitive mapping file for T2 / T3 follow-up handling
MAPPING_FILE = "survey_mapping_sensitive.csv"

# Analysis output (pseudonymized)
PSEUDONYMIZED_OUTPUT = "survey_pseudonymized.csv"

# Stable key used to recognize the same participant in future exports
# NOTE: this only works stably across waves if this column itself is stable.
ID_COLUMN = "id"

# Columns to carry into the sensitive mapping and remove from analysis output
DIRECT_IDENTIFIER_COLUMNS = [
    "Name",
    "eMailIG",
    "eMailKG",
    "PhoneSystem",
    "randomGroup",
]

# Group column to blind in the analysis dataset
STUDYGROUP_COLUMN = "studyGroup"

# Derived / import-ready columns kept in the sensitive mapping
PSEUDOID_COLUMN = "pseudoID"
TOKEN_COLUMN = "token"
FIRSTNAME_COLUMN = "firstname"
LASTNAME_COLUMN = "lastname"
EMAIL_COLUMN = "email"
ATTRIBUTE_1_COLUMN = "attribute_1"   # studyGroup
ATTRIBUTE_2_COLUMN = "attribute_2"   # PhoneSystem
BLINDED_GROUP_COLUMN = "studyGroup_blind"


# =========================================================
# HELPERS
# =========================================================

def read_survey_file(path: str) -> pd.DataFrame:
    """Read CSV or XLSX automatically."""
    path_obj = Path(path)
    suffix = path_obj.suffix.lower()

    if suffix == ".csv":
        # Try common encodings / separators for LimeSurvey exports
        for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            for sep in [",", ";"]:
                try:
                    df = pd.read_csv(path_obj, encoding=encoding, sep=sep)
                    if df.shape[1] > 1:
                        return df
                except Exception:
                    pass
        raise ValueError("Could not read CSV file with common encoding/separator combinations.")

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path_obj)

    raise ValueError(f"Unsupported file type: {suffix}")


def random_code(length: int = 8) -> str:
    """Generate a random alphanumeric participant code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def normalize_series(s: pd.Series) -> pd.Series:
    """Normalize values for stable matching."""
    return s.astype(str).str.strip()


def clean_scalar(value) -> str:
    """Convert scalar values to stripped strings, mapping missing values to ''."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def pick_email(row: pd.Series) -> str:
    """Prefer eMailIG, then eMailKG, else empty string."""
    for col in ["eMailIG", "eMailKG"]:
        if col in row.index:
            value = clean_scalar(row[col])
            if value != "":
                return value
    return ""


def split_name(value) -> tuple[str, str]:
    """
    Split a full name into firstname and lastname.
    If only one token exists, store it as lastname and keep firstname blank.
    """
    full_name = clean_scalar(value)
    if full_name == "":
        return "", ""

    parts = full_name.split()
    if len(parts) == 1:
        return "", parts[0]

    firstname = parts[0]
    lastname = " ".join(parts[1:])
    return firstname, lastname


def get_group_blind_map(existing_groups):
    """Create a persistent blind mapping for study groups."""
    clean_groups = [g for g in existing_groups if pd.notna(g) and str(g).strip() != ""]
    unique_groups = sorted(set(str(g).strip() for g in clean_groups))

    blind_map = {}
    used_numbers = set()

    for group in unique_groups:
        n = random.randint(10, 99)
        while n in used_numbers:
            n = random.randint(10, 99)
        blind_map[group] = str(n)
        used_numbers.add(n)

    return blind_map


def ensure_mapping_columns(mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the sensitive mapping contains all expected columns."""
    required_columns = [
        ID_COLUMN,
        PSEUDOID_COLUMN,
        TOKEN_COLUMN,
        FIRSTNAME_COLUMN,
        LASTNAME_COLUMN,
        EMAIL_COLUMN,
        ATTRIBUTE_1_COLUMN,
        ATTRIBUTE_2_COLUMN,
        BLINDED_GROUP_COLUMN,
    ] + DIRECT_IDENTIFIER_COLUMNS + [STUDYGROUP_COLUMN]

    for col in required_columns:
        if col not in mapping_df.columns:
            mapping_df[col] = ""

    return mapping_df


def backfill_mapping_columns(mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Backfill derived import-related columns for existing rows."""
    mapping_df = mapping_df.copy()
    mapping_df = ensure_mapping_columns(mapping_df)

    # token defaults to pseudoID
    mapping_df[TOKEN_COLUMN] = mapping_df[TOKEN_COLUMN].replace("", pd.NA)
    mapping_df[TOKEN_COLUMN] = mapping_df[TOKEN_COLUMN].fillna(mapping_df[PSEUDOID_COLUMN])

    # firstname / lastname default from Name
    if "Name" in mapping_df.columns:
        missing_first = []
        missing_last = []
        for idx, row in mapping_df.iterrows():
            current_first = clean_scalar(row[FIRSTNAME_COLUMN])
            current_last = clean_scalar(row[LASTNAME_COLUMN])
            if current_first == "" and current_last == "":
                first, last = split_name(row["Name"])
            else:
                first, last = current_first, current_last
            missing_first.append(first)
            missing_last.append(last)
        mapping_df[FIRSTNAME_COLUMN] = missing_first
        mapping_df[LASTNAME_COLUMN] = missing_last

    # email defaults to eMailIG, otherwise eMailKG
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].replace("", pd.NA)
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna(mapping_df["eMailIG"])
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna(mapping_df["eMailKG"])
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna("")

    # attribute_1 defaults to original studyGroup
    mapping_df[ATTRIBUTE_1_COLUMN] = mapping_df[ATTRIBUTE_1_COLUMN].replace("", pd.NA)
    mapping_df[ATTRIBUTE_1_COLUMN] = mapping_df[ATTRIBUTE_1_COLUMN].fillna(mapping_df[STUDYGROUP_COLUMN])

    # attribute_2 defaults to PhoneSystem
    mapping_df[ATTRIBUTE_2_COLUMN] = mapping_df[ATTRIBUTE_2_COLUMN].replace("", pd.NA)
    mapping_df[ATTRIBUTE_2_COLUMN] = mapping_df[ATTRIBUTE_2_COLUMN].fillna(mapping_df["PhoneSystem"])

    # Normalize text-ish fields to clean strings
    for col in [
        ID_COLUMN,
        PSEUDOID_COLUMN,
        TOKEN_COLUMN,
        FIRSTNAME_COLUMN,
        LASTNAME_COLUMN,
        EMAIL_COLUMN,
        ATTRIBUTE_1_COLUMN,
        ATTRIBUTE_2_COLUMN,
        BLINDED_GROUP_COLUMN,
        "Name",
        "PhoneSystem",
        "eMailIG",
        "eMailKG",
        STUDYGROUP_COLUMN,
    ]:
        if col in mapping_df.columns:
            mapping_df[col] = mapping_df[col].apply(clean_scalar)

    return mapping_df


def build_or_update_mapping(df: pd.DataFrame, mapping_file: str) -> pd.DataFrame:
    """
    Build mapping on first run, or extend existing mapping on later runs.
    Same participant id -> same pseudoID and blinded studyGroup over time.
    """
    if ID_COLUMN not in df.columns:
        raise KeyError(f"Required column '{ID_COLUMN}' not found in input file.")

    current_ids = normalize_series(df[ID_COLUMN])

    # Load existing mapping if available
    if Path(mapping_file).exists():
        mapping_df = pd.read_csv(mapping_file, dtype=str)
        mapping_df = ensure_mapping_columns(mapping_df)
        mapping_df = backfill_mapping_columns(mapping_df)
    else:
        mapping_df = pd.DataFrame()

    if not mapping_df.empty and ID_COLUMN not in mapping_df.columns:
        raise KeyError(f"Existing mapping file is missing required column '{ID_COLUMN}'.")

    # Existing IDs / codes / group map
    existing_ids = set()
    existing_codes = set()
    existing_group_map = {}

    if not mapping_df.empty:
        mapping_df[ID_COLUMN] = normalize_series(mapping_df[ID_COLUMN])
        existing_ids = set(mapping_df[ID_COLUMN].tolist())

        if PSEUDOID_COLUMN in mapping_df.columns:
            existing_codes = set(mapping_df[PSEUDOID_COLUMN].dropna().astype(str).tolist())

        if STUDYGROUP_COLUMN in mapping_df.columns and BLINDED_GROUP_COLUMN in mapping_df.columns:
            for _, row in mapping_df[[STUDYGROUP_COLUMN, BLINDED_GROUP_COLUMN]].dropna().drop_duplicates().iterrows():
                original = clean_scalar(row[STUDYGROUP_COLUMN])
                blinded = clean_scalar(row[BLINDED_GROUP_COLUMN])
                if original != "" and blinded != "":
                    existing_group_map[original] = blinded

    # Determine group blind mapping
    if STUDYGROUP_COLUMN in df.columns:
        current_groups = normalize_series(df[STUDYGROUP_COLUMN])
        missing_groups = [
            g for g in current_groups.unique()
            if g not in existing_group_map and g != "" and g.lower() != "nan"
        ]

        if missing_groups:
            new_group_map = get_group_blind_map(missing_groups)
            used_vals = set(existing_group_map.values())
            for g, v in new_group_map.items():
                while str(v) in used_vals:
                    v = str(random.randint(10, 99))
                existing_group_map[g] = str(v)
                used_vals.add(str(v))

    # Build rows for new IDs only
    new_rows = []
    for idx, participant_id in enumerate(current_ids):
        if participant_id in existing_ids:
            continue

        code = random_code(8)
        while code in existing_codes:
            code = random_code(8)
        existing_codes.add(code)

        source_row = df.iloc[idx]
        firstname, lastname = split_name(source_row["Name"]) if "Name" in df.columns else ("", "")
        email = pick_email(source_row)
        phone = clean_scalar(source_row["PhoneSystem"]) if "PhoneSystem" in df.columns else ""

        row = {ID_COLUMN: participant_id, PSEUDOID_COLUMN: code}

        # Carry over direct identifiers if present (sensitive mapping only)
        for col in DIRECT_IDENTIFIER_COLUMNS:
            if col in df.columns:
                row[col] = clean_scalar(source_row[col])

        # Original and blinded study group
        orig_group = ""
        if STUDYGROUP_COLUMN in df.columns:
            orig_group = clean_scalar(source_row[STUDYGROUP_COLUMN])
            row[STUDYGROUP_COLUMN] = orig_group
            row[BLINDED_GROUP_COLUMN] = existing_group_map.get(orig_group, "")

        # Import-ready fields for LimeSurvey participant list
        row[TOKEN_COLUMN] = code
        row[FIRSTNAME_COLUMN] = firstname
        row[LASTNAME_COLUMN] = lastname
        row[EMAIL_COLUMN] = email
        row[ATTRIBUTE_1_COLUMN] = orig_group
        row[ATTRIBUTE_2_COLUMN] = phone

        new_rows.append(row)

    new_rows_df = pd.DataFrame(new_rows)
    new_rows_df = ensure_mapping_columns(new_rows_df) if not new_rows_df.empty else pd.DataFrame(columns=ensure_mapping_columns(pd.DataFrame()).columns)

    if mapping_df.empty:
        mapping_df = new_rows_df.copy()
    elif not new_rows_df.empty:
        mapping_df = pd.concat([mapping_df, new_rows_df], ignore_index=True)

    mapping_df = ensure_mapping_columns(mapping_df)
    mapping_df = backfill_mapping_columns(mapping_df)

    return mapping_df


def pseudonymize_dataset(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis dataset with pseudoID and blinded studyGroup."""
    df = df.copy()

    df[ID_COLUMN] = normalize_series(df[ID_COLUMN])
    mapping_df = mapping_df.copy()
    mapping_df[ID_COLUMN] = normalize_series(mapping_df[ID_COLUMN])

    merge_cols = [ID_COLUMN, PSEUDOID_COLUMN]
    if BLINDED_GROUP_COLUMN in mapping_df.columns:
        merge_cols.append(BLINDED_GROUP_COLUMN)

    df = df.merge(mapping_df[merge_cols], on=ID_COLUMN, how="left")

    # Replace studyGroup with blinded version
    if STUDYGROUP_COLUMN in df.columns and BLINDED_GROUP_COLUMN in df.columns:
        df[STUDYGROUP_COLUMN] = df[BLINDED_GROUP_COLUMN]
        df = df.drop(columns=[BLINDED_GROUP_COLUMN])

    # Remove direct identifiers from analysis file
    cols_to_drop = [col for col in DIRECT_IDENTIFIER_COLUMNS if col in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Drop original id from the analysis dataset to strengthen pseudonymization
    if ID_COLUMN in df.columns:
        df = df.drop(columns=[ID_COLUMN])

    # Put pseudoID first
    cols = df.columns.tolist()
    if PSEUDOID_COLUMN in cols:
        cols = [PSEUDOID_COLUMN] + [c for c in cols if c != PSEUDOID_COLUMN]
        df = df[cols]

    return df


# =========================================================
# MAIN
# =========================================================

def main():
    random.seed(42)  # reproducible code/group creation for new participants

    df = read_survey_file(INPUT_FILE)

    mapping_df = build_or_update_mapping(df, MAPPING_FILE)
    analysis_df = pseudonymize_dataset(df, mapping_df)

    # Save outputs
    mapping_df.to_csv(MAPPING_FILE, index=False)
    analysis_df.to_csv(PSEUDONYMIZED_OUTPUT, index=False)

    print("Done.")
    print(f"Input rows: {len(df)}")
    print(f"Mapping file updated: {MAPPING_FILE}")
    print(f"Analysis file written: {PSEUDONYMIZED_OUTPUT}")
    print("Mapping file contains import-ready LimeSurvey columns:")
    print(f"- {FIRSTNAME_COLUMN}")
    print(f"- {LASTNAME_COLUMN}")
    print(f"- {EMAIL_COLUMN}")
    print(f"- {TOKEN_COLUMN}")
    print(f"- {ATTRIBUTE_1_COLUMN} (studyGroup)")
    print(f"- {ATTRIBUTE_2_COLUMN} (PhoneSystem)")


if __name__ == "__main__":
    main()
