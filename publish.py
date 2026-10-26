#!/usr/bin/env python3
"""Publish the generated CTMS report to the repository's gh-pages branch.

Run ``python3 run.py --no-open`` first so the ignored report artifact contains
the latest OPM data, then run this script. The main branch remains source-only;
the public branch contains ``index.html``, ``.nojekyll``, and the downloadable
CSVs under ``data/``.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "report" / "ctms_workforce_report.html"
DATA_DIR = ROOT / "report" / "data"


def run(*args: str, cwd: Path, check: bool = True, capture: bool = False):
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
    )


def main():
    if not REPORT.exists():
        sys.exit("Generated report is missing. Run: python3 run.py --no-open")

    remote = run(
        "git", "remote", "get-url", "origin", cwd=ROOT, capture=True
    ).stdout.strip()
    if not remote:
        sys.exit("No Git origin remote is configured.")

    with tempfile.TemporaryDirectory(prefix="ctms-pages-") as temp:
        work = Path(temp)
        run("git", "init", "--quiet", cwd=work)
        run("git", "remote", "add", "origin", remote, cwd=work)
        # The temp repo would otherwise fall back to the global git identity;
        # reuse this repo's (e.g. a repo-local GitHub noreply email) instead.
        for key in ("user.name", "user.email"):
            value = run("git", "config", key, cwd=ROOT, check=False, capture=True).stdout.strip()
            if value:
                run("git", "config", key, value, cwd=work)

        fetched = run(
            "git", "fetch", "--quiet", "origin", "gh-pages",
            cwd=work, check=False, capture=True,
        )
        if fetched.returncode == 0:
            run("git", "checkout", "--quiet", "-B", "gh-pages", "FETCH_HEAD", cwd=work)
            run("git", "rm", "-rf", "--quiet", ".", cwd=work, check=False)
        else:
            run("git", "checkout", "--quiet", "--orphan", "gh-pages", cwd=work)

        shutil.copy2(REPORT, work / "index.html")
        (work / ".nojekyll").write_text("", encoding="utf-8")
        to_add = ["index.html", ".nojekyll"]
        if DATA_DIR.is_dir() and any(DATA_DIR.iterdir()):
            shutil.copytree(DATA_DIR, work / "data")
            to_add.append("data")
        else:
            print("Warning: report/data/ is empty - the download links will 404. Run run.py first.")
        run("git", "add", *to_add, cwd=work)

        unchanged = run("git", "diff", "--cached", "--quiet", cwd=work, check=False)
        if unchanged.returncode == 0:
            print("Public report is already current; nothing to publish.")
            return

        run("git", "commit", "--quiet", "-m", "Publish CTMS workforce report", cwd=work)
        run("git", "push", "--quiet", "origin", "gh-pages", cwd=work)

    print("Published report to the gh-pages branch.")


if __name__ == "__main__":
    main()
