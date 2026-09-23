#!/usr/bin/env python3
"""
CTMS pull — incrementally downloads newly available OPM snapshots.

Population: pay plan DC or DL intersected with the DHS-only cybersecurity
occupational-series family (2212/2213/2218/2221/2224/2225/2226/2228/2229/2230).
Keeps every column, plus the accessions and separations files.

The pull manifest records successfully retrieved months, including months
with zero matching rows. Normal runs append only newly published months;
--full-refresh intentionally downloads and replaces the complete history.

Months within each dataset (employment, accessions, separations) download
concurrently (PULL_WORKERS threads) since each is an independent network
request - a --full-refresh no longer waits on ~150 sequential round trips.

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
    ctms_vs_2210.csv      monthly comparison limited to CTMS-using components
    ctms_vs_2210_by_component.csv  component detail used to maintain that scope
    ctms_dc_dl_series_audit.csv  every DHS DC/DL series by month and component
    pull_changes.json      new/revised versions and row-count effects this run
    pull_state.json        machine-readable month -> OPM version update state
    pull_manifest.txt      human-readable run date + retrieved snapshot versions
"""

import argparse
import io
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
STATE_PATH = os.path.join(OUT, "pull_state.json")
PULL_WORKERS = 8  # data.opm.gov downloads are network I/O-bound, not CPU-bound - threads, not processes


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
    if not occ or not pp:
        missing = "occupational_series" if not occ else "pay_plan"
        print(f"    [{tag}] no {missing} column; have: {list(df.columns)[:12]}...")
        return None
    normalized_series = df[occ].astype(str).str.strip().str.zfill(4)
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

    m = normalized_series.isin(SERIES) & normalized_plan.isin(PLANS)
    out = df[m].copy()
    out["snapshot"] = tag
    return out


def comparison_rows(df, tag):
    """Count CTMS and series 2210 separately for every DHS component."""
    cols = {c.lower(): c for c in df.columns}
    agency = cols.get("agency_subelement_code") or cols.get("agysub")
    agency_name = cols.get("agency_subelement")
    occ = cols.get("occupational_series_code") or cols.get("occupational_series")
    plan = cols.get("pay_plan_code") or cols.get("pay_plan")
    if not agency or not occ or not plan:
        print(f"    [{tag}] cannot build 2210 comparison; required columns are missing")
        return []
    selected = [agency, occ, plan] + ([agency_name] if agency_name else [])
    work = df[selected].copy()
    work["component_code"] = work[agency].astype(str).str.strip().str.upper()
    work = work[work["component_code"].str.startswith("HS")]
    work["_series"] = work[occ].astype(str).str.strip().str.zfill(4)
    work["_plan"] = work[plan].astype(str).str.strip().str.upper()
    work["_ctms"] = work["_series"].isin(SERIES) & work["_plan"].isin(PLANS)
    work["_2210"] = work["_series"].eq("2210")

    rows = []
    for code, group in work.groupby("component_code"):
        name = ""
        if agency_name:
            names = group[agency_name].dropna().astype(str).str.strip()
            if len(names):
                name = names.mode().iloc[0]
        rows.append({
            "snapshot": tag,
            "component_code": code,
            "component_name": name,
            "ctms_total": int(group["_ctms"].sum()),
            "series_2210": int(group["_2210"].sum()),
        })
    ctms_n = sum(row["ctms_total"] for row in rows)
    it_n = sum(row["series_2210"] for row in rows)
    print(f"    [{tag}] captured component comparison: CTMS={ctms_n}  all-DHS 2210={it_n}")
    return rows


def aggregate_comparison(component_rows):
    """Restrict both tracks to the fixed set of components that ever use CTMS."""
    if component_rows is None or component_rows.empty:
        return None
    detail = component_rows.copy()
    detail["ctms_total"] = pd.to_numeric(detail["ctms_total"], errors="coerce").fillna(0)
    detail["series_2210"] = pd.to_numeric(detail["series_2210"], errors="coerce").fillna(0)
    ctms_components = sorted(detail.loc[detail["ctms_total"] > 0, "component_code"].dropna().unique())
    scoped = detail[detail["component_code"].isin(ctms_components)]
    summary = (scoped.groupby("snapshot", as_index=False)[["ctms_total", "series_2210"]]
               .sum().sort_values("snapshot"))
    summary["ctms_total"] = summary["ctms_total"].astype(int)
    summary["series_2210"] = summary["series_2210"].astype(int)
    summary["component_codes"] = ",".join(ctms_components)
    return summary


