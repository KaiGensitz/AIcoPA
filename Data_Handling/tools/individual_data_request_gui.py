#!/usr/bin/env python3
"""Simple local GUI for generating individual participant data exports."""
from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "generate_individual_data_export.py"


def choose_mapping(entry: tk.Entry) -> None:
    path = filedialog.askopenfilename(title="Select sensitive mapping CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def choose_processed_files(entry: tk.Entry) -> None:
    paths = filedialog.askopenfilenames(title="Select processed CSV files", filetypes=[("CSV files", "*.csv"), ("All files", "*")])
    if paths:
        entry.delete(0, tk.END)
        entry.insert(0, ";".join(paths))


def choose_output_dir(entry: tk.Entry) -> None:
    path = filedialog.askdirectory(title="Select output directory")
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def run_export(mapping_path: str, processed_paths: str, request_email: str, output_dir: str, include_internal: bool, fmt: str, request_id: str, notes: str, status_label: tk.Label) -> None:
    if not mapping_path or not processed_paths or not request_email or not output_dir:
        messagebox.showerror("Missing information", "Please provide mapping, processed files, requester email, and output directory.")
        return

    cmd = [sys.executable, str(SCRIPT_PATH), "--request-email", request_email, "--mapping", mapping_path, "--output-dir", output_dir, "--format", fmt]
    if include_internal:
        cmd.append("--include-internal-identifiers")
    if request_id:
        cmd.extend(["--request-id", request_id])
    if notes:
        cmd.extend(["--notes", notes])
    for path in processed_paths.split(";"):
        if path.strip():
            cmd.extend(["--processed-files", path.strip()])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as exc:
        messagebox.showerror("Execution failed", f"Could not run export script: {exc}")
        return

    if result.returncode == 0:
        status_label.config(text="Export generated successfully. See console output for location.", fg="green")
    else:
        status_label.config(text="Manual review required or error occurred. See console output.", fg="red")
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)


def build_ui() -> None:
    root = tk.Tk()
    root.title("Individual Data Request Export")
    root.geometry("760x420")

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack(fill=tk.BOTH, expand=True)

    def labelled_row(label_text: str, widget: tk.Widget, row: int) -> None:
        tk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w", pady=4)
        widget.grid(row=row, column=1, sticky="ew", pady=4)

    frame.columnconfigure(1, weight=1)

    mapping_entry = tk.Entry(frame)
    choose_mapping_btn = tk.Button(frame, text="Select mapping CSV", command=lambda: choose_mapping(mapping_entry))
    mapping_entry.grid(row=0, column=1, sticky="ew")
    choose_mapping_btn.grid(row=0, column=2, padx=8)
    tk.Label(frame, text="Mapping CSV:").grid(row=0, column=0, sticky="w", pady=4)

    processed_entry = tk.Entry(frame)
    choose_processed_btn = tk.Button(frame, text="Select processed files", command=lambda: choose_processed_files(processed_entry))
    processed_entry.grid(row=1, column=1, sticky="ew")
    choose_processed_btn.grid(row=1, column=2, padx=8)
    tk.Label(frame, text="Processed files:").grid(row=1, column=0, sticky="w", pady=4)

    email_entry = tk.Entry(frame)
    labelled_row("Requester email:", email_entry, 2)

    output_entry = tk.Entry(frame)
    choose_output_btn = tk.Button(frame, text="Select output dir", command=lambda: choose_output_dir(output_entry))
    output_entry.grid(row=3, column=1, sticky="ew")
    choose_output_btn.grid(row=3, column=2, padx=8)
    tk.Label(frame, text="Output directory:").grid(row=3, column=0, sticky="w", pady=4)

    include_internal = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Include internal identifiers", variable=include_internal).grid(row=4, column=1, sticky="w", pady=4)

    format_var = tk.StringVar(value="both")
    tk.Label(frame, text="Output format:").grid(row=5, column=0, sticky="w", pady=4)
    tk.OptionMenu(frame, format_var, "json", "csv", "both").grid(row=5, column=1, sticky="w", pady=4)

    request_id_entry = tk.Entry(frame)
    labelled_row("Request ID (optional):", request_id_entry, 6)

    notes_entry = tk.Entry(frame)
    labelled_row("Notes (optional):", notes_entry, 7)

    status_label = tk.Label(frame, text="", anchor="w")
    status_label.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def submit() -> None:
        run_export(
            mapping_path=mapping_entry.get(),
            processed_paths=processed_entry.get(),
            request_email=email_entry.get(),
            output_dir=output_entry.get(),
            include_internal=include_internal.get(),
            fmt=format_var.get(),
            request_id=request_id_entry.get(),
            notes=notes_entry.get(),
            status_label=status_label,
        )

    tk.Button(frame, text="Generate export", command=submit, bg="#4CAF50", fg="white").grid(row=8, column=0, columnspan=3, sticky="ew", pady=10)

    root.mainloop()


if __name__ == "__main__":
    build_ui()
