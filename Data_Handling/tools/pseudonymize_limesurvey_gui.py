#!/usr/bin/env python3
"""Simple GUI wrapper to run the existing pseudonymize_limesurvey.py script.

This GUI does not change the script behavior; it only assembles command-line
arguments and runs the script as a subprocess, showing stdout/stderr.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "pseudonymize_limesurvey.py"


def choose_file(entry: tk.Entry, filetypes=("CSV files", "*.csv")) -> None:
    path = filedialog.askopenfilename(title="Select file", filetypes=[(filetypes[0], filetypes[1]), ("All files", "*")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def choose_save(entry: tk.Entry, default_ext=".csv") -> None:
    path = filedialog.asksaveasfilename(title="Select output file", defaultextension=default_ext, filetypes=[("CSV files", "*.csv"), ("All files", "*")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def run_pseudonymize(args, output_box: scrolledtext.ScrolledText) -> None:
    try:
        result = subprocess.run(args, capture_output=True, text=True)
    except Exception as exc:
        messagebox.showerror("Execution failed", f"Could not run script: {exc}")
        return
    output_box.configure(state=tk.NORMAL)
    output_box.delete("1.0", tk.END)
    if result.stdout:
        output_box.insert(tk.END, result.stdout + "\n")
    if result.stderr:
        output_box.insert(tk.END, "STDERR:\n" + result.stderr + "\n")
    output_box.insert(tk.END, f"Exit code: {result.returncode}\n")
    output_box.configure(state=tk.DISABLED)
    if result.returncode == 0:
        messagebox.showinfo("Done", "Pseudonymization script finished successfully.")
    else:
        messagebox.showwarning("Finished with errors", "Script finished with non-zero exit code. See output for details.")


def build_ui() -> None:
    root = tk.Tk()
    root.title("Pseudonymize LimeSurvey GUI")
    root.geometry("900x700")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1)

    def row_label(text, r):
        tk.Label(frame, text=text).grid(row=r, column=0, sticky="w", pady=4)

    # Input file
    input_entry = tk.Entry(frame)
    input_entry.grid(row=0, column=1, sticky="ew")
    tk.Button(frame, text="Select input (csv/xlsx)", command=lambda: choose_file(input_entry, ("CSV/XLSX", "*.csv;*.xlsx"))).grid(row=0, column=2, padx=6)
    row_label("Input file:", 0)

    # Wave
    wave_entry = tk.Entry(frame)
    wave_entry.grid(row=1, column=1, sticky="ew")
    row_label("Wave (e.g., T1):", 1)

    # Mode
    mode_var = tk.StringVar(value="production")
    tk.Label(frame, text="Mode:").grid(row=2, column=0, sticky="w")
    tk.OptionMenu(frame, mode_var, "production", "demo").grid(row=2, column=1, sticky="w")

    # Mapping
    mapping_entry = tk.Entry(frame)
    mapping_entry.grid(row=3, column=1, sticky="ew")
    tk.Button(frame, text="Select mapping CSV", command=lambda: choose_file(mapping_entry, ("CSV files", "*.csv"))).grid(row=3, column=2, padx=6)
    row_label("Mapping file:", 3)

    # Participants output
    participants_entry = tk.Entry(frame)
    participants_entry.grid(row=4, column=1, sticky="ew")
    tk.Button(frame, text="Select participants output", command=lambda: choose_save(participants_entry)).grid(row=4, column=2, padx=6)
    row_label("Participants output:", 4)

    # Analysis output
    analysis_entry = tk.Entry(frame)
    analysis_entry.grid(row=5, column=1, sticky="ew")
    tk.Button(frame, text="Select analysis output", command=lambda: choose_save(analysis_entry)).grid(row=5, column=2, padx=6)
    row_label("Analysis output:", 5)

    # QC output
    qc_entry = tk.Entry(frame)
    qc_entry.grid(row=6, column=1, sticky="ew")
    tk.Button(frame, text="Select QC output", command=lambda: choose_save(qc_entry)).grid(row=6, column=2, padx=6)
    row_label("QC output:", 6)

    # Variable and attention config
    varconf_entry = tk.Entry(frame)
    varconf_entry.grid(row=7, column=1, sticky="ew")
    tk.Button(frame, text="Select variable config", command=lambda: choose_file(varconf_entry, ("JSON files", "*.json"))).grid(row=7, column=2, padx=6)
    row_label("Variable config (optional):", 7)

    attconf_entry = tk.Entry(frame)
    attconf_entry.grid(row=8, column=1, sticky="ew")
    tk.Button(frame, text="Select attention config", command=lambda: choose_file(attconf_entry, ("JSON files", "*.json"))).grid(row=8, column=2, padx=6)
    row_label("Attention config (optional):", 8)

    # Flags
    allow_technical = tk.BooleanVar(value=False)
    allow_free = tk.BooleanVar(value=False)
    allow_unknown = tk.BooleanVar(value=False)
    allow_malformed_demo = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Allow technical metadata", variable=allow_technical).grid(row=9, column=1, sticky="w")
    tk.Checkbutton(frame, text="Allow free text", variable=allow_free).grid(row=10, column=1, sticky="w")
    tk.Checkbutton(frame, text="Allow unknown columns", variable=allow_unknown).grid(row=11, column=1, sticky="w")
    tk.Checkbutton(frame, text="Allow malformed demo CSV (demo only)", variable=allow_malformed_demo).grid(row=12, column=1, sticky="w")

    # Attention min
    attmin_entry = tk.Entry(frame, width=8)
    attmin_entry.grid(row=13, column=1, sticky="w")
    row_label("Attention min correct (optional):", 13)

    # Run button and output box
    output_box = scrolledtext.ScrolledText(frame, height=20, state=tk.DISABLED)
    output_box.grid(row=15, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
    frame.rowconfigure(15, weight=1)

    def submit() -> None:
        input_path = input_entry.get().strip()
        wave = wave_entry.get().strip()
        mode = mode_var.get()
        mapping = mapping_entry.get().strip()
        participants = participants_entry.get().strip()
        analysis = analysis_entry.get().strip()
        qc = qc_entry.get().strip()
        varconf = varconf_entry.get().strip()
        attconf = attconf_entry.get().strip()
        args = [sys.executable, str(SCRIPT_PATH), "--input", input_path, "--wave", wave, "--mode", mode, "--mapping", mapping, "--participants-output", participants, "--analysis-output", analysis, "--qc-output", qc]
        if varconf:
            args.extend(["--variable-config", varconf])
        if attconf:
            args.extend(["--attention-config", attconf])
        if attmin_entry.get().strip():
            args.extend(["--attention-min-correct", attmin_entry.get().strip()])
        if allow_technical.get():
            args.append("--allow-technical-metadata")
        if allow_free.get():
            args.append("--allow-free-text")
        if allow_unknown.get():
            args.append("--allow-unknown-columns")
        if allow_malformed_demo.get():
            args.append("--allow-malformed-demo-csv")

        # Basic validation
        if not input_path or not wave or not mapping or not participants or not analysis or not qc:
            messagebox.showerror("Missing fields", "Please provide input, wave, mapping, participants, analysis and qc output paths.")
            return
        output_box.configure(state=tk.NORMAL)
        output_box.delete("1.0", tk.END)
        output_box.insert(tk.END, f"Running: {' '.join(args)}\n\n")
        output_box.configure(state=tk.DISABLED)
        root.update()
        run_pseudonymize(args, output_box)

    tk.Button(frame, text="Run pseudonymize", command=submit, bg="#4CAF50", fg="white").grid(row=14, column=0, columnspan=3, sticky="ew", pady=8)

    root.mainloop()


if __name__ == "__main__":
    build_ui()