def dc_dl_series_rows(df, tag):
    """Inventory every DHS DC/DL series, including codes outside the CTMS rule."""
    cols = {c.lower(): c for c in df.columns}
    agency = cols.get("agency_subelement_code") or cols.get("agysub")
    occ = cols.get("occupational_series_code") or cols.get("occupational_series")
    plan = cols.get("pay_plan_code") or cols.get("pay_plan")
    if not agency or not occ or not plan:
        print(f"    [{tag}] cannot build DC/DL series audit; required columns are missing")
        return []
    work = df[[agency, occ, plan]].copy()
    work["component_code"] = work[agency].astype(str).str.strip().str.upper()
    work["series"] = work[occ].astype(str).str.strip().str.zfill(4)
    work["pay_plan"] = work[plan].astype(str).str.strip().str.upper()
    work = work[work["component_code"].str.startswith("HS") & work["pay_plan"].isin(PLANS)]
    grouped = (work.groupby(["component_code", "series", "pay_plan"])
               .size().reset_index(name="headcount"))
    grouped.insert(0, "snapshot", tag)
    return grouped.to_dict("records")


def _fetch_and_process(dataset, y, m, v, keep_raw):
    """Runs in a worker thread: one month's full download + row extraction.

    `keep_raw` is only ever True for the chronologically last employment
    month (decided by the caller before dispatch, since triples is sorted) -
    returning every month's raw full-column frame just to pick one afterward
    would hold up to ~50 months of every-column employment data in memory at
    once instead of the single month that's actually reused for the schema
    diagnostic.
    """
    tag = f"{y}-{m}"
    print(f"[{dataset} {tag}] downloading...")
    df = get_parquet(dataset, y, m, v)
    if df is None:
        print(f"[{dataset} {tag}] FAILED")
        return v, None, None, [], []
    rows = ctms_rows(df, tag)
    if rows is None:
        return v, None, None, [], []
    print(f"[{dataset} {tag}] {len(df):,} rows -> {len(rows)} CTMS")
    comparisons = comparison_rows(df, tag) if dataset == "employment" else []
    series_audit = dc_dl_series_rows(df, tag) if dataset == "employment" else []
    return v, rows, (df if keep_raw else None), comparisons, series_audit


def collect(dataset, triples):
    """Downloads every (year, month, version) triple concurrently (network
    I/O-bound, not CPU-bound - each month is an independent OPM download, so
    threads sidestep the ~150-round-trip sequential wait a full refresh used
    to take) then reassembles results in chronological order so output row
    order and "latest month" selection stay deterministic regardless of
    which request happens to finish first.
    """
    if not triples:
        return None, {}, None, pd.DataFrame(), pd.DataFrame()

    latest_tag = f"{triples[-1][0]}-{triples[-1][1]}"
    results = {}
    with ThreadPoolExecutor(max_workers=min(PULL_WORKERS, len(triples))) as pool:
        futures = {
            pool.submit(_fetch_and_process, dataset, y, m, v,
                        dataset == "employment" and f"{y}-{m}" == latest_tag): (y, m)
            for y, m, v in triples
        }
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()

    frames, retrieved, comparisons, series_audit = [], {}, [], []
    latest_raw = None
    for y, m, v in triples:
        tag = (y, m)
        version, rows, raw_df, comp_rows, series_rows = results[tag]
        if rows is None:
            continue
        frames.append(rows)
        retrieved[f"{y}-{m}"] = str(version)
        comparisons.extend(comp_rows)
        series_audit.extend(series_rows)
        if raw_df is not None:
            latest_raw = (f"{y}-{m}", raw_df)
    combined = pd.concat(frames, ignore_index=True) if frames else None
    return combined, retrieved, latest_raw, pd.DataFrame(comparisons), pd.DataFrame(series_audit)


