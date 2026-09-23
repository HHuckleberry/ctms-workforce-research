#!/usr/bin/env python3
"""
CTMS pull — incrementally downloads newly available OPM snapshots.

Population: pay plan DC or DL intersected with the DHS-only cybersecurity
occupational-series family (2212/2213/2218/2221/2224/2225/2226/2228/2229/2230).
Keeps every column, plus the accessions and separations files.

The pull manifest records successfully retrieved months, including months
with zero matching rows. Normal runs append only newly published months;
--full-refresh intentionally downloads and replaces the complete history.

Every new raw snapshot audits all DC/DL rows by occupational series and emits
a warning if another series appears, so future coding changes remain visible.

Run:
    python3 -m venv ~/.venvs/opm
    ~/.venvs/opm/bin/pip install requests pandas pyarrow
    ~/.venvs/opm/bin/python opm_ctms_pull.py

Outputs, in this script's folder:
    ctms_full.csv          every CTMS employment record, all columns, all snapshots
    ctms_accessions.csv    people joining CTMS
    ctms_separations.csv   people leaving CTMS, with separation type
    ctms_schema.txt         column names/types + DHS pay-plan census (diagnostic)
    ctms_salary_moves.csv  median/mean salary by pay plan, per snapshot
    pull_manifest.txt      run date + which snapshots were actually retrieved
"""

import argparse
import io
import os
import sys
from datetime import datetime, timezone

try:
    import requests
    import pandas as pd
except ImportError:
    sys.exit(
        "Missing deps (PEP 668 blocks system pip on Debian-based distros):\n"
        "  python3 -m venv ~/.venvs/opm\n"
        "  ~/.venvs/opm/bin/pip install requests pandas pyarrow\n"
        "  ~/.venvs/opm/bin/python " + os.path.abspath(__file__)
    )

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://data.opm.gov"
PLANS = {"DC", "DL"}
SERIES = {"2212", "2213", "2218", "2221", "2224", "2225", "2226", "2228", "2229", "2230"}
EARLIEST = ("2022", "06")  # first month CTMS appears at all - confirmed by probe


def list_snapshots(dataset):
    """Current (year, month, version) OPM has published for this dataset, >= EARLIEST.

    ?current=true returns exactly one (the latest) version per month. Without it,
    the API returns every historical version ever published for each month, which
    silently multiplies download counts for no benefit (same data, different version
    numbers as OPM corrects earlier files in place).
    """
    r = requests.get(f"{BASE}/api/v1/files/{dataset}?current=true", timeout=120)
    r.raise_for_status()
    listing = r.json()
    by_month = {}
    for f in listing:
        key = (f["year"], f["month"])
        if key < EARLIEST:
            continue
        if key not in by_month or f["version"] > by_month[key]:
            by_month[key] = f["version"]
    return sorted((y, m, v) for (y, m), v in by_month.items())


def get_parquet(dataset, year, month, version):
    for p in (f"/api/v1/files/{dataset}/{year}/{month}/{version}/download",
              f"/v1/files/{dataset}/{year}/{month}/{version}/download"):
        try:
            r = requests.get(BASE + p, timeout=900)
        except requests.RequestException as e:
            print(f"    {p}: {e}")
            continue
        if r.status_code == 200 and len(r.content) > 50_000:
            return pd.read_parquet(io.BytesIO(r.content))
        print(f"    {p}: HTTP {r.status_code}")
    return None


