import os
import random
import string
from pathlib import Path

import pandas as pd

# =========================================================
# CONFIG section - adjust as needed for your specific survey export and requirements
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

INPUT_FILE = "results-survey_T3.csv"
MAPPING_FILE = "survey_mapping_sensitive.csv"
PSEUDONYMIZED_OUTPUT = "survey_pseudonymized.csv"

ID_COLUMN = "id"
MATCH_KEY_COLUMN = "match_key"

DIRECT_IDENTIFIER_COLUMNS = [
    "Name",
    "eMailIG",
    "eMailKG",
    "PhoneSystem",
    "randomGroup",
]

STUDYGROUP_COLUMN = "studyGroup"

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
    path_obj = Path(path)
    suffix = path_obj.suffix.lower()

    if suffix == ".csv":
        for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            for sep in [",", ";", "\t", "|"]:
                try:
                    df = pd.read_csv(path_obj, encoding=encoding, sep=sep)
                    if df.shape[1] > 1:
                        return df
                except Exception:
                    pass

        for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            try:
                df = pd.read_csv(path_obj, encoding=encoding, sep=None, engine="python")
                if df.shape[1] > 1:
                    return df
            except Exception:
                pass

        raise ValueError("Could not read CSV file with common encoding/separator combinations.")

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path_obj)

    raise ValueError(f"Unsupported file type: {suffix}")


def random_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def normalize_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


