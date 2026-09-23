#!/usr/bin/env python3
"""Validate cached/derived CTMS outputs and write a concise refresh audit.

Errors are conditions that make the report internally inconsistent and cause a
non-zero exit. Warnings are review items (for example a large monthly change or
a newly observed DC/DL occupational series) and do not block the build.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pandas as pd


OUT = os.path.dirname(os.path.abspath(__file__))
PLANS = {"DC", "DL"}
SERIES = {"2212", "2213", "2218", "2221", "2224", "2225", "2226", "2228", "2229", "2230"}
KEY_COLS = ["service_computation_date_leave", "duty_station_city", "age_bracket", "education_level_code"]
HEADCOUNT_CHANGE_MIN_PEOPLE = 10
HEADCOUNT_CHANGE_MIN_PCT = 25


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


def add_check(checks, name, status, detail):
    checks.append({"name": name, "status": status, "detail": detail})


def validate():
    checks = []
    errors = []
    warnings = []

    required_files = [
        "ctms_full.csv", "ctms_accessions.csv", "ctms_separations.csv",
        "ctms_people.csv", "ctms_person_history.csv", "ctms_vs_2210.csv",
        "ctms_vs_2210_by_component.csv", "ctms_dc_dl_series_audit.csv",
        "pull_state.json", "pull_changes.json",
    ]
    missing = [name for name in required_files if not os.path.exists(os.path.join(OUT, name))]
    if missing:
        detail = "Missing required outputs: " + ", ".join(missing)
        add_check(checks, "required outputs", "error", detail)
        errors.append(detail)
        return checks, errors, warnings, {}
    add_check(checks, "required outputs", "pass", f"All {len(required_files)} required outputs exist.")

    full = pd.read_csv(os.path.join(OUT, "ctms_full.csv"), dtype=str)
    people = pd.read_csv(os.path.join(OUT, "ctms_people.csv"), dtype=str)
    history = pd.read_csv(os.path.join(OUT, "ctms_person_history.csv"), dtype=str)
    comparison = pd.read_csv(os.path.join(OUT, "ctms_vs_2210.csv"), dtype=str)
    detail = pd.read_csv(os.path.join(OUT, "ctms_vs_2210_by_component.csv"), dtype=str)
    series_audit = pd.read_csv(os.path.join(OUT, "ctms_dc_dl_series_audit.csv"), dtype=str)
    with open(os.path.join(OUT, "pull_state.json"), encoding="utf-8") as f:
        state = json.load(f)
    with open(os.path.join(OUT, "pull_changes.json"), encoding="utf-8") as f:
        pull_changes = json.load(f)

    required_columns = {
        "ctms_full.csv": {"snapshot", "pay_plan_code", "occupational_series_code", "agency_subelement_code", *KEY_COLS},
        "ctms_people.csv": {"person_id", "first_snapshot", "last_snapshot"},
        "ctms_person_history.csv": {"person_id", "snapshot"},
        "ctms_vs_2210.csv": {"snapshot", "ctms_total", "series_2210", "component_codes"},
        "ctms_dc_dl_series_audit.csv": {"snapshot", "component_code", "series", "pay_plan", "headcount"},
    }
    frames = {
        "ctms_full.csv": full, "ctms_people.csv": people,
        "ctms_person_history.csv": history, "ctms_vs_2210.csv": comparison,
        "ctms_dc_dl_series_audit.csv": series_audit,
    }
    for filename, expected in required_columns.items():
        absent = sorted(expected - set(frames[filename].columns))
        if absent:
            message = f"{filename} is missing columns: {', '.join(absent)}"
            add_check(checks, f"schema: {filename}", "error", message)
            errors.append(message)
        else:
            add_check(checks, f"schema: {filename}", "pass", f"Required columns present ({len(expected)} checked).")

    if errors:
        return checks, errors, warnings, {}

    plans = set(full["pay_plan_code"].dropna().str.strip().str.upper())
    observed_series = set(full["occupational_series_code"].dropna().str.strip().str.zfill(4))
    bad_plans = sorted(plans - PLANS)
    bad_series = sorted(observed_series - SERIES)
    if bad_plans or bad_series:
        message = f"Filtered population contains unexpected plans={bad_plans} series={bad_series}"
        add_check(checks, "population rule", "error", message)
        errors.append(message)
    else:
        add_check(checks, "population rule", "pass", f"Only DC/DL and {len(observed_series)} approved series are present.")

    duplicate_keys = int(full.duplicated(subset=["snapshot", *KEY_COLS], keep=False).sum())
    if duplicate_keys:
        message = f"{duplicate_keys} rows share a reconstruction key within a snapshot."
        add_check(checks, "within-month person keys", "error", message)
        errors.append(message)
    else:
        add_check(checks, "within-month person keys", "pass", "No reconstruction-key collisions within a snapshot.")

    history_duplicates = int(history.duplicated(subset=["person_id", "snapshot"], keep=False).sum())
    if history_duplicates:
        message = f"{history_duplicates} person-history rows duplicate a person and snapshot."
        add_check(checks, "person history uniqueness", "error", message)
        errors.append(message)
    else:
        add_check(checks, "person history uniqueness", "pass", "One history row per reconstructed person-month.")

    direct_counts = full.groupby("snapshot").size().astype(int)
    history_counts = history.groupby("snapshot").size().astype(int).reindex(direct_counts.index, fill_value=0)
    history_mismatches = [m for m in direct_counts.index if direct_counts[m] != history_counts[m]]
    if history_mismatches:
        message = f"Reconstructed history does not reconcile to raw CTMS counts in: {history_mismatches}"
        add_check(checks, "person-history reconciliation", "error", message)
        errors.append(message)
    else:
        add_check(checks, "person-history reconciliation", "pass", f"History counts agree for {len(direct_counts)} months.")

    latest = direct_counts.index.max()
    current_people = int(people["last_snapshot"].eq(latest).sum())
    if current_people != int(direct_counts[latest]):
        message = f"Latest reconstructed headcount {current_people} != raw count {int(direct_counts[latest])}."
        add_check(checks, "latest headcount reconciliation", "error", message)
        errors.append(message)
    else:
        add_check(checks, "latest headcount reconciliation", "pass", f"Latest headcount agrees at {current_people}.")

    compare_counts = comparison.set_index("snapshot")["ctms_total"].astype(int)
    common = direct_counts.index.intersection(compare_counts.index)
    mismatches = [m for m in common if direct_counts[m] != compare_counts[m]]
    missing_comparison = sorted(set(direct_counts.index) - set(compare_counts.index))
    if mismatches or missing_comparison:
        message = f"Comparison reconciliation failed: mismatched={mismatches}, missing={missing_comparison}"
        add_check(checks, "CTMS/2210 reconciliation", "error", message)
        errors.append(message)
    else:
        add_check(checks, "CTMS/2210 reconciliation", "pass", f"CTMS totals agree for {len(common)} months.")

    detail_numeric = detail.assign(ctms_total=pd.to_numeric(detail["ctms_total"], errors="coerce").fillna(0))
    using_components = sorted(detail_numeric.loc[detail_numeric["ctms_total"] > 0, "component_code"].unique())
    stated_scope = []
    if len(comparison) and comparison["component_codes"].notna().any():
        stated_scope = sorted(comparison["component_codes"].dropna().iloc[0].split(","))
    if using_components != stated_scope:
        message = f"Comparison scope mismatch: detail={using_components}, summary={stated_scope}"
        add_check(checks, "comparison component scope", "error", message)
        errors.append(message)
    else:
        add_check(checks, "comparison component scope", "pass", "Summary uses the fixed union of CTMS-using components.")

    versions = state.get("datasets", {})
    null_versions = []
    for dataset, months in versions.items():
        null_versions.extend(f"{dataset}:{month}" for month, version in months.items() if version in (None, "", "None"))
    if null_versions:
        message = "Snapshots lack recorded OPM versions: " + ", ".join(null_versions[:10])
        add_check(checks, "OPM version state", "error", message)
        errors.append(message)
    else:
        total_versions = sum(len(months) for months in versions.values())
        add_check(checks, "OPM version state", "pass", f"Recorded versions for {total_versions} dataset-months.")

    audit_series = set(series_audit["series"].dropna().str.zfill(4))
    unexpected_series = sorted(audit_series - SERIES)
    if unexpected_series:
        message = "DHS DC/DL records use series outside the current CTMS rule: " + ", ".join(unexpected_series)
        add_check(checks, "series expansion monitor", "warning", message)
        warnings.append(message)
    else:
        add_check(checks, "series expansion monitor", "pass", "No DC/DL series outside the current CTMS rule.")

    pct = direct_counts.pct_change() * 100
    delta = direct_counts.diff()
    large_changes = []
    for month in direct_counts.index[1:]:
        if abs(delta[month]) >= HEADCOUNT_CHANGE_MIN_PEOPLE and abs(pct[month]) >= HEADCOUNT_CHANGE_MIN_PCT:
            large_changes.append({
                "snapshot": month, "change": int(delta[month]),
                "change_pct": round(float(pct[month]), 1), "headcount": int(direct_counts[month]),
            })
    if large_changes:
        message = f"{len(large_changes)} large month-over-month headcount changes require contextual review."
        add_check(checks, "headcount change monitor", "warning", message)
        warnings.append(message)
    else:
        add_check(checks, "headcount change monitor", "pass", f"No changes crossed the {HEADCOUNT_CHANGE_MIN_PEOPLE}-person and {HEADCOUNT_CHANGE_MIN_PCT}% review threshold.")

    first_component = (full.groupby("agency_subelement_code")["snapshot"].min().sort_values())
    first_series = (full.assign(_series=full["occupational_series_code"].str.zfill(4))
                    .groupby("_series")["snapshot"].min().sort_values())
    monitor = {
        "latest_snapshot": latest,
        "latest_headcount": int(direct_counts[latest]),
        "months": int(len(direct_counts)),
        "components": [{"code": code, "first_observed": month} for code, month in first_component.items()],
        "series": [{"code": code, "first_observed": month, "in_current_rule": code in SERIES} for code, month in first_series.items()],
        "new_components_latest": first_component[first_component == latest].index.tolist(),
        "new_series_latest": first_series[first_series == latest].index.tolist(),
        "unexpected_dc_dl_series": unexpected_series,
        "large_headcount_changes": large_changes,
        "pull_changes": pull_changes.get("changes", []),
        "full_refresh": bool(pull_changes.get("full_refresh")),
        "thresholds": {
            "headcount_change_min_people": HEADCOUNT_CHANGE_MIN_PEOPLE,
            "headcount_change_min_pct": HEADCOUNT_CHANGE_MIN_PCT,
        },
    }
    return checks, errors, warnings, monitor


def main():
    checks, errors, warnings, monitor = validate()
    result = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "fail" if errors else ("warning" if warnings else "pass"),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "monitor": monitor,
    }
    atomic_text(json.dumps(result, indent=2) + "\n", os.path.join(OUT, "ctms_validation.json"))

    lines = [
        "# CTMS refresh validation", "",
        f"Generated: {result['generated']}",
        f"Status: **{result['status'].upper()}**", "",
        "## Checks", "",
    ]
    for check in checks:
        icon = {"pass": "PASS", "warning": "WARN", "error": "FAIL"}[check["status"]]
        lines.append(f"- **{icon} — {check['name']}:** {check['detail']}")
    if monitor:
        lines.extend([
            "", "## Current baseline", "",
            f"- Latest snapshot: {monitor['latest_snapshot']}",
            f"- Latest CTMS headcount: {monitor['latest_headcount']}",
            f"- Monthly snapshots represented: {monitor['months']}",
            f"- Components first appearing in the latest month: {', '.join(monitor['new_components_latest']) or 'none'}",
            f"- Series first appearing in the latest month: {', '.join(monitor['new_series_latest']) or 'none'}",
            f"- DC/DL series outside the current rule: {', '.join(monitor['unexpected_dc_dl_series']) or 'none'}",
        ])
        changes = monitor.get("pull_changes", [])
        lines.extend(["", "## Last pull changes", ""])
        if changes:
            for change in changes:
                lines.append(
                    f"- {change['dataset']} {change['snapshot']}: {change['change_type']} "
                    f"version {change['previous_version'] or 'none'} → {change['current_version']}; "
                    f"filtered rows {change['previous_filtered_rows']} → {change['current_filtered_rows']} "
                    f"({change['filtered_row_change']:+d})"
                )
        else:
            lines.append("- No new or revised snapshots were downloaded.")
    atomic_text("\n".join(lines) + "\n", os.path.join(OUT, "ctms_validation.md"))

    print(f"validation status: {result['status'].upper()} ({len(errors)} errors, {len(warnings)} warnings)")
    print("wrote ctms_validation.json and ctms_validation.md")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
