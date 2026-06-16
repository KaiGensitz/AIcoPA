#!/usr/bin/env python3
"""Privacy-focused LimeSurvey pseudonymization workflow.

This is a pseudonymization script for active longitudinal study operations. It
keeps a sensitive mapping/contact workflow so participants can be linked across
T1/T2/T3 via stable pseudoID, but prevents contact tokens/direct identifiers
from entering default analysis outputs.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import random
import re
import secrets
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_IDENTIFIER_COLUMNS = {
    "Name", "firstname", "lastname", "email", "eMailIG", "eMailKG",
    "PhoneSystem", "randomGroup", "match_key", "name_key", "email_key",
    "token", "refurl", "id",
}
DEFAULT_TECHNICAL_COLUMNS = {"submitdate", "startdate", "datestamp", "interviewtime", "refurl"}
DEFAULT_FREE_TEXT_COLUMNS = {"TransferAppDetail", "QualPos", "QualNeg", "otherAppUse", "QualOthApp", "SystemLink"}
ALPHABET = string.ascii_uppercase + string.digits


def read_csv(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            with path.open(newline="", encoding=encoding) as handle:
                sample = handle.read(4096)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
                return list(csv.DictReader(handle, dialect=dialect))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {path} with supported encodings")


def read_excel(path: Path) -> list[dict[str, str]]:
    if importlib.util.find_spec("openpyxl") is None:
        raise ImportError("openpyxl is required to read .xlsx files. Install it with 'pip install openpyxl'.")
    import openpyxl

    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        raw_rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not raw_rows:
        return []

    headers = [str(cell) if cell is not None else "" for cell in raw_rows[0]]
    rows: list[dict[str, str]] = []
    for raw_row in raw_rows[1:]:
        raw_row = raw_row or []
        row = {
            headers[index]: "" if index >= len(raw_row) or raw_row[index] is None else str(raw_row[index])
            for index in range(len(headers))
        }
        rows.append(row)
    return rows


def read_input(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".xlsx":
        return read_excel(path)
    return read_csv(path)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path | None, default: dict) -> dict:
    if not path:
        return default
    with path.open(encoding="utf-8") as handle:
        merged = dict(default)
        merged.update(json.load(handle))
        return merged


def normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def first_email(row: dict[str, str]) -> str:
    return normalize(row.get("eMailIG")) or normalize(row.get("eMailKG")) or normalize(row.get("email"))


def make_match_keys(rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        row["name_key"] = normalize(row.get("Name") or " ".join([row.get("firstname", ""), row.get("lastname", "")]))
        row["email_key"] = first_email(row)
        counts[row["name_key"]] = counts.get(row["name_key"], 0) + 1
    for row in rows:
        if not row["name_key"]:
            raise ValueError("Cannot create match_key for row without name")
        if counts[row["name_key"]] == 1:
            row["match_key"] = f"name::{row['name_key']}"
        else:
            if not row["email_key"]:
                raise ValueError(f"Duplicate name '{row['name_key']}' requires email for matching")
            row["match_key"] = f"name_email::{row['name_key']}::{row['email_key']}"


def random_code(length: int, demo: bool, rng: random.Random) -> str:
    chooser = rng.choice if demo else secrets.choice
    return "".join(chooser(ALPHABET) for _ in range(length))


def unique_code(existing: set[str], length: int, demo: bool, rng: random.Random) -> str:
    while True:
        code = random_code(length, demo, rng)
        if code not in existing:
            existing.add(code)
            return code


def parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime((value or "").strip(), fmt)
        except ValueError:
            pass
    return None


def date_plus(value: str, days: int) -> str:
    parsed = parse_date(value)
    return (parsed + timedelta(days=days)).strftime("%Y-%m-%d") if parsed else ""


def load_mapping(path: Path) -> list[dict[str, str]]:
    return read_input(path) if path.exists() else []


def build_or_update_mapping(rows: list[dict[str, str]], mapping_rows: list[dict[str, str]], demo: bool) -> list[dict[str, str]]:
    rng = random.Random(40)
    by_key = {r.get("match_key", ""): r for r in mapping_rows if r.get("match_key")}
    used_pids = {r.get("pseudoID", "") for r in mapping_rows if r.get("pseudoID")}
    used_tokens = {r.get("token", "") for r in mapping_rows if r.get("token")}
    blinded: dict[str, str] = {r.get("studyGroup", ""): r.get("studyGroup_blind", "") for r in mapping_rows if r.get("studyGroup") and r.get("studyGroup_blind")}
    used_blind = set(blinded.values())

    for row in rows:
        key = row["match_key"]
        if key in by_key:
            continue
        pseudo = unique_code(used_pids, 8, demo, rng)
        token = unique_code(used_tokens, 12, demo, rng)
        while token == pseudo:
            token = unique_code(used_tokens, 12, demo, rng)
        group = row.get("studyGroup") or row.get("randomGroup") or ""
        if group and group not in blinded:
            while True:
                code = f"{int(unique_code(set(), 2, demo, rng), 36) % 90 + 10:02d}"
                if code not in used_blind:
                    used_blind.add(code)
                    blinded[group] = code
                    break
        submit = row.get("submitdate", "")
        entry = {
            "match_key": key,
            "name_key": row.get("name_key", ""),
            "email_key": row.get("email_key", ""),
            "id": row.get("id", ""),
            "pseudoID": pseudo,
            "token": token,
            "firstname": row.get("firstname") or (row.get("Name", "").split(" ", 1)[0] if row.get("Name") else ""),
            "lastname": row.get("lastname") or (row.get("Name", "").split(" ", 1)[1] if " " in row.get("Name", "") else ""),
            "email": row.get("email") or row.get("eMailIG") or row.get("eMailKG") or "",
            "Name": row.get("Name", ""),
            "eMailIG": row.get("eMailIG", ""),
            "eMailKG": row.get("eMailKG", ""),
            "PhoneSystem": row.get("PhoneSystem", ""),
            "studyGroup": group,
            "studyGroup_blind": blinded.get(group, ""),
            "attribute_1": blinded.get(group, ""),
            "attribute_2": row.get("PhoneSystem", ""),
            "attribute_3": date_plus(submit, 84),
            "attribute_4": date_plus(submit, 87),
            "attribute_5": date_plus(submit, 91),
            "attribute_6": date_plus(submit, 95),
        }
        mapping_rows.append(entry)
        by_key[key] = entry
    return mapping_rows


def classify_columns(headers: list[str], config: dict, allow_technical: bool, allow_free_text: bool) -> tuple[list[str], list[tuple[str, str]]]:
    direct = DEFAULT_IDENTIFIER_COLUMNS | set(config.get("direct_identifier_columns", []))
    raw_operational = {"randomGroup", "studyGroup", "SystemLink", "eMailValidIG", "eMailValidKG"}
    technical = DEFAULT_TECHNICAL_COLUMNS | set(config.get("technical_metadata_columns", []))
    free_text = DEFAULT_FREE_TEXT_COLUMNS | set(config.get("free_text_columns", []))

    def is_privacy_risky(field: str) -> bool:
        lower = field.lower()
        return (
            field in free_text
            or "comment" in lower
            or "other" in lower
            or lower.endswith("[other]")
            or field == "Wohnort"
        )

    keep: list[str] = []
    dropped: list[tuple[str, str]] = []
    for field in headers:
        if field in direct:
            dropped.append((field, "direct identifier or contact field"))
        elif field in raw_operational:
            dropped.append((field, "raw/unblinded operational field"))
        elif field in technical or field.endswith("Time") or field.startswith("groupTime"):
            if allow_technical:
                keep.append(field)
            else:
                dropped.append((field, "technical metadata or timing field"))
        elif is_privacy_risky(field):
            if allow_free_text:
                keep.append(field)
            else:
                dropped.append((field, "free-text or privacy-risky field"))
        else:
            keep.append(field)
    return keep, dropped


def build_analysis(rows: list[dict[str, str]], mapping: dict[str, dict[str, str]], config: dict, args) -> tuple[list[dict[str, object]], list[str], dict]:
    headers = list(rows[0].keys()) if rows else []
    keep, dropped = classify_columns(headers, config, args.allow_technical_metadata, args.allow_free_text)
    allow = set(config.get("analysis_allowlist", []))
    kept_automatic = [field for field in keep if field not in {"timePoint", "studyGroup_blind"}]
    new_kept_columns = [field for field in kept_automatic if field not in allow]
    columns_review = {
        "kept_automatic": kept_automatic,
        "dropped_automatic": [{"column": field, "reason": reason} for field, reason in dropped],
        "new_kept_columns": new_kept_columns,
    }
    out_fields = ["pseudoID", "timePoint", "studyGroup_blind"] + [c for c in keep if c not in {"timePoint", "studyGroup_blind"}]
    out_rows = []
    for row in rows:
        m = mapping[row["match_key"]]
        out = {"pseudoID": m["pseudoID"], "timePoint": args.wave, "studyGroup_blind": m.get("studyGroup_blind", "")}
        for col in keep:
            out[col] = row.get(col, "")
        out_rows.append(out)
    return out_rows, out_fields, columns_review


def attention_failures(analysis_rows: list[dict[str, object]], config: dict) -> list[dict[str, object]]:
    cols = config.get("columns", [])
    min_correct = int(config.get("min_correct", 1))
    prefix = str(config.get("correct_prefix", "3"))
    failures = []
    for row in analysis_rows:
        correct = sum(str(row.get(c, "")).strip().startswith(prefix) for c in cols)
        row["attention_correct_count"] = correct
        row["attention_failed"] = correct < min_correct
        if row["attention_failed"]:
            failures.append({"pseudoID": row.get("pseudoID", ""), "timePoint": row.get("timePoint", ""), "attention_correct_count": correct, "attention_failed": True, **{c: row.get(c, "") for c in cols}})
    return failures



def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_demo_input_path(input_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    allowed_roots = [
        repo_root / "Data_Handling" / "examples" / "synthetic",
        repo_root / "Data_Handling" / "tests",
    ]
    if not any(is_relative_to(input_path, allowed) for allowed in allowed_roots):
        allowed = ", ".join(str(p.relative_to(repo_root)) for p in allowed_roots)
        raise ValueError(
            "--mode demo uses deterministic pseudoIDs/tokens and must never be used "
            "with real participant data. Use demo mode only with synthetic/test inputs "
            f"under: {allowed}."
        )

def validate_analysis(fields: list[str], config: dict) -> None:
    forbidden = DEFAULT_IDENTIFIER_COLUMNS | set(config.get("direct_identifier_columns", []))
    leaked = sorted(forbidden & set(fields))
    if leaked:
        raise ValueError(f"Forbidden identifier/contact columns remain in analysis output: {', '.join(leaked)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--mode", choices=["demo", "production"], default="production")
    parser.add_argument("--mapping", type=Path, default=Path("Data_Handling/sensitive/survey_mapping_sensitive.csv"))
    parser.add_argument("--participants-output", type=Path, default=Path("Data_Handling/sensitive/survey_participants_import.csv"))
    parser.add_argument("--analysis-output", type=Path, default=Path("Data_Handling/processed/survey_pseudonymized.csv"))
    parser.add_argument("--qc-output", type=Path, default=Path("Data_Handling/qc/attention_check_failures.csv"))
    parser.add_argument("--variable-config", type=Path, default=Path("Data_Handling/config/variable_classification.json"))
    parser.add_argument("--attention-config", type=Path, default=Path("Data_Handling/config/attention_checks.json"))
    parser.add_argument("--attention-min-correct", type=int)
    parser.add_argument("--allow-technical-metadata", action="store_true")
    parser.add_argument("--allow-free-text", action="store_true")
    parser.add_argument("--allow-unknown-columns", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "demo":
        validate_demo_input_path(args.input)

    rows = read_input(args.input)
    make_match_keys(rows)
    var_config = load_json(args.variable_config, {})
    att_config = load_json(args.attention_config, {})
    if args.attention_min_correct is not None:
        att_config["min_correct"] = args.attention_min_correct

    mapping_rows = build_or_update_mapping(rows, load_mapping(args.mapping), args.mode == "demo")
    mapping_by_key = {r["match_key"]: r for r in mapping_rows}

    analysis_rows, analysis_fields, columns_review = build_analysis(rows, mapping_by_key, var_config, args)
    failures = attention_failures(analysis_rows, att_config)
    analysis_fields = analysis_fields + ["attention_correct_count", "attention_failed"]
    validate_analysis(analysis_fields, var_config)

    qc_report_path = Path(args.qc_output).parent / "columns_review_.json"
    qc_report_path.parent.mkdir(parents=True, exist_ok=True)
    with qc_report_path.open("w", encoding="utf-8") as handle:
        json.dump(columns_review, handle, indent=2)

    mapping_fields = ["match_key", "name_key", "email_key", "id", "pseudoID", "token", "firstname", "lastname", "email", "Name", "eMailIG", "eMailKG", "PhoneSystem", "studyGroup", "studyGroup_blind", "attribute_1", "attribute_2", "attribute_3", "attribute_4", "attribute_5", "attribute_6"]
    write_csv(args.mapping, mapping_rows, mapping_fields)
    participants_fields = ["token", "firstname", "lastname", "email", "attribute_1", "attribute_2", "attribute_3", "attribute_4", "attribute_5", "attribute_6"]
    write_csv(args.participants_output, [{k: r.get(k, "") for k in participants_fields} for r in mapping_rows], participants_fields)
    write_csv(args.analysis_output, analysis_rows, analysis_fields)
    qc_fields = ["pseudoID", "timePoint", "attention_correct_count", "attention_failed"] + list(att_config.get("columns", []))
    write_csv(args.qc_output, failures, qc_fields)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
