#!/usr/bin/env python3
"""
One-command setup for the CTMS/OPM workforce report.

Usage:
    python3 run.py

What this does:
    1. Creates a local virtual environment (.venv/) if one doesn't exist yet
    2. Installs the three dependencies into it (requests, pandas, pyarrow)
    3. Runs the pipeline, in order:
         pull/opm_ctms_pull.py          pulls raw OPM data since CTMS's actual
                                         inception (June 2022) - ~150 monthly
                                         snapshot downloads from data.opm.gov
         pull/ctms_vs_2210.py           pulls the comparison series (2210) at
                                         the same components, for the report's
                                         "vs. the standard track" chart
         pull/ctms_track_individuals.py reconstructs individual timelines from
                                         the de-identified monthly snapshots
         pull/ctms_report_data.py       builds the consolidated JSON the report
                                         reads
    4. Injects that JSON into report/template.html and writes
       report/ctms_workforce_report.html
    5. Opens the finished report in your default browser

No API key or account is needed anywhere in this - data.opm.gov's open data
API is public with no authentication. The first pull takes roughly 15-20
minutes. Later runs download only newly published months and rebuild all
derived outputs from the cached local extracts. Pass --full-refresh to
intentionally replace the cache with a complete historical re-pull.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
PULL_DIR = ROOT / "pull"
REPORT_DIR = ROOT / "report"

PIPELINE = ["opm_ctms_pull.py", "ctms_vs_2210.py", "ctms_track_individuals.py", "ctms_report_data.py"]


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def step(msg: str):
    print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}", flush=True)


def ensure_venv():
    if venv_python().exists():
        step("Using existing virtual environment (.venv/)")
        return
    step("Creating virtual environment (.venv/) ...")
    venv.EnvBuilder(with_pip=True).create(VENV_DIR)


def ensure_deps():
    check = subprocess.run(
        [str(venv_python()), "-c", "import requests, pandas, pyarrow"],
        capture_output=True,
    )
    if check.returncode == 0:
        step("Dependencies already installed")
        return
    step("Installing dependencies (requests, pandas, pyarrow) ...")
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
        check=True,
    )


def run_pipeline_script(name: str, *args: str):
    step(f"Running {name} ...")
    subprocess.run(
        [str(venv_python()), str(PULL_DIR / name), *args],
        check=True,
        cwd=str(PULL_DIR),
    )


def assemble_template() -> str:
    """Inline report sources in explicit template order, preserving whitespace."""
    root = REPORT_DIR.resolve()
    directive = re.compile(r'\{\{ include "([^"\n]+)" \}\}(?:\r?\n)?')

    def expand(path, stack=()):
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Report include is outside report directory: {path}")
        if path in stack:
            raise ValueError(f"Circular report include: {path}")
        source = path.read_text(encoding="utf-8")
        return directive.sub(
            lambda match: expand(root / match[1], (*stack, path)), source
        )

    return expand(root / "template.html")


def build_report() -> Path:
    step("Building report/ctms_workforce_report.html ...")
    with open(PULL_DIR / "ctms_report_data.json", encoding="utf-8") as f:
        data = json.load(f)
    data_str = json.dumps(data)
    template = assemble_template()
    if "__DATA_JSON__" not in template:
        sys.exit("report/template.html is missing the __DATA_JSON__ placeholder - can't inject data.")
    out = template.replace("__DATA_JSON__", data_str, 1)
    out_path = REPORT_DIR / "ctms_workforce_report.html"
    out_path.write_text(out, encoding="utf-8")
    return out_path


def parse_args():
    parser = argparse.ArgumentParser(description="Update and build the CTMS workforce report.")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="assemble the report from existing report JSON without downloads or dependency setup",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="download every available OPM month again instead of only new months",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do not open the finished report in a browser (useful for scheduled runs)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.build_only and args.full_refresh:
        sys.exit("--build-only and --full-refresh cannot be used together.")
    if not args.build_only:
        ensure_venv()
        ensure_deps()
        pull_args = ("--full-refresh",) if args.full_refresh else ()
        run_pipeline_script("opm_ctms_pull.py", *pull_args)
        run_pipeline_script("ctms_vs_2210.py", *pull_args)
        for script in PIPELINE[2:]:
            run_pipeline_script(script)
    out_path = build_report()
    if args.no_open:
        step(f"Done. Built {out_path.name}")
    else:
        step(f"Done. Opening {out_path.name} in your browser ...")
        webbrowser.open(out_path.as_uri())
    print(f"\nReport saved at: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\nA step failed (exit code {e.returncode}). See the output above for details.", file=sys.stderr)
        sys.exit(1)