def previous_retrieved_versions():
    """Read month -> OPM version state, migrating the old month-only manifest."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        return state.get("datasets", {})

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
            # A legacy manifest proves completion but not the OPM version. None
            # deliberately makes it eligible for replacement on the next pull.
            parsed = {}
            for item in tags.split(","):
                item = item.strip()
                if not item:
                    continue
                if "@" in item:
                    tag, version = item.rsplit("@", 1)
                    parsed[tag] = version
                else:
                    parsed[item] = None
            found[dataset] = parsed
    return found


def existing_output(path):
    return pd.read_csv(path, dtype=str) if os.path.exists(path) else None


def snapshots_to_update(available, completed_versions):
    """Return new months and months whose current OPM version has changed."""
    return [
        triple for triple in available
        if completed_versions.get(f"{triple[0]}-{triple[1]}") != str(triple[2])
    ]


def replace_snapshots(existing, new, completed_tags):
    """Idempotently replace successfully downloaded snapshots, including empty ones."""
    if existing is not None and "snapshot" in existing:
        existing = existing[~existing["snapshot"].astype(str).isin(completed_tags)]
    frames = [frame for frame in (existing, new) if frame is not None and len(frame)]
    if not frames:
        return new if new is not None else existing
    return pd.concat(frames, ignore_index=True, sort=False).sort_values("snapshot")


def atomic_csv(df, path):
    """Write beside the destination and replace it only after a complete write."""
    fd, temp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=OUT)
    os.close(fd)
    try:
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def atomic_text(text, path):
    fd, temp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=OUT)
    os.close(fd)
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def change_records(dataset, retrieved_versions, previous_versions, old, new):
    """Describe successful new/revised downloads and their filtered row effects."""
    records = []
    old_counts = old.groupby("snapshot").size().to_dict() if old is not None and "snapshot" in old else {}
    new_counts = new.groupby("snapshot").size().to_dict() if new is not None and "snapshot" in new else {}
    for tag, version in sorted(retrieved_versions.items()):
        previous_version = previous_versions.get(tag)
        records.append({
            "dataset": dataset,
            "snapshot": tag,
            "change_type": "new" if previous_version is None else "revised",
            "previous_version": previous_version,
            "current_version": version,
            "previous_filtered_rows": int(old_counts.get(tag, 0)),
            "current_filtered_rows": int(new_counts.get(tag, 0)),
            "filtered_row_change": int(new_counts.get(tag, 0) - old_counts.get(tag, 0)),
        })
    return records


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
    tag, df = emp_raw_sample
    schema = io.StringIO()
    schema.write(f"Snapshot: {tag}\n\nCOLUMNS\n")
    for c in df.columns:
        schema.write(f"  {c}  ({df[c].dtype})\n")
    cols = {c.lower(): c for c in df.columns}
    agency = cols.get("agency_subelement_code") or cols.get("agysub")
    payplan = cols.get("pay_plan_code") or cols.get("pay_plan")
    if agency and payplan:
        dhs = df[df[agency].astype(str).str.upper().str.startswith("HS")]
        schema.write("\nDHS PAY PLAN CENSUS (all plans, descending)\n")
        for plan, n in dhs[payplan].value_counts().items():
            schema.write(f"  {plan!r:12} {n:>8,}\n")
        schema.write("\nDHS SUBELEMENTS\n")
        for a, n in dhs[agency].value_counts().items():
            schema.write(f"  {a!r:12} {n:>8,}\n")
    atomic_text(schema.getvalue(), os.path.join(OUT, "ctms_schema.txt"))
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
        atomic_csv(pivot, os.path.join(OUT, "ctms_salary_moves.csv"))
        print(f"wrote ctms_salary_moves.csv ({len(pivot):,} rows)")


def main():
    args = parse_args()
    manifest_lines = [f"Pull run: {datetime.now(timezone.utc).isoformat()}", ""]
    previous = {} if args.full_refresh else previous_retrieved_versions()
    pull_changes = []

    emp_triples = list_snapshots("employment")
    emp_missing = snapshots_to_update(emp_triples, previous.get("employment", {}))
    comparison_detail_path = os.path.join(OUT, "ctms_vs_2210_by_component.csv")
    series_audit_path = os.path.join(OUT, "ctms_dc_dl_series_audit.csv")
    if not args.full_refresh and (
        not os.path.exists(comparison_detail_path) or not os.path.exists(series_audit_path)
    ):
        print("[employment] comparison/series baseline is missing; rebuilding it from all months")
        emp_missing = emp_triples
    print(f"[employment] {len(emp_triples)} available; {len(emp_missing)} new or revised month(s) to download")
    emp_new, emp_got, emp_raw, comparison_new, series_audit_new = collect("employment", emp_missing)
    if args.full_refresh and len(emp_got) != len(emp_missing):
        sys.exit("Full refresh did not retrieve every employment snapshot; existing employment outputs were left untouched.")
    emp_path = os.path.join(OUT, "ctms_full.csv")
    emp_old = None if args.full_refresh else existing_output(emp_path)
    pull_changes.extend(change_records(
        "employment", emp_got, previous.get("employment", {}), emp_old, emp_new
    ))
    emp = replace_snapshots(emp_old, emp_new, set(emp_got))
    if emp is None:
        sys.exit("No employment data retrieved. Check access to data.opm.gov.")
    if emp_new is not None or args.full_refresh:
        atomic_csv(emp, emp_path)
        print(f"\nwrote ctms_full.csv  ({len(emp):,} rows, {len(emp.columns)} cols)")
    else:
        print(f"[employment] already current; using {len(emp):,} cached rows")
    emp_versions = dict(previous.get("employment", {}))
    emp_versions.update(emp_got)
    manifest_lines.append(f"employment: {len(emp_versions)} snapshots retrieved -> {', '.join(f'{tag}@{version}' for tag, version in sorted(emp_versions.items()))}")

    comparison_path = os.path.join(OUT, "ctms_vs_2210.csv")
    comparison_detail_old = None if args.full_refresh else existing_output(comparison_detail_path)
    comparison_detail = replace_snapshots(comparison_detail_old, comparison_new, set(emp_got))
    comparison = aggregate_comparison(comparison_detail)
    if comparison is not None and (emp_got or args.full_refresh):
        atomic_csv(comparison_detail, comparison_detail_path)
        atomic_csv(comparison, comparison_path)
        scope = comparison["component_codes"].iloc[0]
        print(f"wrote ctms_vs_2210.csv ({len(comparison):,} rows; CTMS-using components: {scope})")

    series_audit_old = None if args.full_refresh else existing_output(series_audit_path)
    series_audit = replace_snapshots(series_audit_old, series_audit_new, set(emp_got))
    if series_audit is not None and (emp_got or args.full_refresh):
        atomic_csv(series_audit, series_audit_path)
        unexpected = sorted(set(series_audit["series"].astype(str).str.zfill(4)) - SERIES)
        suffix = f"; review unexpected series: {', '.join(unexpected)}" if unexpected else ""
        print(f"wrote ctms_dc_dl_series_audit.csv ({len(series_audit):,} rows{suffix})")

    # Reuse the newest employment download for the schema diagnostic rather
    # than making a second request for data we just received.
    if emp_raw is not None:
        write_schema_and_moves(emp_raw, emp)

    for ds, fname in (("accessions", "ctms_accessions.csv"),
                      ("separations", "ctms_separations.csv")):
        triples = list_snapshots(ds)
        missing = snapshots_to_update(triples, previous.get(ds, {}))
        print(f"\n[{ds}] {len(triples)} available; {len(missing)} new or revised month(s) to download")
        got, got_versions, _, _, _ = collect(ds, missing)
        if args.full_refresh and len(got_versions) != len(missing):
            sys.exit(f"Full refresh did not retrieve every {ds} snapshot; the existing {ds} output was left untouched.")
        path = os.path.join(OUT, fname)
        old = None if args.full_refresh else existing_output(path)
        pull_changes.extend(change_records(ds, got_versions, previous.get(ds, {}), old, got))
        combined = replace_snapshots(old, got, set(got_versions))
        if combined is not None and (got is not None or args.full_refresh):
            atomic_csv(combined, path)
            print(f"wrote {fname}  ({len(combined):,} rows)")
        elif combined is not None:
            print(f"[{ds}] already current; using {len(combined):,} cached rows")
        else:
            print(f"[{ds}] no matching CTMS rows retrieved")
        all_versions = dict(previous.get(ds, {}))
        all_versions.update(got_versions)
        manifest_lines.append(f"{ds}: {len(all_versions)} snapshots retrieved -> {', '.join(f'{tag}@{version}' for tag, version in sorted(all_versions.items()))}")

        if ds == "accessions":
            acc_versions = all_versions
        else:
            sep_versions = all_versions

    state = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {
            "employment": emp_versions,
            "accessions": acc_versions,
            "separations": sep_versions,
        },
    }
    atomic_text(json.dumps(state, indent=2, sort_keys=True) + "\n", STATE_PATH)
    atomic_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(),
        "full_refresh": args.full_refresh,
        "changes": pull_changes,
    }, indent=2) + "\n", os.path.join(OUT, "pull_changes.json"))
    atomic_text("\n".join(manifest_lines) + "\n", os.path.join(OUT, "pull_manifest.txt"))
    print("\nwrote pull_manifest.txt")
    print("\nDone.")


if __name__ == "__main__":
    main()
