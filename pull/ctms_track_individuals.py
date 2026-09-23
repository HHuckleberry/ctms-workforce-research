#!/usr/bin/env python3
"""
Track individuals across CTMS employment snapshots and detect pay/career events.

OPM's public data has no employee ID - it's de-identified. So "individual" here
means a composite key: service_computation_date_leave (an actual date, not
bucketed - the strongest field available) + duty_station_city + age_bracket +
education_level_code. Verified 0 collisions across all 34 snapshots individually.

That key can still drift for the same real person: an age_bracket boundary
crossed (e.g. 39->40), a relocation, or a degree earned. Left unhandled, that
looks like the person leaving and someone new joining on the same day. To
correct for it, records sharing the same SCD whose snapshot ranges are
adjacent/non-overlapping (one ends right where another begins) are linked as
the same person - the same disambiguation logic manually described in the
original pull's design notes, generalized to remove per-run manual review.

Outputs, in this script's folder:
    ctms_people.csv    one row per tracked individual: span, start/end pay &
                       plan, whether they were promoted / became a supervisor /
                       got at least one raise, total months tracked
    ctms_events.csv    one row per detected change between two consecutive
                       snapshots for the same tracked individual
    ctms_summary.json  aggregate stats for the report
"""

import json
import os
from datetime import date

import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))

KEY_COLS = ["service_computation_date_leave", "duty_station_city", "age_bracket", "education_level_code"]


def load():
    df = pd.read_csv(os.path.join(OUT, "ctms_full.csv"), dtype=str)
    df["salary_num"] = pd.to_numeric(df["annualized_adjusted_basic_pay"], errors="coerce")
    df["is_supervisor"] = df["supervisory_status"].eq("SUPERVISOR OR MANAGER")
    df = df.sort_values("snapshot")
    return df


def load_accession_lookup():
    """SCD -> list of (snapshot, accession_category), for tagging how someone joined."""
    path = os.path.join(OUT, "ctms_accessions.csv")
    if not os.path.exists(path):
        return {}
    acc = pd.read_csv(path, dtype=str)
    lookup = {}
    for scd, g in acc.groupby("service_computation_date_leave"):
        lookup[scd] = list(zip(g["snapshot"], g["accession_category"]))
    return lookup


def load_separation_lookup():
    """SCD -> list of (snapshot, separation_category), for tagging how someone left."""
    path = os.path.join(OUT, "ctms_separations.csv")
    if not os.path.exists(path):
        return {}
    sep = pd.read_csv(path, dtype=str)
    lookup = {}
    for scd, g in sep.groupby("service_computation_date_leave"):
        lookup[scd] = list(zip(g["snapshot"], g["separation_category"]))
    return lookup


def cohort_quarter(snapshot):
    y, m = snapshot.split("-")
    q = (int(m) - 1) // 3 + 1
    return f"{y} Q{q}"


def years_federal_before_ctms(scd_str, first_ctms_snapshot):
    """Years between the service computation date (total creditable federal
    service - can predate CTMS by years for someone who transferred in) and
    when this person first shows up in CTMS. 0 means hired straight into
    CTMS with no prior federal service credited."""
    try:
        y, m, d = (int(x) for x in scd_str.split("-"))
        scd_date = date(y, m, d)
    except (ValueError, AttributeError, TypeError):
        return None
    sy, sm = (int(x) for x in first_ctms_snapshot.split("-"))
    entry_date = date(sy, sm, 1)
    years = (entry_date - scd_date).days / 365.25
    return max(0.0, years)  # SCD after CTMS entry isn't meaningful - treat as 0


def prior_service_bucket(years):
    if years is None:
        return "Unknown"
    if years < 0.5:
        return "New to federal service"
    if years < 3:
        return "0.5–3 yrs prior service"
    if years < 8:
        return "3–8 yrs prior service"
    if years < 15:
        return "8–15 yrs prior service"
    return "15+ yrs prior service"


