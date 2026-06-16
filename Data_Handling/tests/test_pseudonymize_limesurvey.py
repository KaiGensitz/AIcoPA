import csv
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pseudonymize_limesurvey.py"
spec = importlib.util.spec_from_file_location("pseudonymize_limesurvey", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class PseudonymizationPrivacyTests(unittest.TestCase):
    def run_pipeline(self, tmp, input_path, wave="T1", extra_args=None):
        args = [
            "--mode", "demo",
            "--wave", wave,
            "--input", str(input_path),
            "--mapping", str(tmp / "sensitive" / "mapping.csv"),
            "--participants-output", str(tmp / "sensitive" / "participants.csv"),
            "--analysis-output", str(tmp / "processed" / f"analysis_{wave}.csv"),
            "--qc-output", str(tmp / "qc" / f"attention_{wave}.csv"),
            "--variable-config", str(ROOT / "config" / "variable_classification.json"),
            "--attention-config", str(ROOT / "config" / "attention_checks.json"),
        ]
        if extra_args:
            args.extend(extra_args)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            mod.main(args)
        return stderr.getvalue()


    def test_root_gitignore_blocks_sensitive_generated_patterns(self):
        repo_root = ROOT.parent
        ignored = [
            "results-survey999999.xlsx",
            "results-survey999999.csv",
            "survey_mapping_sensitive.csv",
            "survey_participants_import.csv",
            "survey_pseudonymized_T1.csv",
            "attention_check_failures_T1.csv",
        ]
        for path in ignored:
            result = subprocess.run(["git", "check-ignore", "-q", path], cwd=repo_root)
            self.assertEqual(result.returncode, 0, path)

    def test_demo_mode_rejected_outside_synthetic_or_tests_paths(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            input_path = tmp / "looks_real.csv"
            input_path.write_text((ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv").read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "demo uses deterministic pseudoIDs/tokens"):
                self.run_pipeline(tmp, input_path, "T1")

    def test_production_unknown_columns_fail_without_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args = [
                "--mode", "production", "--wave", "T1",
                "--input", str(ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv"),
                "--mapping", str(tmp / "sensitive" / "mapping.csv"),
                "--participants-output", str(tmp / "sensitive" / "participants.csv"),
                "--analysis-output", str(tmp / "processed" / "analysis.csv"),
                "--qc-output", str(tmp / "qc" / "attention.csv"),
                "--variable-config", str(ROOT / "config" / "variable_classification.json"),
                "--attention-config", str(ROOT / "config" / "attention_checks.json"),
            ]
            with self.assertRaisesRegex(ValueError, "Unknown/unclassified columns found in production mode"):
                mod.main(args)

    def test_production_unknown_columns_allowed_only_with_explicit_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args = [
                "--mode", "production", "--wave", "T1",
                "--input", str(ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv"),
                "--mapping", str(tmp / "sensitive" / "mapping.csv"),
                "--participants-output", str(tmp / "sensitive" / "participants.csv"),
                "--analysis-output", str(tmp / "processed" / "analysis.csv"),
                "--qc-output", str(tmp / "qc" / "attention.csv"),
                "--variable-config", str(ROOT / "config" / "variable_classification.json"),
                "--attention-config", str(ROOT / "config" / "attention_checks.json"),
                "--allow-unknown-columns",
            ]
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                mod.main(args)
            self.assertIn("SomeNewColumn", stderr.getvalue())
            self.assertTrue((tmp / "processed" / "analysis.csv").exists())

    def test_production_mode_does_not_use_deterministic_demo_ids(self):
        pseudo_ids = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                args = [
                    "--mode", "production", "--wave", "T1",
                    "--input", str(ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv"),
                    "--mapping", str(tmp / "sensitive" / "mapping.csv"),
                    "--participants-output", str(tmp / "sensitive" / "participants.csv"),
                    "--analysis-output", str(tmp / "processed" / "analysis.csv"),
                    "--qc-output", str(tmp / "qc" / "attention.csv"),
                    "--variable-config", str(ROOT / "config" / "variable_classification.json"),
                    "--attention-config", str(ROOT / "config" / "attention_checks.json"),
                    "--allow-unknown-columns",
                ]
                mod.main(args)
                pseudo_ids.append([r["pseudoID"] for r in read_rows(tmp / "sensitive" / "mapping.csv")])
        self.assertNotEqual(pseudo_ids[0], pseudo_ids[1])

    def test_validation_fails_if_forbidden_identifier_is_in_analysis_fields(self):
        with self.assertRaisesRegex(ValueError, "token"):
            mod.validate_analysis(["pseudoID", "token"], {})

    def test_longitudinal_linkage_and_privacy_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self.run_pipeline(tmp, ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv", "T1")
            self.run_pipeline(tmp, ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T2.csv", "T2")
            mapping = read_rows(tmp / "sensitive" / "mapping.csv")
            alex = [r for r in mapping if r["email"] == "alex@example.test"]
            self.assertEqual(len(alex), 1)
            self.assertNotEqual(alex[0]["pseudoID"], alex[0]["token"])

            analysis = read_rows(tmp / "processed" / "analysis_T2.csv")
            self.assertEqual(analysis[0]["pseudoID"], alex[0]["pseudoID"])
            forbidden = {"token", "Name", "firstname", "lastname", "email", "eMailIG", "eMailKG", "PhoneSystem", "match_key", "name_key", "email_key", "refurl", "submitdate", "startdate", "datestamp", "NameTime", "QualPos"}
            self.assertTrue(forbidden.isdisjoint(analysis[0].keys()))
            self.assertIn("email", read_rows(tmp / "sensitive" / "participants.csv")[0])

    def test_unknown_columns_warn_and_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            warning = self.run_pipeline(tmp, ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv", "T1")
            self.assertIn("SomeNewColumn", warning)
            analysis = read_rows(tmp / "processed" / "analysis_T1.csv")
            self.assertNotIn("SomeNewColumn", analysis[0])

    def test_attention_threshold_supports_two_of_three(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            attention = tmp / "attention_2of3.json"
            attention.write_text(json.dumps({"columns": ["ACheck1[ACheck1]", "KIM[ACheck2]", "ACheck3[ACheck3]"], "correct_prefix": "3", "min_correct": 2}), encoding="utf-8")
            args = [
                "--mode", "demo", "--wave", "T1",
                "--input", str(ROOT / "examples" / "synthetic" / "raw" / "synthetic_results-survey_T1.csv"),
                "--mapping", str(tmp / "sensitive" / "mapping.csv"),
                "--participants-output", str(tmp / "sensitive" / "participants.csv"),
                "--analysis-output", str(tmp / "processed" / "analysis.csv"),
                "--qc-output", str(tmp / "qc" / "attention.csv"),
                "--variable-config", str(ROOT / "config" / "variable_classification.json"),
                "--attention-config", str(attention),
            ]
            mod.main(args)
            rows = read_rows(tmp / "processed" / "analysis.csv")
            self.assertEqual([r["attention_failed"] for r in rows], ["False", "False"])
            mod.main(args + ["--attention-min-correct", "3"])
            rows = read_rows(tmp / "processed" / "analysis.csv")
            self.assertEqual([r["attention_failed"] for r in rows], ["False", "True"])

if __name__ == "__main__":
    unittest.main()