def ctms_rows(df, tag):
    """Keep only CTMS: a DHS-only cyber series plus pay plan DC/DL.

    Anchor on occupational_series_code first - it's the clean numeric field.
    Pay plan must come from pay_plan_code (the short "DC"/"DL" code),
    NOT the "pay_plan" column, which holds the long descriptive text (e.g.
    "POSITIONS DESIGNATED AND PAID RATES OF BASIC PAY UNDER 6 U.S.C. 658 ...")
    and will never equal "DC" or "DL" as a plain string.
    """
    cols = {c.lower(): c for c in df.columns}
    occ = cols.get("occupational_series_code") or cols.get("occupational_series")
    pp = cols.get("pay_plan_code") or cols.get("pay_plan")
    if not occ:
        print(f"    [{tag}] no occupational_series column; have: {list(df.columns)[:12]}...")
        return None
    normalized_series = df[occ].astype(str).str.strip().str.zfill(4)
    if pp:
        normalized_plan = df[pp].astype(str).str.strip().str.upper()
        dc_dl = df[normalized_plan.isin(PLANS)]
        dc_dl_series = normalized_series.loc[dc_dl.index].value_counts().to_dict()
        print(f"    [{tag}] DC/DL occupational-series audit: {dc_dl_series}")
        unexpected = {series: count for series, count in dc_dl_series.items() if series not in SERIES}
        if unexpected:
            print(
                f"    [{tag}] WARNING: DC/DL records appear outside the known DHS cyber series: "
                f"{unexpected}. Review the CTMS population rule."
            )

    m = normalized_series.isin(SERIES)
    if pp:
        m &= df[pp].astype(str).str.strip().str.upper().isin(PLANS)
    out = df[m].copy()
    out["snapshot"] = tag
    return out


def collect(dataset, triples):
    frames = []
    retrieved = []
    latest_raw = None
    for y, m, v in triples:
        tag = f"{y}-{m}"
        print(f"[{dataset} {tag}] downloading...")
        df = get_parquet(dataset, y, m, v)
        if df is None:
            print(f"[{dataset} {tag}] FAILED")
            continue
        rows = ctms_rows(df, tag)
        if rows is None:
            continue
        print(f"[{dataset} {tag}] {len(df):,} rows -> {len(rows)} CTMS")
        frames.append(rows)
        retrieved.append(tag)
        latest_raw = (tag, df)
    combined = pd.concat(frames, ignore_index=True) if frames else None
    return combined, retrieved, latest_raw


def previous_retrieved_months():
    """Read completed downloads from the prior manifest, including empty months."""
    path = os.path.join(OUT, "pull_manifest.txt")
    found = {}
    if not os.path.exists(path):
        return found
    with open(path, encoding="utf-8") as f:
        for line in f:
            if ":" not in line or " snapshots retrieved -> " not in line:
                continue
            dataset, rest = line.rstrip().split(":", 1)
            tags = rest.split(" snapshots retrieved -> ", 1)[1]
            found[dataset] = {tag.strip() for tag in tags.split(",") if tag.strip()}
    return found


def existing_output(path):
    return pd.read_csv(path, dtype=str) if os.path.exists(path) else None


def merge_output(existing, new):
    if existing is None:
        return new
    if new is None:
        return existing
    return pd.concat([existing, new], ignore_index=True, sort=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Incrementally update CTMS OPM extracts.")
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="download all available months, replacing the existing extracts",
    )
    return parser.parse_args()


