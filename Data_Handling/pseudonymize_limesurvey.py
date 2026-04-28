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

INPUT_FILE = "results-survey_T2.csv"
MAPPING_FILE = "survey_mapping_sensitive.csv"
PSEUDONYMIZED_OUTPUT = "survey_pseudonymized_T2.csv"
PARTICIPANTS_IMPORT_OUTPUT = "survey_participants_import.csv"

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
ATTRIBUTE_3_COLUMN = "attribute_3"   # invitation date
ATTRIBUTE_4_COLUMN = "attribute_4"   # reminder 1 date
ATTRIBUTE_5_COLUMN = "attribute_5"   # reminder 2 date
ATTRIBUTE_6_COLUMN = "attribute_6"   # reminder 3 date
BLINDED_GROUP_COLUMN = "studyGroup_blind"

# Source date for schedule creation.
# Set this to the column that contains the participant-specific start date
# of the first intervention phase.
START_DATE_COLUMN = "submitdate"

# Study schedule rules
INVITATION_OFFSET_WEEKS = 12
REMINDER_1_OFFSET_DAYS = 3
REMINDER_2_OFFSET_DAYS = 7
REMINDER_3_OFFSET_DAYS = 11
DATE_OUTPUT_FORMAT = "%Y-%m-%d"

# =========================================================
# ATTENTION CHECK / ACheck RULES
# =========================================================
APPLY_ATTENTION_CHECK_NA = True
ATTENTION_CHECK_COLUMNS = ["ACheck1[ACheck1]", "KIM[ACheck2]"]
ATTENTION_CHECK_CORRECT_VALUE = "3"
MIN_CORRECT_ATTENTION_CHECKS = 1
ATTENTION_CHECK_FAILURE_OUTPUT = "attention_check_failures.csv"
ATTENTION_CHECK_KEEP_COLUMNS = [
    PSEUDOID_COLUMN,
    STUDYGROUP_COLUMN,
    "timePoint",
    "attention_check_correct_count",
    "attention_check_failed",
]


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


def parse_date_value(value) -> pd.Timestamp | None:
    cleaned = clean_scalar(value)
    if cleaned == "":
        return None

    # dayfirst=False keeps ISO handling stable; infer_datetime_format is deprecated
    parsed = pd.to_datetime(cleaned, errors="coerce", utc=False)
    return parsed


def format_date_value(value) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime(DATE_OUTPUT_FORMAT)


def calculate_schedule_from_start(start_value) -> dict[str, str]:
    start_date = parse_date_value(start_value)
    if pd.isna(start_date):
        return {
            ATTRIBUTE_3_COLUMN: "",
            ATTRIBUTE_4_COLUMN: "",
            ATTRIBUTE_5_COLUMN: "",
            ATTRIBUTE_6_COLUMN: "",
        }

    invitation_date = start_date + pd.Timedelta(weeks=INVITATION_OFFSET_WEEKS)
    reminder_1_date = invitation_date + pd.Timedelta(days=REMINDER_1_OFFSET_DAYS)
    reminder_2_date = invitation_date + pd.Timedelta(days=REMINDER_2_OFFSET_DAYS)
    reminder_3_date = invitation_date + pd.Timedelta(days=REMINDER_3_OFFSET_DAYS)

    return {
        ATTRIBUTE_3_COLUMN: format_date_value(invitation_date),
        ATTRIBUTE_4_COLUMN: format_date_value(reminder_1_date),
        ATTRIBUTE_5_COLUMN: format_date_value(reminder_2_date),
        ATTRIBUTE_6_COLUMN: format_date_value(reminder_3_date),
    }


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
        ATTRIBUTE_3_COLUMN,
        ATTRIBUTE_4_COLUMN,
        ATTRIBUTE_5_COLUMN,
        ATTRIBUTE_6_COLUMN,
        BLINDED_GROUP_COLUMN,
    ] + DIRECT_IDENTIFIER_COLUMNS + [STUDYGROUP_COLUMN, "name_key", "email_key"]

    if ID_COLUMN not in mapping_df.columns:
        mapping_df[ID_COLUMN] = ""

    if START_DATE_COLUMN not in mapping_df.columns:
        mapping_df[START_DATE_COLUMN] = ""

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

    mapping_df[PSEUDOID_COLUMN] = mapping_df[PSEUDOID_COLUMN].replace("", pd.NA)

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

    # Keep existing schedule values if already present. Only fill missing ones from START_DATE_COLUMN.
    schedule_df = mapping_df[START_DATE_COLUMN].apply(calculate_schedule_from_start).apply(pd.Series)
    for schedule_col in [ATTRIBUTE_3_COLUMN, ATTRIBUTE_4_COLUMN, ATTRIBUTE_5_COLUMN, ATTRIBUTE_6_COLUMN]:
        mapping_df[schedule_col] = mapping_df[schedule_col].replace("", pd.NA)
        mapping_df[schedule_col] = mapping_df[schedule_col].fillna(schedule_df[schedule_col])
        mapping_df[schedule_col] = mapping_df[schedule_col].fillna("")

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
        ATTRIBUTE_3_COLUMN,
        ATTRIBUTE_4_COLUMN,
        ATTRIBUTE_5_COLUMN,
        ATTRIBUTE_6_COLUMN,
        BLINDED_GROUP_COLUMN,
        "Name",
        "PhoneSystem",
        "eMailIG",
        "eMailKG",
        STUDYGROUP_COLUMN,
        START_DATE_COLUMN,
        "name_key",
        "email_key",
    ]:
        if col in mapping_df.columns:
            if col in [EMAIL_COLUMN, "eMailIG", "eMailKG", "email_key"]:
                mapping_df[col] = mapping_df[col].apply(normalize_email)
            else:
                mapping_df[col] = mapping_df[col].apply(clean_scalar)

    return mapping_df


