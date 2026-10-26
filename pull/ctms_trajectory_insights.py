#!/usr/bin/env python3
"""Career-trajectory archetypes and auto-generated findings.

Everything here is computed from ctms_people.csv + ctms_events.csv, so findings
refresh with every monthly run. Findings only appear when each compared group has
at least MIN_N people; anything shorter is reported as "too few to compare".
Left-censored people (already present in the first snapshot) have unknown entry
dates and are excluded from time-to-event measures.
"""
import pandas as pd

MIN_N = 15
MIN_TENURE = 12  # months observed before a person counts toward leaver-vs-stayer comparisons


def _months_between(a, b):
    return (pd.Period(b, "M") - pd.Period(a, "M")).n


def _first_event_months(people, events, event, extra=None):
    """Months from first snapshot to the first matching event, per person (entry-observed people only)."""
    ev = events[events.event == event]
    if extra is not None:
        ev = ev[extra(ev)]
    first = ev.sort_values("to_snapshot").groupby("person_id").first()
    base = people.set_index("person_id")
    base = base[~base.joined_left_censored.astype(bool)]
    joined = base.join(first[["to_snapshot"]], how="inner")
    return joined.apply(lambda r: _months_between(r.first_snapshot, r.to_snapshot), axis=1)


def _tier_num(tier):
    try:
        return int(str(tier).split()[-1])
    except ValueError:
        return None


def assign_archetypes(people, events):
    """One mutually exclusive label per person, highest-signal path first."""
    up = set()
    for r in events[events.event == "rate_tier_change"].itertuples():
        a, b = _tier_num(r.from_value), _tier_num(r.to_value)
        if a is not None and b is not None and b > a:
            up.add(r.person_id)
    promoted = set(events[events.event == "pay_plan_change"].person_id)
    sup = set(events[events.event == "became_supervisor"].person_id)
    moved = set(events[events.event == "relocation"].person_id)

    def label(r):
        pid = r.person_id
        if pid in promoted:
            return "Promoted DC to DL"
        if pid in sup:
            return "Became supervisor"
        if pid in up:
            return "Climbed rate tiers"
        if pid in moved:
            return "Relocated"
        if r.num_raise_events > 0:
            return "Annual raises only"
        return "No pay movement"

    out = people.copy()
    out["archetype"] = out.apply(label, axis=1)
    return out


def archetype_table(tagged):
    rows = []
    for name, g in tagged.groupby("archetype"):
        mature = g[g.months_tracked >= MIN_TENURE]
        rows.append({
            "archetype": name,
            "n": int(len(g)),
            "share_pct": round(len(g) / len(tagged) * 100, 1),
            "median_months_tracked": float(g.months_tracked.median()),
            "median_salary_change_pct": None if g.salary_change_pct.dropna().empty else round(float(g.salary_change_pct.median()), 1),
            "still_present_pct": round(float(g.still_present_latest.astype(bool).mean() * 100), 1),
            "n_mature": int(len(mature)),
        })
    return sorted(rows, key=lambda r: -r["n"])


def time_to_event_summary(people, events):
    out = {}
    specs = {
        "first_raise": ("pay_increase", None),
        "tier_change": ("rate_tier_change", None),
        "supervisor": ("became_supervisor", None),
        "dc_to_dl": ("pay_plan_change", None),
    }
    for key, (event, extra) in specs.items():
        s = _first_event_months(people, events, event, extra)
        out[key] = {
            "n": int(len(s)),
            "median_months": None if s.empty else float(s.median()),
            "p25": None if s.empty else float(s.quantile(.25)),
            "p75": None if s.empty else float(s.quantile(.75)),
        }
    return out


def leaver_vs_stayer(tagged, events):
    """Compare leavers and stayers on what happened in the first MIN_TENURE months.

    Using a fixed window from entry gives both groups equal opportunity to
    accumulate events; comparing lifetime events would favor stayers simply
    because they were observed longer. Entry-observed people only.
    """
    pool = tagged[(tagged.months_tracked >= MIN_TENURE) & (~tagged.joined_left_censored.astype(bool))].copy()
    pool["left"] = ~pool.still_present_latest.astype(bool)
    first = pool.set_index("person_id").first_snapshot
    ev = events[events.person_id.isin(first.index)].copy()
    ev["offset"] = [_months_between(first[pid], snap) for pid, snap in zip(ev.person_id, ev.to_snapshot)]
    early = ev[ev.offset <= MIN_TENURE]
    rows = []
    for name, event in [("Pay increase", "pay_increase"), ("Relocation", "relocation"),
                        ("Rate-tier change", "rate_tier_change"), ("Became supervisor", "became_supervisor")]:
        hit = set(early[early.event == event].person_id)
        pool["_hit"] = pool.person_id.isin(hit)
        left, stay = pool[pool.left], pool[~pool.left]
        if len(left) < MIN_N or len(stay) < MIN_N:
            continue
        rows.append({
            "trait": name,
            "leavers_n": int(len(left)), "stayers_n": int(len(stay)),
            "leavers_pct": round(float(left._hit.mean() * 100), 1),
            "stayers_pct": round(float(stay._hit.mean() * 100), 1),
        })
    return rows


