#!/usr/bin/env python3
"""Generate an individual participant data export package from mapping and processed files.

This tool is for internal study operations only. Requester emails are matched only
against the sensitive mapping file, and no automatic email sending is performed.
The generated export package must be reviewed manually before any data are sent.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MATCH_FIELDS = ["email", "eMailIG", "eMailKG", "email_key"]
INTERNAL_FIELDS = {
    "token",
    "name",
    "Name",
    "firstname",
    "lastname",
    "email",
    "eMailIG",
    "eMailKG",
    "match_key",
    "name_key",
    "email_key",
    "refurl",
    "id",
}


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def normalize_string(value: str | None) -> str:
    return (value or "").strip()


def parse_waves_from_filename(path: Path) -> list[str]:
    text = path.name
    waves = []
    for candidate in re.findall(r"(?<![A-Za-z0-9])(T[123])(?=$|[^A-Za-z0-9])", text, flags=re.IGNORECASE):
        waves.append(candidate.upper())
    return sorted(dict.fromkeys(waves))


def extract_wave(row: dict[str, str], path: Path) -> str | None:
    for field in ("timePoint", "timepoint", "wave", "survey", "surveyWave"):
        if value := normalize_string(row.get(field)):
            return value
    candidates = parse_waves_from_filename(path)
    return candidates[0] if candidates else None


def load_mapping(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    return read_csv(path)


def find_email_matches(rows: list[dict[str, str]], request_email: str) -> list[tuple[dict[str, str], list[str]]]:
    normalized = normalize_email(request_email)
    if not normalized:
        raise ValueError("Request email must be provided.")
    matches: list[tuple[dict[str, str], list[str]]] = []
    for row in rows:
        matched_fields = [field for field in MATCH_FIELDS if normalize_email(row.get(field)) == normalized]
        if matched_fields:
            matches.append((row, matched_fields))
    return matches


def filter_internal_fields(row: dict[str, str], include_internal: bool) -> dict[str, str]:
    if include_internal:
        return dict(row)
    return {k: v for k, v in row.items() if k not in INTERNAL_FIELDS}


def validate_output_dir(output_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sensitive_root = repo_root / "Data_Handling" / "sensitive"
    resolved_dir = output_dir.resolve()
    if resolved_dir.exists():
        resolved_dir = resolved_dir.resolve()
    if output_dir.is_absolute() and is_relative_to(resolved_dir, repo_root) and not is_relative_to(resolved_dir, sensitive_root):
        raise ValueError(
            "Output directory inside repository must be under Data_Handling/sensitive "
            "to ensure generated exports remain in ignored sensitive paths."
        )
    if not output_dir.is_absolute() and is_relative_to((repo_root / output_dir).resolve(), repo_root) and not is_relative_to((repo_root / output_dir).resolve(), sensitive_root):
        raise ValueError(
            "Output directory inside repository must be under Data_Handling/sensitive "
            "to ensure generated exports remain in ignored sensitive paths."
        )


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def collect_processed_rows(processed_files: list[Path], pseudo_id: str) -> tuple[list[dict[str, str]], list[str], list[str]]:
    rows: list[dict[str, str]] = []
    found_waves: list[str] = []
    expected_waves: list[str] = []
    for path in processed_files:
        if not path.exists():
            raise FileNotFoundError(f"Processed file not found: {path}")
        file_rows = read_csv(path)
        expected_waves.extend(parse_waves_from_filename(path))
        for row in file_rows:
            if row.get("pseudoID") == pseudo_id:
                rows.append(dict(row))
                wave = extract_wave(row, path)
                if wave and wave not in found_waves:
                    found_waves.append(wave)
    return rows, found_waves, sorted(dict.fromkeys(expected_waves))


def merge_internal_mapping_fields(row: dict[str, str], mapping_row: dict[str, str], include_internal: bool) -> dict[str, str]:
    merged = dict(row)
    if include_internal:
        for field in INTERNAL_FIELDS:
            if field in mapping_row:
                merged[field] = mapping_row[field]
    return merged


def build_manifest(
    request_email: str,
    request_id: str | None,
    pseudo_id: str | None,
    matched_mapping_fields: list[str],
    processed_files: list[Path],
    number_of_records: int,
    waves_found: list[str],
    expected_waves: list[str],
    include_internal_identifiers: bool,
    notes: str | None,
    match_status: str,
) -> dict[str, object]:
    missing_waves = [wave for wave in expected_waves if wave not in waves_found]
    manifest = {
        "request_email_normalized": normalize_email(request_email),
        "request_id": request_id or "",
        "pseudoID": pseudo_id or "",
        "matched_mapping_fields": matched_mapping_fields,
        "processed_files_checked": [str(path) for path in processed_files],
        "number_of_records_exported": number_of_records,
        "waves_found": waves_found,
        "missing_waves": missing_waves,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "manual_review_required": True,
        "automatic_email_sending": False,
        "internal_review_only": bool(include_internal_identifiers),
        "match_status": match_status,
        "notes": notes or "",
    }
    return manifest


def safe_directory_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", name)


def write_readme(path: Path, status: str, additional_text: str) -> None:
    text = (
        "This export package was generated for an internal individual participant data request.\n"
        "Requester identity must be verified manually before any data are sent to the requester.\n"
        "The request email is matched only against the sensitive mapping file, not processed analysis files.\n"
        "No automatic email sending is performed.\n\n"
        f"Status: {status}\n"
        f"{additional_text}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_export_files(
    output_dir: Path,
    include_json: bool,
    include_csv: bool,
    participant_rows: list[dict[str, str]],
    manifest: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "export_manifest.json", manifest)
    write_readme(
        output_dir / "README_for_manual_review.txt",
        status="Data export package generated",
        additional_text="Review the manifest and exported participant data before any external disclosure.",
    )
    if include_json:
        write_json(output_dir / "participant_data.json", {"rows": participant_rows})
    if include_csv:
        fieldnames: list[str] = []
        for row in participant_rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        write_csv(output_dir / "participant_data.csv", participant_rows, fieldnames)


def generate_individual_data_export(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a reviewable export package for an individual participant data request.")
    parser.add_argument("--request-email", required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--processed-files", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-internal-identifiers", action="store_true")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--request-id")
    parser.add_argument("--notes")
    args = parser.parse_args(argv)

    validate_output_dir(args.output_dir)
    mapping_rows = load_mapping(args.mapping)
    matches = find_email_matches(mapping_rows, args.request_email)
    if len(matches) != 1:
        status = "no_match" if not matches else "multiple_matches"
        output_subdir = args.output_dir / f"request_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_manual_review"
        manifest = build_manifest(
            request_email=args.request_email,
            request_id=args.request_id,
            pseudo_id=None,
            matched_mapping_fields=[],
            processed_files=args.processed_files,
            number_of_records=0,
            waves_found=[],
            expected_waves=[],
            include_internal_identifiers=args.include_internal_identifiers,
            notes=args.notes,
            match_status=status,
        )
        write_export_files(output_subdir, include_json=False, include_csv=False, participant_rows=[], manifest=manifest)
        write_readme(
            output_subdir / "README_for_manual_review.txt",
            status="Manual review required",
            additional_text=(
                "No exact email match was found in the mapping file. "
                if status == "no_match" else
                "Multiple exact email matches were found in the mapping file. "
                "This requires manual review before any data export."
            ),
        )
        return 1

    matched_row, matched_fields = matches[0]
    pseudo_id = matched_row.get("pseudoID", "")
    if not pseudo_id:
        raise ValueError("Matched mapping row does not contain a pseudoID.")

    participant_rows, waves_found, expected_waves = collect_processed_rows(args.processed_files, pseudo_id)
    merged_rows = [merge_internal_mapping_fields(row, matched_row, args.include_internal_identifiers) for row in participant_rows]
    filtered_rows = [filter_internal_fields(row, args.include_internal_identifiers) for row in merged_rows]
    manifest = build_manifest(
        request_email=args.request_email,
        request_id=args.request_id,
        pseudo_id=pseudo_id,
        matched_mapping_fields=matched_fields,
        processed_files=args.processed_files,
        number_of_records=len(filtered_rows),
        waves_found=waves_found,
        expected_waves=expected_waves,
        include_internal_identifiers=args.include_internal_identifiers,
        notes=args.notes,
        match_status="matched",
    )
    output_subdir = args.output_dir / f"request_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{safe_directory_name(pseudo_id)}"
    write_export_files(
        output_subdir,
        include_json=args.format in {"json", "both"},
        include_csv=args.format in {"csv", "both"},
        participant_rows=filtered_rows,
        manifest=manifest,
    )
    print(f"Generated individual data export package at: {output_subdir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return generate_individual_data_export(argv)


if __name__ == "__main__":
    raise SystemExit(main())
