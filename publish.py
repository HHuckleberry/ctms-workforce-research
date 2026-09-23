#!/usr/bin/env python3
"""Publish the generated CTMS report to the repository's gh-pages branch.

Run ``python3 run.py --no-open`` first so the ignored report artifact contains
the latest OPM data, then run this script. The main branch remains source-only;
the public branch contains just ``index.html`` and ``.nojekyll``.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "report" / "ctms_workforce_report.html"


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

        fetched = run(
            "git", "fetch", "--quiet", "origin", "gh-pages",
            cwd=work, check=False,
        )
        if fetched.returncode == 0:
            run("git", "checkout", "--quiet", "-B", "gh-pages", "FETCH_HEAD", cwd=work)
            run("git", "rm", "-rf", "--quiet", ".", cwd=work, check=False)
        else:
            run("git", "checkout", "--quiet", "--orphan", "gh-pages", cwd=work)

        shutil.copy2(REPORT, work / "index.html")
        (work / ".nojekyll").write_text("", encoding="utf-8")
        run("git", "add", "index.html", ".nojekyll", cwd=work)

        unchanged = run("git", "diff", "--cached", "--quiet", cwd=work, check=False)
        if unchanged.returncode == 0:
            print("Public report is already current; nothing to publish.")
            return

        run("git", "commit", "--quiet", "-m", "Publish CTMS workforce report", cwd=work)
        run("git", "push", "--quiet", "origin", "gh-pages", cwd=work)

    print("Published report to the gh-pages branch.")


if __name__ == "__main__":
    main()