def exit_rate_by(tagged, column, label):
    """Exit rate by a category among people observed >= MIN_TENURE months; small groups dropped."""
    pool = tagged[tagged.months_tracked >= MIN_TENURE].copy()
    pool["left"] = ~pool.still_present_latest.astype(bool)
    rows = []
    for key, g in pool.groupby(column):
        if len(g) >= MIN_N:
            rows.append({"group": str(key), "n": int(len(g)), "exit_pct": round(float(g.left.mean() * 100), 1)})
    return {"by": label, "rows": sorted(rows, key=lambda r: -r["exit_pct"])}


def generate_findings(tagged, archetypes, tte, leave_stay, exit_tiers, exit_components):
    findings = []
    if archetypes:
        top = archetypes[0]
        findings.append({
            "id": "dominant-path",
            "headline": f"The most common path is \"{top['archetype']}\" ({top['share_pct']}% of {len(tagged)} people)",
            "detail": f"Median {top['median_months_tracked']:.0f} months observed; {top['still_present_pct']}% still present.",
            "n": top["n"],
        })
    fr = tte["first_raise"]
    if fr["n"] >= MIN_N and fr["median_months"] is not None:
        findings.append({
            "id": "time-to-first-raise",
            "headline": f"Half of people observed from entry see their first raise within {fr['median_months']:.0f} months",
            "detail": f"Middle half: {fr['p25']:.0f} to {fr['p75']:.0f} months (n={fr['n']}, entry-observed only).",
            "n": fr["n"],
        })
    for row in leave_stay:
        gap = row["leavers_pct"] - row["stayers_pct"]
        if abs(gap) >= 10:
            direction = "more" if gap > 0 else "less"
            findings.append({
                "id": "leaver-" + row["trait"].lower().replace(" ", "-"),
                "headline": f"Within their first {MIN_TENURE} months, leavers were {abs(gap):.0f} points {direction} likely than stayers to have a {row['trait'].lower()}",
                "detail": f"{row['leavers_pct']}% of {row['leavers_n']} leavers vs {row['stayers_pct']}% of {row['stayers_n']} stayers (entry-observed, {MIN_TENURE}+ months tracked). An association, not a cause.",
                "n": row["leavers_n"] + row["stayers_n"],
            })
    if leave_stay and all(abs(r["leavers_pct"] - r["stayers_pct"]) < 10 for r in leave_stay):
        findings.append({
            "id": "no-early-signal",
            "headline": "No early pay event separates leavers from stayers",
            "detail": "Raises, relocations, tier changes and supervisor moves in the first "
                      f"{MIN_TENURE} months differ by under 10 points between the two groups (n={leave_stay[0]['leavers_n'] + leave_stay[0]['stayers_n']}).",
            "n": leave_stay[0]["leavers_n"] + leave_stay[0]["stayers_n"],
        })
    for block in (exit_tiers, exit_components):
        rows = block["rows"]
        if len(rows) >= 2 and rows[0]["exit_pct"] - rows[-1]["exit_pct"] >= 15:
            hi, lo = rows[0], rows[-1]
            findings.append({
                "id": "exit-by-" + block["by"].lower().replace(" ", "-"),
                "headline": f"Exit rate varies by {block['by'].lower()}: {hi['group']} {hi['exit_pct']}% vs {lo['group']} {lo['exit_pct']}%",
                "detail": f"Among people observed {MIN_TENURE}+ months; groups under {MIN_N} people omitted ({hi['n']} and {lo['n']} people shown).",
                "n": hi["n"] + lo["n"],
            })
    return findings


def build(people, events):
    tagged = assign_archetypes(people, events)
    archetypes = archetype_table(tagged)
    tte = time_to_event_summary(people, events)
    leave_stay = leaver_vs_stayer(tagged, events)
    exit_tiers = exit_rate_by(tagged, "start_rate_tier", "Starting rate tier")
    exit_components = exit_rate_by(tagged, "agency_subelement_name", "Component")
    return {
        "archetype_caveat": "Path labels are assigned from whatever happened during each person's observed time, so people tracked longer have more chances to earn a richer label. Compare 'still present' across paths with that in mind.",
        "min_n": MIN_N,
        "min_tenure_months": MIN_TENURE,
        "archetypes": archetypes,
        "time_to_event": tte,
        "leaver_vs_stayer": leave_stay,
        "exit_by_tier": exit_tiers,
        "exit_by_component": exit_components,
        "findings": generate_findings(tagged, archetypes, tte, leave_stay, exit_tiers, exit_components),
    }
