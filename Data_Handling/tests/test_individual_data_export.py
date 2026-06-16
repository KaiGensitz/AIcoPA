import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_individual_data_export.py"
spec = importlib.util.spec_from_file_location("generate_individual_data_export", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class IndividualDataExportTests(unittest.TestCase):
    def test_exact_email_match(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [
                {"pseudoID": "PID1", "email": "person@example.com", "eMailIG": "", "eMailKG": "", "token": "token-1"},
            ])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID1", "timePoint": "T1", "score": "5"}, {"pseudoID": "PID2", "timePoint": "T1", "score": "3"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "person@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
                "--format", "both",
            ])
            self.assertEqual(result, 0)
            candidates = list(output_dir.glob("request_*_PID1"))
            self.assertEqual(len(candidates), 1)
            package = candidates[0]
            self.assertTrue((package / "participant_data.json").exists())
            self.assertTrue((package / "participant_data.csv").exists())
            manifest = json.loads((package / "export_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["pseudoID"], "PID1")
            self.assertEqual(manifest["number_of_records_exported"], 1)

    def test_case_insensitive_whitespace_email_match(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [{"pseudoID": "PID2", "email": "User@Example.com", "eMailIG": "", "eMailKG": "", "token": "token-2"}])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID2", "timePoint": "T1", "score": "7"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "  user@example.com  ",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
                "--format", "json",
            ])
            self.assertEqual(result, 0)
            package = list(output_dir.glob("request_*_PID2"))[0]
            rows = json.loads((package / "participant_data.json").read_text(encoding="utf-8"))["rows"]
            self.assertEqual(rows[0]["pseudoID"], "PID2")

    def test_no_match_produces_manual_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [{"pseudoID": "PID3", "email": "other@example.com", "eMailIG": "", "eMailKG": "", "token": "token-3"}])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID3", "timePoint": "T1", "score": "8"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "missing@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
                "--format", "both",
            ])
            self.assertEqual(result, 1)
            package = list(output_dir.glob("request_*_manual_review"))[0]
            manifest = json.loads((package / "export_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["match_status"], "no_match")
            self.assertEqual(manifest["number_of_records_exported"], 0)
            self.assertFalse((package / "participant_data.json").exists())

    def test_duplicate_email_requires_manual_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [
                {"pseudoID": "PID4", "email": "dup@example.com", "eMailIG": "", "eMailKG": "", "token": "token-4"},
                {"pseudoID": "PID5", "email": "dup@example.com", "eMailIG": "", "eMailKG": "", "token": "token-5"},
            ])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID4", "timePoint": "T1", "score": "2"}, {"pseudoID": "PID5", "timePoint": "T1", "score": "9"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "dup@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(result, 1)
            package = list(output_dir.glob("request_*_manual_review"))[0]
            manifest = json.loads((package / "export_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["match_status"], "multiple_matches")

    def test_matched_pseudoid_extracts_only_participant_rows(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [
                {"pseudoID": "PID6", "email": "select@example.com", "eMailIG": "", "eMailKG": "", "token": "token-6"},
            ])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [
                {"pseudoID": "PID6", "timePoint": "T1", "score": "1"},
                {"pseudoID": "PID7", "timePoint": "T1", "score": "4"},
            ])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "select@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(result, 0)
            package = list(output_dir.glob("request_*_PID6"))[0]
            with (package / "participant_data.csv").open("r", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["pseudoID"], "PID6")
            self.assertNotIn("email", rows[0])

    def test_include_internal_identifiers_flag_includes_internal_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [{"pseudoID": "PID8", "email": "internal@example.com", "eMailIG": "ig@example.com", "eMailKG": "", "token": "token-8", "firstname": "Test", "lastname": "User"}])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID8", "timePoint": "T1", "score": "10"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "internal@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
                "--include-internal-identifiers",
            ])
            self.assertEqual(result, 0)
            package = list(output_dir.glob("request_*_PID8"))[0]
            row = json.loads((package / "participant_data.json").read_text(encoding="utf-8"))["rows"][0]
            self.assertEqual(row["email"], "internal@example.com")
            self.assertEqual(row["firstname"], "Test")
            self.assertEqual(row["lastname"], "User")

    def test_multiple_processed_files_combined_and_missing_waves_recorded(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [{"pseudoID": "PID9", "email": "multi@example.com", "eMailIG": "", "eMailKG": "", "token": "token-9"}])
            t1 = tmp / "survey_pseudonymized_T1.csv"
            t2 = tmp / "survey_pseudonymized_T2.csv"
            write_csv(t1, [{"pseudoID": "PID9", "timePoint": "T1", "score": "3"}])
            write_csv(t2, [{"pseudoID": "PID10", "timePoint": "T2", "score": "6"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "multi@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(t1), str(t2),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(result, 0)
            package = list(output_dir.glob("request_*_PID9"))[0]
            manifest = json.loads((package / "export_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("T1", manifest["waves_found"])
            self.assertIn("T2", manifest["missing_waves"])
            self.assertEqual(manifest["number_of_records_exported"], 1)

    def test_generated_outputs_are_written_under_sensitive_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "sensitive") as td:
            tmp = Path(td)
            mapping = tmp / "survey_mapping_sensitive.csv"
            write_csv(mapping, [{"pseudoID": "PID10", "email": "safe@example.com", "eMailIG": "", "eMailKG": "", "token": "token-10"}])
            processed = tmp / "survey_pseudonymized_T1.csv"
            write_csv(processed, [{"pseudoID": "PID10", "timePoint": "T1", "score": "9"}])
            output_dir = tmp / "individual_data_requests"
            result = mod.generate_individual_data_export([
                "--request-email", "safe@example.com",
                "--mapping", str(mapping),
                "--processed-files", str(processed),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(result, 0)
            package = list(output_dir.glob("request_*_PID10"))[0]
            self.assertTrue(str(package).startswith(str(tmp)))
            self.assertTrue((package / "export_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