def assign_person_ids(df):
    df = df.copy()
    df["raw_key"] = df[KEY_COLS].fillna("").astype(str).agg("|".join, axis=1)

    key_detail = df.groupby("raw_key")[KEY_COLS + ["agency_subelement_code"]].first()
    spans = (df.groupby("raw_key")["snapshot"]
             .agg(first="min", last="max", months=lambda s: sorted(s.unique()))
             .reset_index())
    spans = spans.merge(key_detail, on="raw_key")
    spans["scd"] = spans[KEY_COLS[0]]

    # Union-find over raw_keys, merged when same SCD and snapshot ranges are
    # adjacent/non-overlapping (drift), not when they overlap (that would be
    # two different, coincidentally-same-SCD people in the same month).
    parent = {k: k for k in spans["raw_key"]}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Same SCD is common on its own (DHS hires in cohorts - batches of people
    # starting the same day), so it's not sufficient by itself. Require the
    # subelement to match AND at most one of the other three key fields to
    # differ (a real person drifting - one age-bracket tick, one relocation,
    # or one degree upgrade - changes a single field; two unrelated people who
    # coincidentally share an SCD essentially never also share subelement plus
    # 2 of 3 remaining demographic fields in a population this size).
    drift_fields = ["duty_station_city", "age_bracket", "education_level_code"]
    for scd, grp in spans.groupby("scd"):
        if len(grp) < 2:
            continue
        grp = grp.sort_values("first")
        rows = grp.to_dict("records")
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                a_months, b_months = set(a["months"]), set(b["months"])
                if a_months & b_months:
                    continue  # overlap -> genuinely different people, don't merge
                if a["agency_subelement_code"] != b["agency_subelement_code"]:
                    continue
                differing = sum(1 for f in drift_fields if a[f] != b[f])
                if differing > 1:
                    continue  # too many fields differ - likely a coincidental SCD match
                union(a["raw_key"], b["raw_key"])

    df["person_id"] = df["raw_key"].map(find)

    # Union-find only validates the specific pairs it merges - it does NOT
    # guarantee every pair within the resulting connected component is
    # non-overlapping. Two genuinely different people (same SCD, both
    # present every month) can end up in one component if each gets
    # separately linked to a third, unrelated bridge record via drift.
    # Concretely: A and C never got unioned directly (they overlap in time,
    # so union() would have rejected that pair) - but if A<->B and B<->C
    # were each unioned, A and C land in the same component anyway. Detect
    # and undo that here: any component containing an overlapping pair gets
    # split back into one person per raw_key rather than risk a false merge.
    month_sets = spans.set_index("raw_key")["months"].apply(set).to_dict()
    groups = {}
    for raw_key in spans["raw_key"]:
        groups.setdefault(find(raw_key), []).append(raw_key)

    override = {}
    for keys in groups.values():
        if len(keys) < 2:
            continue
        bad = any(month_sets[keys[i]] & month_sets[keys[j]]
                  for i in range(len(keys)) for j in range(i + 1, len(keys)))
        if bad:
            for k in keys:
                override[k] = k  # split back into one person per raw_key

    if override:
        df["person_id"] = df["raw_key"].map(lambda k: override.get(k, find(k)))

    return df


def build_people_and_events(df):
    people_rows = []
    event_rows = []
    data_earliest = df["snapshot"].min()
    data_latest = df["snapshot"].max()
    accession_lookup = load_accession_lookup()
    separation_lookup = load_separation_lookup()

    for pid, g in df.groupby("person_id"):
        g = g.sort_values("snapshot").reset_index(drop=True)
        first, last = g.iloc[0], g.iloc[-1]

        promoted = False
        became_supervisor = False
        got_raise = False
        raises = []

        for i in range(1, len(g)):
            prev, cur = g.iloc[i - 1], g.iloc[i]
            # Rate-tier change is appended before pay_increase/pay_decrease so
            # that when both fire on the same from/to snapshot pair (they
            # usually do - a tier change is often what moves the pay), the
            # timeline shows tier change first, pay change second, matching
            # the actual cause-then-effect rather than alphabetical/insertion
            # order of unrelated checks.
            prev_rate, cur_rate = prev.get("step_or_rate_type"), cur.get("step_or_rate_type")
            if pd.notna(prev_rate) and pd.notna(cur_rate) and prev_rate != cur_rate:
                event_rows.append({
                    "person_id": pid, "from_snapshot": prev["snapshot"], "to_snapshot": cur["snapshot"],
                    "event": "rate_tier_change", "from_value": prev_rate,
                    "to_value": cur_rate,
                })
            if pd.notna(prev["salary_num"]) and pd.notna(cur["salary_num"]) and cur["salary_num"] != prev["salary_num"]:
                delta = cur["salary_num"] - prev["salary_num"]
                pct = delta / prev["salary_num"] * 100 if prev["salary_num"] else None
                if delta > 0:
                    got_raise = True
                    raises.append(pct)
                reason = None
                if delta < 0:
                    if prev.get("locality_pay_area") != cur.get("locality_pay_area"):
                        reason = "relocation_lower_locality"
                    elif prev.get("step_or_rate_type") != cur.get("step_or_rate_type"):
                        reason = "rate_tier_change"
                    elif pd.notna(cur.get("length_of_service_years")) and float(cur.get("length_of_service_years") or 1) <= 0.25:
                        reason = "new_hire_pay_correction"
                    else:
                        reason = "unexplained"
                event_rows.append({
                    "person_id": pid, "from_snapshot": prev["snapshot"], "to_snapshot": cur["snapshot"],
                    "event": "pay_increase" if delta > 0 else "pay_decrease",
                    "from_salary": prev["salary_num"], "to_salary": cur["salary_num"],
                    "delta": delta, "pct": pct, "decrease_reason": reason,
                    "from_duty_station": prev["duty_station_city"], "to_duty_station": cur["duty_station_city"],
                })
            if prev["pay_plan_code"] != cur["pay_plan_code"]:
                if prev["pay_plan_code"] == "DC" and cur["pay_plan_code"] == "DL":
                    promoted = True
                event_rows.append({
                    "person_id": pid, "from_snapshot": prev["snapshot"], "to_snapshot": cur["snapshot"],
                    "event": "pay_plan_change", "from_value": prev["pay_plan_code"], "to_value": cur["pay_plan_code"],
                })
            if prev["is_supervisor"] != cur["is_supervisor"] and cur["is_supervisor"]:
                became_supervisor = True
                event_rows.append({
                    "person_id": pid, "from_snapshot": prev["snapshot"], "to_snapshot": cur["snapshot"],
                    "event": "became_supervisor",
                })
            if prev["duty_station_city"] != cur["duty_station_city"]:
                event_rows.append({
                    "person_id": pid, "from_snapshot": prev["snapshot"], "to_snapshot": cur["snapshot"],
                    "event": "relocation", "from_value": prev["duty_station_city"], "to_value": cur["duty_station_city"],
                })

        months = sorted(g["snapshot"].unique())
        gaps = sum(1 for a, b in zip(months, months[1:]) if _month_gap(a, b) > 1)

        scd = pid.split("|")[0]
        accession_hits = accession_lookup.get(scd, [])
        how_joined = None
        for snap, category in accession_hits:
            if abs(_month_gap(snap, first["snapshot"])) <= 1:
                how_joined = category
                break
        if how_joined is None and accession_hits:
            how_joined = accession_hits[0][1]  # fall back to whatever's on record for that SCD

        still_present = last["snapshot"] == data_latest
        how_left = None
        if not still_present:
            separation_hits = separation_lookup.get(scd, [])
            for snap, category in separation_hits:
                if abs(_month_gap(snap, last["snapshot"])) <= 1:
                    how_left = category
                    break
            if how_left is None and separation_hits:
                how_left = separation_hits[0][1]

        prior_years = years_federal_before_ctms(scd, first["snapshot"])

        people_rows.append({
            "person_id": pid,
            "cohort_quarter": cohort_quarter(first["snapshot"]),
            "joined_left_censored": first["snapshot"] == data_earliest,
            "how_joined": how_joined,
            "years_federal_before_ctms": prior_years,
            "prior_service_bucket": prior_service_bucket(prior_years),
            "first_snapshot": first["snapshot"], "last_snapshot": last["snapshot"],
            "span_months": _month_gap(first["snapshot"], last["snapshot"]) + 1,
            "months_tracked": len(months), "has_gap": gaps > 0,
            "start_pay_plan": first["pay_plan_code"], "end_pay_plan": last["pay_plan_code"],
            "start_salary": first["salary_num"], "end_salary": last["salary_num"],
            "salary_change": (last["salary_num"] - first["salary_num"]) if pd.notna(first["salary_num"]) and pd.notna(last["salary_num"]) else None,
            "salary_change_pct": ((last["salary_num"] - first["salary_num"]) / first["salary_num"] * 100)
                                  if pd.notna(first["salary_num"]) and first["salary_num"] else None,
            "promoted_dc_to_dl": promoted,
            "became_supervisor": became_supervisor,
            "got_any_raise": got_raise,
            "num_raise_events": len(raises),
            "still_present_jul_2026": still_present,
            "how_left": how_left,
            "agency_subelement": first["agency_subelement_code"],
            "agency_subelement_name": first["agency_subelement"],
            "duty_station": first["duty_station_city"],
            "latest_duty_station": last["duty_station_city"],
            "latest_subelement": last["agency_subelement_code"],
            "latest_subelement_name": last["agency_subelement"],
            "start_rate_tier": first["step_or_rate_type"],
            "latest_rate_tier": last["step_or_rate_type"],
            "latest_locality": last["locality_pay_area"],
            "latest_education_bracket": last["education_level_bracket"],
            "latest_age_bracket": last["age_bracket"],
            "veteran": first["veteran_indicator"],
            "had_relocation": bool((g["duty_station_city"] != g["duty_station_city"].shift()).iloc[1:].any()),
        })

    return pd.DataFrame(people_rows), pd.DataFrame(event_rows)


def _month_gap(a, b):
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)


