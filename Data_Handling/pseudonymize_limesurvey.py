import os
import random
import string
from pathlib import Path

import pandas as pd

# =========================================================
# CONFIG
# =========================================================

# Ensure paths work relative to the script location
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

# Input file (.csv or .xlsx)
INPUT_FILE = "AIcoPA_simulation_v3_export_like_template.xlsx"

# Persistent mapping file for T2 and T3
MAPPING_FILE = "survey_mapping_sensitive.csv"

# Analysis output
PSEUDONYMIZED_OUTPUT = "survey_pseudonymized.csv"

# Stable key used to recognize the same participant in future exports
ID_COLUMN = "id"

# Columns to remove from the analysis dataset if present
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

# Group column to blind if present
STUDYGROUP_COLUMN = "studyGroup"


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


def get_group_blind_map(existing_groups):
    """
    Create a persistent blind mapping for study groups.
    """
    clean_groups = [g for g in existing_groups if pd.notna(g) and str(g).strip() != ""]
    unique_groups = sorted(set(str(g).strip() for g in clean_groups))

    blind_map = {}
    used_numbers = set()

    for group in unique_groups:
        n = random.randint(10, 99)
        while n in used_numbers:
            n = random.randint(10, 99)
        blind_map[group] = n
        used_numbers.add(n)

    return blind_map


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
    else:
        mapping_df = pd.DataFrame()

    if not mapping_df.empty and ID_COLUMN not in mapping_df.columns:
        raise KeyError(f"Existing mapping file is missing required column '{ID_COLUMN}'.")

    # Existing IDs / codes
    existing_ids = set()
    existing_codes = set()
    existing_group_map = {}

    if not mapping_df.empty:
        mapping_df[ID_COLUMN] = normalize_series(mapping_df[ID_COLUMN])
        existing_ids = set(mapping_df[ID_COLUMN].tolist())

        if "pseudoID" in mapping_df.columns:
            existing_codes = set(mapping_df["pseudoID"].dropna().astype(str).tolist())

        if STUDYGROUP_COLUMN in mapping_df.columns and "studyGroup_blind" in mapping_df.columns:
            for _, row in mapping_df[[STUDYGROUP_COLUMN, "studyGroup_blind"]].dropna().drop_duplicates().iterrows():
                existing_group_map[str(row[STUDYGROUP_COLUMN]).strip()] = str(row["studyGroup_blind"]).strip()

    # Determine group blind mapping
    if STUDYGROUP_COLUMN in df.columns:
        current_groups = normalize_series(df[STUDYGROUP_COLUMN])
        missing_groups = [g for g in current_groups.unique() if g not in existing_group_map and g != "" and g.lower() != "nan"]

        if missing_groups:
            new_group_map = get_group_blind_map(missing_groups)
            used_vals = set(existing_group_map.values())
            for g, v in new_group_map.items():
                while str(v) in used_vals:
                    v = random.randint(10, 99)
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

        row = {ID_COLUMN: participant_id, "pseudoID": code}

        # Carry over direct identifiers if present
        for col in DIRECT_IDENTIFIER_COLUMNS:
            if col in df.columns:
                row[col] = df.iloc[idx][col]

        # Original and blinded study group
        if STUDYGROUP_COLUMN in df.columns:
            orig_group = str(df.iloc[idx][STUDYGROUP_COLUMN]).strip()
            row[STUDYGROUP_COLUMN] = orig_group
            row["studyGroup_blind"] = existing_group_map.get(orig_group, "")

        new_rows.append(row)

    new_rows_df = pd.DataFrame(new_rows)

    if mapping_df.empty:
        mapping_df = new_rows_df
    elif not new_rows_df.empty:
        mapping_df = pd.concat([mapping_df, new_rows_df], ignore_index=True)

    return mapping_df


def pseudonymize_dataset(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis dataset with pseudoID and blinded studyGroup."""
    df = df.copy()

    df[ID_COLUMN] = normalize_series(df[ID_COLUMN])
    mapping_df = mapping_df.copy()
    mapping_df[ID_COLUMN] = normalize_series(mapping_df[ID_COLUMN])

    merge_cols = [ID_COLUMN, "pseudoID"]
    if "studyGroup_blind" in mapping_df.columns:
        merge_cols.append("studyGroup_blind")

    df = df.merge(mapping_df[merge_cols], on=ID_COLUMN, how="left")

    # Replace studyGroup with blinded version
    if STUDYGROUP_COLUMN in df.columns and "studyGroup_blind" in df.columns:
        df[STUDYGROUP_COLUMN] = df["studyGroup_blind"]
        df = df.drop(columns=["studyGroup_blind"])

    # Remove direct identifiers from analysis file
    cols_to_drop = [col for col in DIRECT_IDENTIFIER_COLUMNS if col in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Keep internal id or drop it depending on your needs:
    # Here we drop original id from the analysis dataset to strengthen pseudonymization.
    if ID_COLUMN in df.columns:
        df = df.drop(columns=[ID_COLUMN])

    # Put pseudoID first
    cols = df.columns.tolist()
    if "pseudoID" in cols:
        cols = ["pseudoID"] + [c for c in cols if c != "pseudoID"]
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


if __name__ == "__main__":
    main()