def write_schema_and_moves(emp_raw_sample, emp_full):
    """Diagnostic schema dump (from one raw snapshot) + salary trend summary."""
    with open(os.path.join(OUT, "ctms_schema.txt"), "w") as f:
        tag, df = emp_raw_sample
        f.write(f"Snapshot: {tag}\n\nCOLUMNS\n")
        for c in df.columns:
            f.write(f"  {c}  ({df[c].dtype})\n")
        cols = {c.lower(): c for c in df.columns}
        agency = cols.get("agency_subelement_code") or cols.get("agysub")
        payplan = cols.get("pay_plan_code") or cols.get("pay_plan")
        if agency and payplan:
            dhs = df[df[agency].astype(str).str.upper().str.startswith("HS")]
            f.write("\nDHS PAY PLAN CENSUS (all plans, descending)\n")
            for plan, n in dhs[payplan].value_counts().items():
                f.write(f"  {plan!r:12} {n:>8,}\n")
            f.write("\nDHS SUBELEMENTS\n")
            for a, n in dhs[agency].value_counts().items():
                f.write(f"  {a!r:12} {n:>8,}\n")
    print("wrote ctms_schema.txt")

    full_cols = {c.lower(): c for c in emp_full.columns}
    salary_col = (full_cols.get("annualized_adjusted_basic_pay")
                  or full_cols.get("salary") or full_cols.get("adjusted_basic_pay"))
    payplan_col = full_cols.get("pay_plan_code") or full_cols.get("pay_plan")
    if salary_col and payplan_col:
        sal = pd.to_numeric(emp_full[salary_col], errors="coerce")
        tmp = emp_full.assign(salary_num=sal)
        pivot = (tmp.groupby([payplan_col, "snapshot"])["salary_num"]
                 .agg(["count", "median", "mean"])
                 .reset_index()
                 .rename(columns={payplan_col: "pay_plan"}))
        pivot.to_csv(os.path.join(OUT, "ctms_salary_moves.csv"), index=False)
        print(f"wrote ctms_salary_moves.csv ({len(pivot):,} rows)")


def main():
    args = parse_args()
    manifest_lines = [f"Pull run: {datetime.now(timezone.utc).isoformat()}Z", ""]
    previous = {} if args.full_refresh else previous_retrieved_months()

    emp_triples = list_snapshots("employment")
    emp_missing = [t for t in emp_triples if f"{t[0]}-{t[1]}" not in previous.get("employment", set())]
    print(f"[employment] {len(emp_triples)} available; {len(emp_missing)} new month(s) to download")
    emp_new, emp_got, emp_raw = collect("employment", emp_missing)
    emp_path = os.path.join(OUT, "ctms_full.csv")
    emp_old = None if args.full_refresh else existing_output(emp_path)
    emp = merge_output(emp_old, emp_new)
    if emp is None:
        sys.exit("No employment data retrieved. Check access to data.opm.gov.")
    if emp_new is not None or args.full_refresh:
        emp.to_csv(emp_path, index=False)
        print(f"\nwrote ctms_full.csv  ({len(emp):,} rows, {len(emp.columns)} cols)")
    else:
        print(f"[employment] already current; using {len(emp):,} cached rows")
    emp_all_got = sorted(previous.get("employment", set()) | set(emp_got))
    manifest_lines.append(f"employment: {len(emp_all_got)} snapshots retrieved -> {', '.join(emp_all_got)}")

    # Reuse the newest employment download for the schema diagnostic rather
    # than making a second request for data we just received.
    if emp_raw is not None:
        write_schema_and_moves(emp_raw, emp)

    for ds, fname in (("accessions", "ctms_accessions.csv"),
                      ("separations", "ctms_separations.csv")):
        triples = list_snapshots(ds)
        missing = [t for t in triples if f"{t[0]}-{t[1]}" not in previous.get(ds, set())]
        print(f"\n[{ds}] {len(triples)} available; {len(missing)} new month(s) to download")
        got, got_tags, _ = collect(ds, missing)
        path = os.path.join(OUT, fname)
        old = None if args.full_refresh else existing_output(path)
        combined = merge_output(old, got)
        if combined is not None and (got is not None or args.full_refresh):
            combined.to_csv(path, index=False)
            print(f"wrote {fname}  ({len(combined):,} rows)")
        elif combined is not None:
            print(f"[{ds}] already current; using {len(combined):,} cached rows")
        else:
            print(f"[{ds}] no matching CTMS rows retrieved")
        all_got = sorted(previous.get(ds, set()) | set(got_tags))
        manifest_lines.append(f"{ds}: {len(all_got)} snapshots retrieved -> {', '.join(all_got)}")

    with open(os.path.join(OUT, "pull_manifest.txt"), "w") as f:
        f.write("\n".join(manifest_lines) + "\n")
    print("\nwrote pull_manifest.txt")
    print("\nDone.")


if __name__ == "__main__":
    main()
