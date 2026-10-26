"""Resolve external source cards and claim-vs-data checks from sources.json.

Pure functions only (no file reads beyond load_sources) so they are unit-testable.
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STALE_MONTHS = 12


def load_sources(path=None):
    with open(path or os.path.join(HERE, "sources.json"), encoding="utf-8") as f:
        return json.load(f)["sources"]


def month_label(ym):
    return pd.Period(ym, "M").strftime("%b %Y") if ym else "n/a"


def build_metrics(report):
    """Flatten the report values that source cards may reference."""
    acct = report["accountability_metrics"]
    r24 = acct.get("retention_24m") or {}
    elapsed = acct.get("months_from_june_2024_to_peak")
    if elapsed is None:
        timing = "at an undetermined time"
    elif elapsed >= 0:
        timing = f"{elapsed} months later"
    else:
        timing = f"{abs(elapsed)} months earlier"
    if r24.get("eligible"):
        sentence = (
            f"Using a consistent 24-month milestone, this reconstruction retains "
            f"<b>{r24['retained']} of {r24['eligible']} eligible people ({r24['pct']:.1f}%)</b>. "
            "Differences from the public claim may reflect cohort, date, and definition differences."
        )
    else:
        sentence = "The current dataset does not yet contain a maturity-eligible 24-month group for a comparable calculation."
    exit_event = report.get("major_exit_event")
    if exit_event:
        wave = (
            f"the {month_label(exit_event['start'])}–{month_label(exit_event['end'])} exit wave accounts for "
            f"{exit_event['departures']} departures ({exit_event['share_of_all_departures_pct']}% of all observed departures)."
        )
    else:
        wave = "no single exit wave stands out."
    pct = acct.get("peak_to_latest_pct")
    return {
        "peak_headcount": acct.get("peak_headcount"),
        "peak_month_label": month_label(acct.get("peak_month")),
        "peak_timing_vs_testimony": timing,
        "peak_to_latest_pct_label": "n/a" if pct is None else f"{pct:+.1f}%",
        "first_month_label": month_label(report["coverage"]["first"]),
        "last_month_label": month_label(report["coverage"]["last"]),
        "retention_24m_sentence": sentence,
        "retention_24m_pct": r24.get("pct"),
        "exit_wave_sentence": wave,
        "total_accessions": int(sum(report["flow"]["accessions"])),
    }


def _fill(text, metrics):
    return text.format(**{k: ("n/a" if v is None else v) for k, v in metrics.items()}) if text else text


def _verdict(check, observed):
    """Map observed data to match / mismatch / not_comparable per the check rule."""
    if observed is None:
        return "not_comparable"
    claim = check["claim_value"]
    kind = check.get("verdict")
    if kind == "below_claim":
        # The source reports a shortfall against `claim_value`; data agrees if it also falls short.
        return "match" if observed < claim else "mismatch"
    tol = check.get("tolerance", 0)
    return "match" if abs(observed - claim) <= tol else "mismatch"


def resolve(report, sources=None, today=None):
    """Return (cards, claim_checks) ready to embed in the report JSON."""
    sources = sources if sources is not None else load_sources()
    metrics = build_metrics(report)
    today = pd.Period(today, "M") if today else pd.Period(report["coverage"]["last"], "M")
    cards, checks = [], []
    for src in sources:
        age = (today - pd.Period(src["published"][:7], "M")).n
        card = {
            "id": src["id"],
            "label": src["label"],
            "status": src["status"],
            "published": src["published"],
            "html": src["html"],
            "context": _fill(src.get("context"), metrics),
            "caveat": src.get("caveat"),
            "foot": src.get("foot"),
            "link": src.get("link"),
            "stale": age > STALE_MONTHS,
            "age_months": age,
        }
        cards.append(card)
        chk = src.get("check")
        if chk:
            observed = metrics.get(chk["metric"])
            checks.append({
                "source_id": src["id"],
                "source_label": src["label"],
                "claim": chk["claim"],
                "claim_value": chk["claim_value"],
                "observed_label": _fill(chk["metric_label"], metrics),
                "observed": observed,
                "verdict": _verdict(chk, observed),
                "note": chk.get("note"),
            })
        for text in src.get("unverified_claims", []):
            checks.append({
                "source_id": src["id"], "source_label": src["label"], "claim": text,
                "claim_value": None, "observed_label": None, "observed": None,
                "verdict": "unverified", "note": src.get("caveat"),
            })
    return cards, checks