def build_or_update_mapping(df: pd.DataFrame, mapping_file: str) -> pd.DataFrame:
    df = ensure_matching_columns(df)
    validate_match_keys(df)

    if START_DATE_COLUMN not in df.columns:
        raise KeyError(
            f"Required date column '{START_DATE_COLUMN}' not found in input file. "
            "Please set START_DATE_COLUMN to the participant-specific intervention start date column."
        )

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
        orig_group = clean_scalar(source_row[STUDYGROUP_COLUMN]) if STUDYGROUP_COLUMN in df.columns else ""
        start_date_raw = clean_scalar(source_row[START_DATE_COLUMN])
        schedule = calculate_schedule_from_start(start_date_raw)

        row = {
            MATCH_KEY_COLUMN: participant_key,
            "name_key": normalize_name(source_row["Name"]) if "Name" in df.columns else "",
            "email_key": pick_email(source_row),
            ID_COLUMN: clean_scalar(source_row[ID_COLUMN]) if ID_COLUMN in df.columns else "",
            PSEUDOID_COLUMN: pseudoid,
            START_DATE_COLUMN: start_date_raw,
            STUDYGROUP_COLUMN: orig_group,
            BLINDED_GROUP_COLUMN: existing_group_map.get(orig_group, ""),
            TOKEN_COLUMN: token,
            FIRSTNAME_COLUMN: firstname,
            LASTNAME_COLUMN: lastname,
            EMAIL_COLUMN: email,
            ATTRIBUTE_1_COLUMN: orig_group,
            ATTRIBUTE_2_COLUMN: phone,
            ATTRIBUTE_3_COLUMN: schedule[ATTRIBUTE_3_COLUMN],
            ATTRIBUTE_4_COLUMN: schedule[ATTRIBUTE_4_COLUMN],
            ATTRIBUTE_5_COLUMN: schedule[ATTRIBUTE_5_COLUMN],
            ATTRIBUTE_6_COLUMN: schedule[ATTRIBUTE_6_COLUMN],
        }

        for col in DIRECT_IDENTIFIER_COLUMNS:
            if col in df.columns:
                value = source_row[col]
                row[col] = normalize_email(value) if col in ["eMailIG", "eMailKG"] else clean_scalar(value)

        new_rows.append(row)

    new_rows_df = pd.DataFrame(new_rows)
    if not new_rows_df.empty:
        new_rows_df = ensure_mapping_columns(new_rows_df)
    else:
        mapping_template = ensure_mapping_columns(pd.DataFrame())
        new_rows_df = pd.DataFrame(columns=mapping_template.columns)

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



def add_attention_check_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if not APPLY_ATTENTION_CHECK_NA:
        df["attention_check_correct_count"] = pd.NA
        df["attention_check_failed"] = False
        return df

    existing_acheck_cols = [col for col in ATTENTION_CHECK_COLUMNS if col in df.columns]
    missing_acheck_cols = [col for col in ATTENTION_CHECK_COLUMNS if col not in df.columns]

    if missing_acheck_cols:
        print("Warning: Attention-check column(s) not found and ignored: " + ", ".join(missing_acheck_cols))

    if not existing_acheck_cols:
        print("Warning: No attention-check columns found. No ACheck NA rule applied.")
        df["attention_check_correct_count"] = pd.NA
        df["attention_check_failed"] = False
        return df

    correct_matrix = pd.DataFrame(index=df.index)
    for col in existing_acheck_cols:
        correct_matrix[col] = df[col].apply(lambda v: clean_scalar(v).replace("\xa0", " ").strip().startswith(ATTENTION_CHECK_CORRECT_VALUE))

    df["attention_check_correct_count"] = correct_matrix.sum(axis=1).astype("Int64")
    df["attention_check_failed"] = df["attention_check_correct_count"] < MIN_CORRECT_ATTENTION_CHECKS

    return df