def main():
    df = load()
    df = assign_person_ids(df)
    people, events = build_people_and_events(df)

    people.to_csv(os.path.join(OUT, "ctms_people.csv"), index=False)
    events.to_csv(os.path.join(OUT, "ctms_events.csv"), index=False)

    # Compact month-by-month trajectory per person (for the report's per-person
    # detail view) - just the fields a trajectory chart/timeline needs, not
    # every raw column.
    history_cols = ["person_id", "snapshot", "salary_num", "pay_plan_code",
                     "duty_station_city", "is_supervisor", "grade", "tenure_code",
                     "step_or_rate_type"]
    history = df.sort_values(["person_id", "snapshot"])[history_cols].rename(columns={"salary_num": "salary"})
    history.to_csv(os.path.join(OUT, "ctms_person_history.csv"), index=False)
    print(f"wrote ctms_person_history.csv ({len(history)} rows)")

    summary = {
        "total_tracked_individuals": int(people["person_id"].nunique()),
        "raw_keys_before_linking": int(df["raw_key"].nunique()),
        "people_with_gap_in_timeline": int(people["has_gap"].sum()),
        "promoted_dc_to_dl": int(people["promoted_dc_to_dl"].sum()),
        "became_supervisor": int(people["became_supervisor"].sum()),
        "got_any_raise": int(people["got_any_raise"].sum()),
        "median_salary_change_pct_multi_month": float(
            people.loc[people["months_tracked"] > 1, "salary_change_pct"].median()
        ) if (people["months_tracked"] > 1).any() else None,
        "longest_tracked_months": int(people["months_tracked"].max()),
        "pay_increase_events": int((events["event"] == "pay_increase").sum()) if len(events) else 0,
        "pay_decrease_events": int((events["event"] == "pay_decrease").sum()) if len(events) else 0,
        "relocation_events": int((events["event"] == "relocation").sum()) if len(events) else 0,
    }
    with open(os.path.join(OUT, "ctms_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nwrote ctms_people.csv ({len(people)} rows), ctms_events.csv ({len(events)} rows)")


if __name__ == "__main__":
    main()
