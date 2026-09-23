#!/usr/bin/env python3
"""
Compare CTMS (DC/DL in the DHS-only cyber series family) against series 2210 (IT Management -
the standard government-wide track CTMS was meant to offer an alternative
to) at the same DHS components, over the same window.

2210 is broader than cyber specifically (it covers general IT management
roles too), so this is a proxy comparison, not a clean series-for-series
match - flagged in the output.

Output: ctms_vs_2210.csv - month, ctms_total, series_2210, both counted
within the same subelements (HSAA = DHS HQ, HSCA = CISA - where CTMS
actually lives) so the comparison is apples-to-apples on location at least.
"""

import argparse
import io
import os
import sys

import requests
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://data.opm.gov"
EARLIEST = ("2022", "06")
SUBELEMENTS = {"HSAA", "HSCA"}  # where CTMS actually lives
CTMS_SERIES = {"2212", "2213", "2218", "2221", "2224", "2225", "2226", "2228", "2229", "2230"}


def list_snapshots(dataset):
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


def get_parquet(year, month, version):
    for p in (f"/api/v1/files/employment/{year}/{month}/{version}/download",
              f"/v1/files/employment/{year}/{month}/{version}/download"):
        try:
            r = requests.get(BASE + p, timeout=900)
        except requests.RequestException as e:
            print(f"    {p}: {e}")
            continue
        if r.status_code == 200 and len(r.content) > 50_000:
            return pd.read_parquet(io.BytesIO(r.content))
        print(f"    {p}: HTTP {r.status_code}")
    return None


def parse_args():
    parser = argparse.ArgumentParser(description="Incrementally update the CTMS/2210 comparison.")
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="download all available months, replacing the existing comparison",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    triples = list_snapshots("employment")
    path = os.path.join(OUT, "ctms_vs_2210.csv")
    old = None
    migrated = False
    completed = set()
    if not args.full_refresh and os.path.exists(path):
        old = pd.read_csv(path)
        if "ctms_2230" in old.columns and "ctms_total" not in old.columns:
            old = old.rename(columns={"ctms_2230": "ctms_total"})
            migrated = True
        completed = set(old["snapshot"].astype(str))
    missing = [t for t in triples if f"{t[0]}-{t[1]}" not in completed]
    print(f"{len(triples)} monthly files available; {len(missing)} new month(s) to download")
    rows = []
    for y, m, v in missing:
        tag = f"{y}-{m}"
        print(f"[{tag}] downloading...")
        df = get_parquet(y, m, v)
        if df is None:
            print(f"[{tag}] FAILED")
            continue
        cols = {c.lower(): c for c in df.columns}
        agency = cols.get("agency_subelement_code")
        occ = cols.get("occupational_series_code")
        plan = cols.get("pay_plan_code")
        sub = df[df[agency].isin(SUBELEMENTS)]
        ctms_n = (
            sub[occ].astype(str).str.strip().str.zfill(4).isin(CTMS_SERIES)
            & sub[plan].astype(str).str.strip().str.upper().isin({"DC", "DL"})
        ).sum()
        it_n = (sub[occ].astype(str).str.strip().str.zfill(4) == "2210").sum()
        print(f"[{tag}] CTMS={ctms_n}  2210={it_n}")
        rows.append({"snapshot": tag, "ctms_total": int(ctms_n), "series_2210": int(it_n)})

    new = pd.DataFrame(rows)
    if old is not None and len(new):
        out = pd.concat([old, new], ignore_index=True).sort_values("snapshot")
    elif old is not None:
        out = old
    else:
        out = new
    if len(new) or args.full_refresh or migrated:
        out.to_csv(path, index=False)
        print(f"\nwrote ctms_vs_2210.csv ({len(out)} rows)")
    else:
        print(f"comparison already current; using {len(out)} cached rows")


if __name__ == "__main__":
    main()