def clean_scalar(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def normalize_email(value) -> str:
    return clean_scalar(value).lower()


def normalize_name(value) -> str:
    text = clean_scalar(value).lower()
    text = " ".join(text.split())
    return text


def pick_email(row: pd.Series) -> str:
    for col in ["eMailIG", "eMailKG"]:
        if col in row.index:
            value = normalize_email(row[col])
            if value != "":
                return value
    return ""


def split_name(value) -> tuple[str, str]:
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


def ensure_matching_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a stable internal match key:
    - unique name -> name::<normalized_name>
    - duplicate name -> name_email::<normalized_name>::<normalized_email>
    """
    df = df.copy()

    if "Name" not in df.columns:
        raise KeyError("Required column 'Name' not found in input file.")

    df["name_key"] = df["Name"].apply(normalize_name)
    df["email_key"] = df.apply(pick_email, axis=1)

    missing_name_mask = df["name_key"] == ""
    if missing_name_mask.any():
        raise ValueError(
            f"{int(missing_name_mask.sum())} row(s) have no usable value in 'Name'. "
            "Cannot match participants by name."
        )

    name_counts = df["name_key"].value_counts(dropna=False)
    duplicate_names = set(name_counts[name_counts > 1].index.tolist())

    def build_match_key(row):
        name_key = row["name_key"]
        email_key = row["email_key"]

        if name_key not in duplicate_names:
            return f"name::{name_key}"

        if email_key == "":
            raise ValueError(
                f"Duplicate name without usable email found: '{row['Name']}'. "
                "Need an email to disambiguate participants with identical names."
            )

        return f"name_email::{name_key}::{email_key}"

    df[MATCH_KEY_COLUMN] = df.apply(build_match_key, axis=1)
    return df


def validate_match_keys(df: pd.DataFrame):
    missing_mask = df[MATCH_KEY_COLUMN] == ""
    if missing_mask.any():
        raise ValueError("Some rows have an empty match_key.")

    duplicate_mask = df.duplicated(subset=[MATCH_KEY_COLUMN], keep=False)
    if duplicate_mask.any():
        duplicates = (
            df.loc[duplicate_mask, MATCH_KEY_COLUMN]
            .value_counts()
            .sort_values(ascending=False)
        )
        example_text = ", ".join([f"{k} ({v}x)" for k, v in duplicates.head(10).items()])
        raise ValueError(
            "Duplicate match keys found in the input file. "
            f"Examples: {example_text}"
        )


def ensure_mapping_columns(mapping_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        MATCH_KEY_COLUMN,
        PSEUDOID_COLUMN,
        TOKEN_COLUMN,
        FIRSTNAME_COLUMN,
        LASTNAME_COLUMN,
        EMAIL_COLUMN,
        ATTRIBUTE_1_COLUMN,
        ATTRIBUTE_2_COLUMN,
        BLINDED_GROUP_COLUMN,
    ] + DIRECT_IDENTIFIER_COLUMNS + [STUDYGROUP_COLUMN, "name_key", "email_key"]

    if ID_COLUMN not in mapping_df.columns:
        mapping_df[ID_COLUMN] = ""

    for col in required_columns:
        if col not in mapping_df.columns:
            mapping_df[col] = ""

    return mapping_df


def backfill_mapping_columns(mapping_df: pd.DataFrame) -> pd.DataFrame:
    mapping_df = mapping_df.copy()
    mapping_df = ensure_mapping_columns(mapping_df)

    if "Name" in mapping_df.columns:
        mapping_df["name_key"] = mapping_df["Name"].apply(normalize_name)
    else:
        mapping_df["name_key"] = ""

    if "email_key" in mapping_df.columns:
        mapping_df["email_key"] = mapping_df["email_key"].replace("", pd.NA)
        if EMAIL_COLUMN in mapping_df.columns:
            mapping_df["email_key"] = mapping_df["email_key"].fillna(
                mapping_df[EMAIL_COLUMN].apply(normalize_email)
            )
        if "eMailIG" in mapping_df.columns:
            mapping_df["email_key"] = mapping_df["email_key"].fillna(
                mapping_df["eMailIG"].apply(normalize_email)
            )
        if "eMailKG" in mapping_df.columns:
            mapping_df["email_key"] = mapping_df["email_key"].fillna(
                mapping_df["eMailKG"].apply(normalize_email)
            )
        mapping_df["email_key"] = mapping_df["email_key"].fillna("")

    # Keep existing pseudoIDs; only normalize empties
    mapping_df[PSEUDOID_COLUMN] = mapping_df[PSEUDOID_COLUMN].replace("", pd.NA)

    # Ensure token exists and is different from pseudoID
    existing_tokens = set()
    if TOKEN_COLUMN in mapping_df.columns:
        existing_tokens = set(
            mapping_df[TOKEN_COLUMN].dropna().astype(str).tolist()
        )

    new_tokens = []
    for _, row in mapping_df.iterrows():
        current_token = clean_scalar(row[TOKEN_COLUMN]) if TOKEN_COLUMN in mapping_df.columns else ""
        current_pseudoid = clean_scalar(row[PSEUDOID_COLUMN])

        if current_token == "" or current_token == current_pseudoid:
            new_token = random_code(8)
            while new_token in existing_tokens or new_token == current_pseudoid:
                new_token = random_code(8)
            existing_tokens.add(new_token)
            new_tokens.append(new_token)
        else:
            existing_tokens.add(current_token)
            new_tokens.append(current_token)

    mapping_df[TOKEN_COLUMN] = new_tokens

    if "Name" in mapping_df.columns:
        rebuilt_first = []
        rebuilt_last = []
        for _, row in mapping_df.iterrows():
            current_first = clean_scalar(row[FIRSTNAME_COLUMN])
            current_last = clean_scalar(row[LASTNAME_COLUMN])
            if current_first == "" and current_last == "":
                first, last = split_name(row["Name"])
            else:
                first, last = current_first, current_last
            rebuilt_first.append(first)
            rebuilt_last.append(last)
        mapping_df[FIRSTNAME_COLUMN] = rebuilt_first
        mapping_df[LASTNAME_COLUMN] = rebuilt_last

    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].replace("", pd.NA)
    if "eMailIG" in mapping_df.columns:
        mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna(mapping_df["eMailIG"])
    if "eMailKG" in mapping_df.columns:
        mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna(mapping_df["eMailKG"])
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].fillna("")
    mapping_df[EMAIL_COLUMN] = mapping_df[EMAIL_COLUMN].apply(normalize_email)

    mapping_df[ATTRIBUTE_1_COLUMN] = mapping_df[ATTRIBUTE_1_COLUMN].replace("", pd.NA)
    mapping_df[ATTRIBUTE_1_COLUMN] = mapping_df[ATTRIBUTE_1_COLUMN].fillna(mapping_df[STUDYGROUP_COLUMN])

    mapping_df[ATTRIBUTE_2_COLUMN] = mapping_df[ATTRIBUTE_2_COLUMN].replace("", pd.NA)
    if "PhoneSystem" in mapping_df.columns:
        mapping_df[ATTRIBUTE_2_COLUMN] = mapping_df[ATTRIBUTE_2_COLUMN].fillna(mapping_df["PhoneSystem"])

    for col in [
        ID_COLUMN,
        MATCH_KEY_COLUMN,
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
        "name_key",
        "email_key",
    ]:
        if col in mapping_df.columns:
            if col in [EMAIL_COLUMN, "eMailIG", "eMailKG", "email_key"]:
                mapping_df[col] = mapping_df[col].apply(normalize_email)
            elif col == "name_key":
                mapping_df[col] = mapping_df[col].apply(normalize_name)
            else:
                mapping_df[col] = mapping_df[col].apply(clean_scalar)

    return mapping_df


def build_or_update_mapping(df: pd.DataFrame, mapping_file: str) -> pd.DataFrame:
    df = ensure_matching_columns(df)
    validate_match_keys(df)

    if Path(mapping_file).exists():
        mapping_df = pd.read_csv(mapping_file, dtype=str)
        mapping_df = ensure_mapping_columns(mapping_df)
        mapping_df = backfill_mapping_columns(mapping_df)
    else:
        mapping_df = pd.DataFrame()

    existing_keys = set()
    existing_pseudoids = set()
    existing_tokens = set()
    existing_group_map = {}

    if not mapping_df.empty:
        existing_keys = set(mapping_df[MATCH_KEY_COLUMN].astype(str).tolist())

        if PSEUDOID_COLUMN in mapping_df.columns:
            existing_pseudoids = set(mapping_df[PSEUDOID_COLUMN].dropna().astype(str).tolist())

        if TOKEN_COLUMN in mapping_df.columns:
            existing_tokens = set(mapping_df[TOKEN_COLUMN].dropna().astype(str).tolist())

        if STUDYGROUP_COLUMN in mapping_df.columns and BLINDED_GROUP_COLUMN in mapping_df.columns:
            for _, row in mapping_df[[STUDYGROUP_COLUMN, BLINDED_GROUP_COLUMN]].dropna().drop_duplicates().iterrows():
                original = clean_scalar(row[STUDYGROUP_COLUMN])
                blinded = clean_scalar(row[BLINDED_GROUP_COLUMN])
                if original != "" and blinded != "":
                    existing_group_map[original] = blinded

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

    new_rows = []
    for _, source_row in df.iterrows():
        participant_key = source_row[MATCH_KEY_COLUMN]

        if participant_key in existing_keys:
            continue

        pseudoid = random_code(8)
        while pseudoid in existing_pseudoids:
            pseudoid = random_code(8)
        existing_pseudoids.add(pseudoid)

        token = random_code(8)
        while token in existing_tokens or token == pseudoid:
            token = random_code(8)
        existing_tokens.add(token)

        existing_keys.add(participant_key)

        firstname, lastname = split_name(source_row["Name"]) if "Name" in df.columns else ("", "")
        email = pick_email(source_row)
        phone = clean_scalar(source_row["PhoneSystem"]) if "PhoneSystem" in df.columns else ""

        row = {
            MATCH_KEY_COLUMN: participant_key,
            "name_key": normalize_name(source_row["Name"]) if "Name" in df.columns else "",
            "email_key": pick_email(source_row),
            ID_COLUMN: clean_scalar(source_row[ID_COLUMN]) if ID_COLUMN in df.columns else "",
            PSEUDOID_COLUMN: pseudoid,
        }

        for col in DIRECT_IDENTIFIER_COLUMNS:
            if col in df.columns:
                value = source_row[col]
                row[col] = normalize_email(value) if col in ["eMailIG", "eMailKG"] else clean_scalar(value)

        orig_group = ""
        if STUDYGROUP_COLUMN in df.columns:
            orig_group = clean_scalar(source_row[STUDYGROUP_COLUMN])
            row[STUDYGROUP_COLUMN] = orig_group
            row[BLINDED_GROUP_COLUMN] = existing_group_map.get(orig_group, "")

        row[TOKEN_COLUMN] = token
        row[FIRSTNAME_COLUMN] = firstname
        row[LASTNAME_COLUMN] = lastname
        row[EMAIL_COLUMN] = email
        row[ATTRIBUTE_1_COLUMN] = orig_group
        row[ATTRIBUTE_2_COLUMN] = phone

        new_rows.append(row)

    new_rows_df = pd.DataFrame(new_rows)
    if not new_rows_df.empty:
        new_rows_df = ensure_mapping_columns(new_rows_df)
    else:
        new_rows_df = pd.DataFrame(columns=ensure_mapping_columns(pd.DataFrame()).columns)

    if mapping_df.empty:
        mapping_df = new_rows_df.copy()
    elif not new_rows_df.empty:
        mapping_df = pd.concat([mapping_df, new_rows_df], ignore_index=True)

    mapping_df = ensure_mapping_columns(mapping_df)
    mapping_df = backfill_mapping_columns(mapping_df)

    if mapping_df[MATCH_KEY_COLUMN].eq("").any():
        raise ValueError("The mapping file contains empty match keys.")

    if mapping_df.duplicated(subset=[MATCH_KEY_COLUMN], keep=False).any():
        raise ValueError("The mapping file contains duplicate match keys.")

    if (mapping_df[PSEUDOID_COLUMN] == mapping_df[TOKEN_COLUMN]).any():
        raise ValueError("At least one row still has pseudoID equal to token after processing.")

    return mapping_df


def pseudonymize_dataset(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = ensure_matching_columns(df)
    validate_match_keys(df)

    mapping_df = mapping_df.copy()

    merge_cols = [MATCH_KEY_COLUMN, PSEUDOID_COLUMN]
    if BLINDED_GROUP_COLUMN in mapping_df.columns:
        merge_cols.append(BLINDED_GROUP_COLUMN)

    df = df.merge(mapping_df[merge_cols], on=MATCH_KEY_COLUMN, how="left")

    if STUDYGROUP_COLUMN in df.columns and BLINDED_GROUP_COLUMN in df.columns:
        df[STUDYGROUP_COLUMN] = df[BLINDED_GROUP_COLUMN]
        df = df.drop(columns=[BLINDED_GROUP_COLUMN])

    cols_to_drop = [col for col in DIRECT_IDENTIFIER_COLUMNS if col in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    for col in [ID_COLUMN, MATCH_KEY_COLUMN, "name_key", "email_key"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    cols = df.columns.tolist()
    if PSEUDOID_COLUMN in cols:
        cols = [PSEUDOID_COLUMN] + [c for c in cols if c != PSEUDOID_COLUMN]
        df = df[cols]

    return df


def main():
    random.seed(40)

    print(f"Working directory: {Path.cwd()}")
    print(f"Script file: {Path(__file__).resolve()}")
    print(f"Input file: {SCRIPT_DIR / INPUT_FILE}")

    df = read_survey_file(INPUT_FILE)
    mapping_df = build_or_update_mapping(df, MAPPING_FILE)
    analysis_df = pseudonymize_dataset(df, mapping_df)

    mapping_path = SCRIPT_DIR / MAPPING_FILE
    analysis_path = SCRIPT_DIR / PSEUDONYMIZED_OUTPUT

    mapping_df.to_csv(mapping_path, index=False)
    analysis_df.to_csv(analysis_path, index=False)

    print("Done.")
    print(f"Input rows: {len(df)}")
    print(f"Unique participants by match key: {mapping_df[MATCH_KEY_COLUMN].nunique()}")
    print(f"Mapping file written to: {mapping_path}")
    print(f"Analysis file written to: {analysis_path}")
    print(f"PseudoIDs unique: {mapping_df[PSEUDOID_COLUMN].nunique()}")
    print(f"Tokens unique: {mapping_df[TOKEN_COLUMN].nunique()}")
    print(f"Rows with pseudoID == token: {(mapping_df[PSEUDOID_COLUMN] == mapping_df[TOKEN_COLUMN]).sum()}")


if __name__ == "__main__":
    main()