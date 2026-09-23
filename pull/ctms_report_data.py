#!/usr/bin/env python3
"""Build one consolidated JSON with everything the HTML report needs."""

import json
import os

import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))

# Verified directly from our own pulled data (agency_subelement_code next to
# agency_subelement in ctms_full.csv) - not guessed. Only these 4 codes ever
# appear in the CTMS-filtered population.
SUBELEMENT_NAMES = {
    "HSAA": "DHS HQ",
    "HSAB": "USCIS",
    "HSAC": "Coast Guard",
    "HSAD": "Secret Service",
    "HSAE": "DHS OIG",
    "HSBB": "ICE",
    "HSBC": "TSA",
    "HSBD": "CBP",
    "HSBE": "FLETC",
    "HSCA": "CISA",
    "HSCB": "FEMA",
    "HSDA": "DNDO",
    "HSFA": "Science & Technology",
}

PRIOR_SERVICE_BUCKET_ORDER = ["New to federal service", "0.5–3 yrs prior service", "3–8 yrs prior service",
                              "8–15 yrs prior service", "15+ yrs prior service"]


def _months_between(a, b):
    """a, b are 'YYYY-MM' snapshot strings."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)


def main():
    full = pd.read_csv(os.path.join(OUT, "ctms_full.csv"), dtype=str)
    full["salary_num"] = pd.to_numeric(full["annualized_adjusted_basic_pay"], errors="coerce")
    people = pd.read_csv(os.path.join(OUT, "ctms_people.csv"))
    events = pd.read_csv(os.path.join(OUT, "ctms_events.csv"))
    acc = pd.read_csv(os.path.join(OUT, "ctms_accessions.csv"), dtype=str)
    sep = pd.read_csv(os.path.join(OUT, "ctms_separations.csv"), dtype=str)
    history = pd.read_csv(os.path.join(OUT, "ctms_person_history.csv"), dtype={"person_id": str})
    with open(os.path.join(OUT, "ctms_summary.json")) as f:
        summary = json.load(f)

    months = sorted(full["snapshot"].unique())

    headcount = (full.groupby(["snapshot", "pay_plan_code"]).size()
                 .unstack(fill_value=0).reindex(months, fill_value=0))
    headcount_series = {
        "months": months,
        "dc": headcount.get("DC", pd.Series(0, index=months)).tolist(),
        "dl": headcount.get("DL", pd.Series(0, index=months)).tolist(),
        "total": headcount.sum(axis=1).tolist(),
    }

    # Medians/ratios are noisy in the earliest months (population started at 2
    # people in Jun 2022 and ramped up) - gate those series to start once the
    # population is reasonably sized, so headcount/flow show the full history
    # but pay-index and supervisory-share don't chart statistical noise.
    STABILITY_THRESHOLD = 20
    stable_start_i = next((i for i, v in enumerate(headcount_series["total"]) if v >= STABILITY_THRESHOLD), 0)
    stable_months = months[stable_start_i:]

    sal = (full.groupby(["snapshot", "pay_plan_code"])["salary_num"]
           .median().unstack())
    salary_series = {
        "months": stable_months,
        "dc_median": [None if pd.isna(v) else round(v) for v in sal.get("DC", pd.Series(index=stable_months)).reindex(stable_months)],
        "dl_median": [None if pd.isna(v) else round(v) for v in sal.get("DL", pd.Series(index=stable_months)).reindex(stable_months)],
    }

    supv = (full.groupby("snapshot")["supervisory_status"]
            .apply(lambda s: (s == "SUPERVISOR OR MANAGER").mean() * 100)
            .reindex(stable_months))
    supervisory_pct = {"months": stable_months, "pct": [round(v, 1) for v in supv]}

    acc_by_month = acc.groupby("snapshot").size().reindex(months, fill_value=0)
    sep_by_month = sep.groupby("snapshot").size().reindex(months, fill_value=0)
    flow = {
        "months": months,
        "accessions": acc_by_month.tolist(),
        "separations": sep_by_month.tolist(),
        "net": (acc_by_month - sep_by_month).tolist(),
    }

    dec_events = events[events.event == "pay_decrease"]
    decrease_reasons = dec_events["decrease_reason"].value_counts().to_dict()

    reason_labels = {
        "relocation_lower_locality": "Moved to lower-cost locality",
        "rate_tier_change": "Same-location rate-tier change",
        "new_hire_pay_correction": "First-month pay correction",
        "unexplained": "Negligible (rounding-level)",
    }
    pay_decreases = []
    for _, r in dec_events.sort_values("from_snapshot").iterrows():
        loc = (f"{r['from_duty_station'].title()} → {r['to_duty_station'].title()}"
               if r["from_duty_station"] != r["to_duty_station"] else f"{r['from_duty_station'].title()} (same location)")
        pay_decreases.append({
            "id": r["person_id"],
            "location": loc, "from_salary": round(r["from_salary"]), "to_salary": round(r["to_salary"]),
            "pct": round(r["pct"], 1), "reason": reason_labels.get(r["decrease_reason"], r["decrease_reason"]),
        })

    latest = full[full["snapshot"] == months[-1]]
    # Build composition breakdowns from `people` (using each person's latest
    # snapshot fields), not the raw `full` snapshot rows - so these numbers
    # are drawn from exactly the same rows the report's drill-down table can
    # filter to (a raw-snapshot count and a people-table count could differ
    # by an edge case or two; using one source keeps "click the 2 -> see 2" exact).
    active_people = people[people["still_present_jul_2026"]]
    duty_station = (active_people["latest_duty_station"].str.title().value_counts().head(8).to_dict())
    education = (active_people["latest_education_bracket"].value_counts().to_dict())
    age = (active_people["latest_age_bracket"].value_counts().sort_index().to_dict())
    sep_reasons_people = (people["how_left"].dropna().value_counts().to_dict())

    # January-boundary check: does pay actually move across each Jan?
    def snap_med(tag, plan):
        s = full[(full.snapshot == tag) & (full.pay_plan_code == plan)]["salary_num"]
        return None if s.empty else round(s.median())

    jan_boundaries = []
    years_covered = sorted({int(m[:4]) for m in months})
    for yr in years_covered:
        dec_tag, feb_tag = f"{yr-1}-12", f"{yr}-02"
        if dec_tag in months and feb_tag in months:
            jan_boundaries.append({
                "label": f"Jan {yr}",
                "dc_before": snap_med(dec_tag, "DC"), "dc_after": snap_med(feb_tag, "DC"),
                "dl_before": snap_med(dec_tag, "DL"), "dl_after": snap_med(feb_tag, "DL"),
            })

    # Raise-tier explorer: for each January cycle, find whichever single-month
    # transition (Dec->Jan or Jan->Feb) actually carries the raise that year -
    # it moved a month later in the 2025->2026 cycle (see the Jan 31-Feb 3,
    # 2026 shutdown) - and bucket individual % changes into discrete tiers.
    # These are real administrative tiers (a performance/impact-rating system),
    # not noise - that's the whole point of surfacing the distribution instead
    # of just a mean.
    def person_deltas(tag_a, tag_b):
        ha = history[history.snapshot == tag_a][["person_id", "salary"]].rename(columns={"salary": "a"})
        hb = history[history.snapshot == tag_b][["person_id", "salary"]].rename(columns={"salary": "b"})
        m = ha.merge(hb, on="person_id")
        m = m[m.a.notna() & m.b.notna() & (m.a > 0)]
        m = m.assign(pct=(m.b - m.a) / m.a * 100)
        return m

    raise_years = []
    for yr in years_covered:
        candidates = [(f"{yr-1}-12", f"{yr}-01", "Dec → Jan"), (f"{yr}-01", f"{yr}-02", "Jan → Feb")]
        best = None
        for a, b, label in candidates:
            if a not in months or b not in months:
                continue
            m = person_deltas(a, b)
            if len(m) == 0:
                continue
            score = m["pct"].abs().sum()  # whichever transition carries the actual raise that year
            if best is None or score > best["score"]:
                best = {"a": a, "b": b, "label": label, "m": m, "score": score}
        if best is None:
            continue
        m = best["m"].copy()
        m["pct_round"] = m["pct"].round(1)
        tier_groups = m.groupby("pct_round")
        tiers = sorted(
            ({"pct": float(pct), "count": int(len(g)), "ids": g["person_id"].tolist()}
             for pct, g in tier_groups),
            key=lambda t: t["pct"]
        )
        raise_years.append({
            "year": yr,
            "transition": best["label"],
            "from_month": best["a"], "to_month": best["b"],
            "n": len(m),
            "mean_pct": round(m["pct"].mean(), 2),
            "median_pct": round(m["pct"].median(), 2),
            "n_groupings": sum(1 for t in tiers if t["count"] >= 2),
            "n_distinct_values": len(tiers),
            "tiers": tiers,
        })

    # Subelement comparison: pay, retention, promotion, supervisory rate by
    # component. Uses each person's FIRST subelement (which one they actually
    # joined into), not latest, so results describe where CTMS placed people,
    # not where attrition left them.
    subelement_stats = []
    for code, g in people.groupby("agency_subelement"):
        supplied_name = g["agency_subelement_name"].dropna().iloc[0] if "agency_subelement_name" in g and g["agency_subelement_name"].notna().any() else code
        name = SUBELEMENT_NAMES.get(code, supplied_name)
        valid_sal = g["end_salary"].dropna()
        subelement_stats.append({
            "code": name,
            "n": len(g),
            "median_salary": round(valid_sal.median()) if len(valid_sal) else None,
            "pct_dl": round((g["end_pay_plan"] == "DL").mean() * 100, 1),
            "pct_supervisor": round(g["became_supervisor"].mean() * 100, 1),
            "pct_still_present": round(g["still_present_jul_2026"].mean() * 100, 1),
            "median_prior_years": round(g["years_federal_before_ctms"].dropna().median(), 1) if g["years_federal_before_ctms"].notna().any() else None,
        })
    subelement_stats.sort(key=lambda s: -s["n"])

    # Salary spread (not just median) per month per plan - p25/p75/min/max,
    # so within-plan pay inequality is visible, not just central tendency.
    def pct_stats(s):
        s = s.dropna()
        if len(s) == 0:
            return None
        return {
            "p10": round(s.quantile(0.10)), "p25": round(s.quantile(0.25)),
            "median": round(s.median()), "p75": round(s.quantile(0.75)), "p90": round(s.quantile(0.90)),
            "n": int(len(s)),
        }

    salary_spread = {"months": stable_months, "dc": [], "dl": []}
    for m in stable_months:
        snap = full[full.snapshot == m]
        salary_spread["dc"].append(pct_stats(snap[snap.pay_plan_code == "DC"]["salary_num"]))
        salary_spread["dl"].append(pct_stats(snap[snap.pay_plan_code == "DL"]["salary_num"]))

    # Total payroll actually disbursed: each row is one person-month at an
    # annualized rate, so /12 gives that month's real pay. This is a figure
    # we can compute directly and defend, unlike the appropriated/requested
    # figures in the accountability section which come from secondary reporting.
    total_payroll_disbursed = round((full["salary_num"] / 12).dropna().sum())

    # Veteran status and its relationship to retention.
    veteran_counts = people["veteran"].value_counts().to_dict()
    veteran_retention = {
        v: round(g["still_present_jul_2026"].mean() * 100, 1)
        for v, g in people.groupby("veteran") if len(g) >= 5
    }

    # Tenure-group mix over time (population-level, no person-linkage needed).
    TENURE_LABELS = {"1": "Career", "2": "Career-conditional", "3": "Term/temporary"}
    tenure_trend = {"months": months}
    for code, label in TENURE_LABELS.items():
        tenure_trend[label] = [
            round((full[full.snapshot == m]["tenure_code"] == code).mean() * 100, 1)
            for m in months
        ]

    # Does prior federal experience predict retention? Does relocating?
    prior_vs_retention = [
        {"bucket": b, "retention_pct": round(g["still_present_jul_2026"].mean() * 100, 1), "n": len(g)}
        for b in PRIOR_SERVICE_BUCKET_ORDER
        for g in [people[people["prior_service_bucket"] == b]]
        if len(g) >= 5
    ]
    reloc_vs_retention = {
        label: round(g["still_present_jul_2026"].mean() * 100, 1)
        for label, g in [("Relocated at least once", people[people["had_relocation"]]),
                          ("Never relocated", people[~people["had_relocation"]])]
        if len(g) >= 5
    }

    # Time to promotion / time to becoming a supervisor, from CTMS entry.
    promo_events = events[(events.event == "pay_plan_change") & (events.to_value == "DL")]
    supervisor_events = events[events.event == "became_supervisor"]
    first_by_pid = people.set_index("person_id")["first_snapshot"].to_dict()

    def time_to_first_event(ev_df):
        out = []
        for pid, g in ev_df.groupby("person_id"):
            fs = first_by_pid.get(pid)
            if fs is None:
                continue
            first_event_snap = g.sort_values("to_snapshot")["to_snapshot"].iloc[0]
            out.append(_months_between(fs, first_event_snap))
        return out

    promo_months = time_to_first_event(promo_events)
    supervisor_months = time_to_first_event(supervisor_events)
    time_to_advance = {
        "promotion": {"n": len(promo_months), "median_months": (sorted(promo_months)[len(promo_months)//2] if promo_months else None), "values": promo_months},
        "supervisor": {"n": len(supervisor_months), "median_months": (sorted(supervisor_months)[len(supervisor_months)//2] if supervisor_months else None), "values": supervisor_months},
    }

    # Current administrative rate tiers. OPM reports these as RATE 01–06 in
    # step_or_rate_type; within DC they form a clear pay progression. DL uses
    # the same field but not every tier is populated in every month.
    rate_tiers = []
    active_by_rate = people[people["still_present_jul_2026"]]
    for tier in [f"RATE {i:02d}" for i in range(1, 7)]:
        g = active_by_rate[active_by_rate["latest_rate_tier"] == tier]
        if len(g) == 0:
            continue
        dc_group = g[g["end_pay_plan"] == "DC"]
        dl_group = g[g["end_pay_plan"] == "DL"]
        rate_tiers.append({
            "tier": tier,
            "dc": int(len(dc_group)),
            "dl": int(len(dl_group)),
            "total": int(len(g)),
            "dc_median": round(dc_group["end_salary"].dropna().median()) if dc_group["end_salary"].notna().any() else None,
            "dl_median": round(dl_group["end_salary"].dropna().median()) if dl_group["end_salary"].notna().any() else None,
            "ids": g["person_id"].tolist(),
            "dc_ids": dc_group["person_id"].tolist(),
            "dl_ids": dl_group["person_id"].tolist(),
        })

    rate_changes = events[events.event == "rate_tier_change"]
    rate_change_summary = {
        "events": int(len(rate_changes)),
        "people": int(rate_changes["person_id"].nunique()) if len(rate_changes) else 0,
    }

    # Boomerang check: anyone who separated and a later accession shares their
    # SCD - independent of the person-linking model entirely, checked directly
    # against the raw separations/accessions files.
    boomerangs = []
    sep_by_scd = sep.groupby("service_computation_date_leave")["snapshot"].apply(list)
    acc_by_scd = acc.groupby("service_computation_date_leave")["snapshot"].apply(list)
    for scd, sep_snaps in sep_by_scd.items():
        acc_snaps = acc_by_scd.get(scd)
        if not acc_snaps:
            continue
        last_sep = max(sep_snaps)
        later_acc = [a for a in acc_snaps if a > last_sep]
        if later_acc:
            boomerangs.append({"scd_year": scd[:4], "left": last_sep, "rejoined": min(later_acc)})

    # Notable individual stories, anonymized. "First observed" = first_snapshot
    # (the first month they show up in CTMS), NOT the service computation date
    # (SCD) - SCD is total federal service credit and can predate CTMS entry
    # by years for someone who transferred in. See the prior-service section
    # below for that distinction.
    def label_for(pid, row):
        return f"{row['duty_station']} · first observed {row['first_snapshot'][:4]}"

    top_raises = []
    multi = people[people.months_tracked > 3].nlargest(6, "salary_change_pct")
    for _, r in multi.iterrows():
        top_raises.append({
            "id": r["person_id"],
            "label": label_for(r["person_id"], r),
            "start_salary": None if pd.isna(r["start_salary"]) else round(r["start_salary"]),
            "end_salary": None if pd.isna(r["end_salary"]) else round(r["end_salary"]),
            "pct": round(r["salary_change_pct"], 1),
            "promoted": bool(r["promoted_dc_to_dl"]),
            "became_supervisor": bool(r["became_supervisor"]),
            "span": f"{r['first_snapshot']} → {r['last_snapshot']}",
        })

    promotions = []
    for _, r in people[people.promoted_dc_to_dl].iterrows():
        promotions.append({
            "id": r["person_id"],
            "label": label_for(r["person_id"], r),
            "start_salary": None if pd.isna(r["start_salary"]) else round(r["start_salary"]),
            "end_salary": None if pd.isna(r["end_salary"]) else round(r["end_salary"]),
            "pct": round(r["salary_change_pct"], 1) if pd.notna(r["salary_change_pct"]) else None,
            "span": f"{r['first_snapshot']} → {r['last_snapshot']}",
        })

    # Cohorts: when people were first observed in CTMS, and who's still here.
    cohorts = []
    latest_snapshot = months[-1]
    for q, g in people.groupby("cohort_quarter"):
        still = int(g["still_present_jul_2026"].sum())
        joined = len(g)
        cohorts.append({
            "quarter": q,
            "joined": joined,
            "still_present": still,
            "retention_pct": round(still / joined * 100, 1) if joined else None,
            "median_tenure_months": int(g["span_months"].median()),
            "promoted": int(g["promoted_dc_to_dl"].sum()),
            "got_raise": int(g["got_any_raise"].sum()),
            "left_censored": bool(g["joined_left_censored"].any()),
        })
    cohorts.sort(key=lambda c: c["quarter"])

    how_joined_counts = (people["how_joined"].dropna().value_counts().to_dict())

    # Hired (service computation date) vs. joined CTMS (first CTMS snapshot):
    # how many came in fresh vs. brought prior federal service with them.
    bucket_counts = people["prior_service_bucket"].value_counts().to_dict()
    prior_service = [{"bucket": b, "count": bucket_counts.get(b, 0)} for b in PRIOR_SERVICE_BUCKET_ORDER if bucket_counts.get(b, 0)]
    valid_years = people["years_federal_before_ctms"].dropna()
    prior_service_summary = {
        "median_years": round(valid_years.median(), 1) if len(valid_years) else None,
        "pct_new_to_federal": round((people["prior_service_bucket"] == "New to federal service").mean() * 100, 1),
        "max_years": round(valid_years.max(), 1) if len(valid_years) else None,
    }

    # Full per-person table, ranked by onboarding order (when they actually
    # joined CTMS - first_snapshot), for the "All Individuals" tab.
    people_sorted = people.sort_values(["first_snapshot", "person_id"]).reset_index(drop=True)
    people_table = []
    for i, r in people_sorted.iterrows():
        people_table.append({
            "id": r["person_id"],
            "rank": i + 1,
            "duty_station": r["duty_station"].title() if isinstance(r["duty_station"], str) else r["duty_station"],
            "latest_duty_station": r["latest_duty_station"].title() if isinstance(r["latest_duty_station"], str) else r["latest_duty_station"],
            "subelement": SUBELEMENT_NAMES.get(r["agency_subelement"], r.get("agency_subelement_name", r["agency_subelement"])),
            "latest_subelement": SUBELEMENT_NAMES.get(r["latest_subelement"], r.get("latest_subelement_name", r["latest_subelement"])),
            "rate_tier": r["latest_rate_tier"],
            "start_rate_tier": r["start_rate_tier"] if pd.notna(r["start_rate_tier"]) else None,
            "education_bracket": r["latest_education_bracket"],
            "age_bracket": r["latest_age_bracket"],
            "cohort": r["cohort_quarter"],
            "joined": r["first_snapshot"],
            "last_seen": r["last_snapshot"],
            "how_left": r["how_left"] if pd.notna(r["how_left"]) else None,
            "prior_years": round(r["years_federal_before_ctms"], 1) if pd.notna(r["years_federal_before_ctms"]) else None,
            "start_plan": r["start_pay_plan"],
            "end_plan": r["end_pay_plan"],
            "start_salary": None if pd.isna(r["start_salary"]) else round(r["start_salary"]),
            "end_salary": None if pd.isna(r["end_salary"]) else round(r["end_salary"]),
            "pct_change": None if pd.isna(r["salary_change_pct"]) else round(r["salary_change_pct"], 1),
            "promoted": bool(r["promoted_dc_to_dl"]),
            "supervisor": bool(r["became_supervisor"]),
            "active": bool(r["still_present_jul_2026"]),
            "tenure_months": int(r["span_months"]),
            "has_gap": bool(r["has_gap"]),
            "prior_service_bucket": r["prior_service_bucket"],
            "had_relocation": bool(r["had_relocation"]),
            "veteran": r["veteran"],
        })

    # Per-person month-by-month trajectory + event timeline, for the
    # click-through "story" view. Keyed by person_id.
    person_history = {}
    for pid, g in history.groupby("person_id"):
        g = g.sort_values("snapshot")
        person_history[pid] = [
            {
                "s": row["snapshot"],
                "sal": None if pd.isna(row["salary"]) else round(row["salary"]),
                "plan": row["pay_plan_code"],
                "rate": row["step_or_rate_type"],
                "loc": row["duty_station_city"].title() if isinstance(row["duty_station_city"], str) else row["duty_station_city"],
                "sup": bool(row["is_supervisor"]),
            }
            for _, row in g.iterrows()
        ]

    person_events = {}
    for pid, g in events.groupby("person_id"):
        rows = []
        for _, row in g.sort_values("from_snapshot").iterrows():
            e = {"event": row["event"], "from": row["from_snapshot"], "to": row["to_snapshot"]}
            if row["event"] in ("pay_increase", "pay_decrease"):
                e["from_salary"] = None if pd.isna(row["from_salary"]) else round(row["from_salary"])
                e["to_salary"] = None if pd.isna(row["to_salary"]) else round(row["to_salary"])
                e["pct"] = None if pd.isna(row["pct"]) else round(row["pct"], 1)
                if pd.notna(row.get("decrease_reason")):
                    e["reason"] = row["decrease_reason"]
            elif row["event"] in ("relocation", "pay_plan_change", "rate_tier_change"):
                e["from_value"] = row["from_value"]
                e["to_value"] = row["to_value"]
            rows.append(e)
        person_events[pid] = rows

    # CTMS (DC/DL in DHS-only cyber series) vs. IT-management series 2210
    # at the same DHS components (HSAA + HSCA, ~98% of the CTMS population).
    vs_2210 = None
    vs_2210_path = os.path.join(OUT, "ctms_vs_2210.csv")
    if os.path.exists(vs_2210_path):
        cmp_df = pd.read_csv(vs_2210_path).set_index("snapshot")
        cmp_df = cmp_df.reindex(months).dropna()
        cmp_months = cmp_df.index.tolist()
        ctms_col = "ctms_total" if "ctms_total" in cmp_df else "ctms_2230"
        ctms_peak_m = cmp_df[ctms_col].idxmax()
        it_peak_m = cmp_df["series_2210"].idxmax()
        ctms_peak, it_peak = cmp_df[ctms_col].max(), cmp_df["series_2210"].max()
        ctms_now, it_now = cmp_df[ctms_col].iloc[-1], cmp_df["series_2210"].iloc[-1]

        def pct_change(a, b):
            return round((b - a) / a * 100, 1) if a else None

        shock_a, shock_b = ("2025-09", "2025-10")
        vs_2210 = {
            "months": cmp_months,
            "ctms": cmp_df[ctms_col].tolist(),
            "series_2210": cmp_df["series_2210"].tolist(),
            "ctms_index": [round(v / cmp_df[ctms_col].iloc[0] * 100, 1) for v in cmp_df[ctms_col]],
            "series_2210_index": [round(v / cmp_df["series_2210"].iloc[0] * 100, 1) for v in cmp_df["series_2210"]],
            "ctms_peak": {"month": ctms_peak_m, "value": int(ctms_peak)},
            "it_peak": {"month": it_peak_m, "value": int(it_peak)},
            "ctms_peak_to_now_pct": pct_change(ctms_peak, ctms_now),
            "it_peak_to_now_pct": pct_change(it_peak, it_now),
            "shock_ctms_pct": pct_change(cmp_df.loc[shock_a, ctms_col], cmp_df.loc[shock_b, ctms_col]) if shock_a in cmp_df.index and shock_b in cmp_df.index else None,
            "shock_it_pct": pct_change(cmp_df.loc[shock_a, "series_2210"], cmp_df.loc[shock_b, "series_2210"]) if shock_a in cmp_df.index and shock_b in cmp_df.index else None,
        }

    report = {
        "generated": pd.Timestamp.now("UTC").isoformat(),
        "coverage": {"first": months[0], "last": months[-1], "n_months": len(months)},
        "headcount": headcount_series,
        "salary": salary_series,
        "supervisory_pct": supervisory_pct,
        "flow": flow,
        "separation_reasons": sep_reasons_people,
        "pay_decrease_reasons": decrease_reasons,
        "pay_decreases": pay_decreases,
        "duty_station_top": duty_station,
        "education_latest": education,
        "age_latest": age,
        "jan_boundaries": jan_boundaries,
        "cohorts": cohorts,
        "how_joined_counts": how_joined_counts,
        "prior_service": prior_service,
        "prior_service_summary": prior_service_summary,
        "people_table": people_table,
        "person_history": person_history,
        "person_events": person_events,
        "vs_2210": vs_2210,
        "raise_years": raise_years,
        "subelement_stats": subelement_stats,
        "salary_spread": salary_spread,
        "total_payroll_disbursed": total_payroll_disbursed,
        "veteran_counts": veteran_counts,
        "veteran_retention": veteran_retention,
        "tenure_trend": tenure_trend,
        "prior_vs_retention": prior_vs_retention,
        "reloc_vs_retention": reloc_vs_retention,
        "time_to_advance": time_to_advance,
        "rate_tiers": rate_tiers,
        "rate_change_summary": rate_change_summary,
        "boomerangs": boomerangs,
        "summary": summary,
        "top_raises": top_raises,
        "promotions": promotions,
        "latest_headcount": int(len(latest)),
        "peak_headcount": int(headcount_series["total"][headcount_series["total"].index(max(headcount_series["total"]))]),
        "peak_month": months[headcount_series["total"].index(max(headcount_series["total"]))],
    }

    with open(os.path.join(OUT, "ctms_report_data.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("wrote ctms_report_data.json")


if __name__ == "__main__":
    main()