def apply_attention_check_na_rule(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = add_attention_check_flags(df)

    if not APPLY_ATTENTION_CHECK_NA or "attention_check_failed" not in df.columns:
        return df, pd.DataFrame()

    failed_mask = df["attention_check_failed"] == True

    report_cols = [
        col for col in [
            PSEUDOID_COLUMN,
            STUDYGROUP_COLUMN,
            "timePoint",
            "attention_check_correct_count",
            "attention_check_failed",
        ] + ATTENTION_CHECK_COLUMNS
        if col in df.columns
    ]
    failure_report = df.loc[failed_mask, report_cols].copy()

    keep_cols = [col for col in ATTENTION_CHECK_KEEP_COLUMNS if col in df.columns]
    cols_to_na = [col for col in df.columns if col not in keep_cols]
    df.loc[failed_mask, cols_to_na] = pd.NA

    return df, failure_report

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


def build_participants_import(mapping_df: pd.DataFrame) -> pd.DataFrame:
    participants_df = mapping_df.copy()

    import_columns = [
        TOKEN_COLUMN,
        FIRSTNAME_COLUMN,
        LASTNAME_COLUMN,
        EMAIL_COLUMN,
        ATTRIBUTE_1_COLUMN,
        ATTRIBUTE_2_COLUMN,
        ATTRIBUTE_3_COLUMN,
        ATTRIBUTE_4_COLUMN,
        ATTRIBUTE_5_COLUMN,
        ATTRIBUTE_6_COLUMN,
    ]

    for col in import_columns:
        if col not in participants_df.columns:
            participants_df[col] = ""

    participants_df = participants_df[import_columns].copy()
    participants_df = participants_df.drop_duplicates(subset=[TOKEN_COLUMN], keep="first")

    return participants_df


def main():
    random.seed(40)

    df = read_survey_file(INPUT_FILE)

    # Drop incomplete LimeSurvey rows without a usable name before matching.
    # These are usually aborted/test rows and cannot be linked to the mapping file.
    if "Name" in df.columns:
        before_rows = len(df)
        df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "")].copy()
        dropped_rows = before_rows - len(df)
        if dropped_rows > 0:
            print(f"Dropped incomplete row(s) without Name before matching: {dropped_rows}")

    mapping_df = build_or_update_mapping(df, MAPPING_FILE)
    analysis_df = pseudonymize_dataset(df, mapping_df)
    analysis_df, attention_failure_df = apply_attention_check_na_rule(analysis_df)
    participants_df = build_participants_import(mapping_df)

    mapping_path = SCRIPT_DIR / MAPPING_FILE
    analysis_path = SCRIPT_DIR / PSEUDONYMIZED_OUTPUT
    participants_path = SCRIPT_DIR / PARTICIPANTS_IMPORT_OUTPUT
    attention_failure_path = SCRIPT_DIR / ATTENTION_CHECK_FAILURE_OUTPUT

    mapping_df.to_csv(mapping_path, index=False)
    analysis_df.to_csv(analysis_path, index=False)
    participants_df.to_csv(participants_path, index=False)
    attention_failure_df.to_csv(attention_failure_path, index=False)

    print("Done.")
    print(f"Input rows: {len(df)}")
    print(f"Unique participants by match key: {mapping_df[MATCH_KEY_COLUMN].nunique()}")
    print(f"Rows set to NA due to failed attention checks: {len(attention_failure_df)}")
    if len(attention_failure_df) > 0 and PSEUDOID_COLUMN in attention_failure_df.columns:
        print("Affected pseudoIDs: " + ", ".join(attention_failure_df[PSEUDOID_COLUMN].astype(str).tolist()))
    print(f"PseudoIDs unique: {mapping_df[PSEUDOID_COLUMN].nunique()}")
    print(f"Tokens unique: {mapping_df[TOKEN_COLUMN].nunique()}")
    print(f"Rows with pseudoID == token: {(mapping_df[PSEUDOID_COLUMN] == mapping_df[TOKEN_COLUMN]).sum()}")

if __name__ == "__main__":
    main()
