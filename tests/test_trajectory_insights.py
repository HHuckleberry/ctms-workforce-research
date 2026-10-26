import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pull"))
import ctms_trajectory_insights as t  # noqa: E402


def person(pid, **kw):
    base = dict(person_id=pid, first_snapshot="2023-01", joined_left_censored=False, months_tracked=24,
                num_raise_events=0, still_present_latest=True, salary_change_pct=0.0,
                start_rate_tier="RATE 01", agency_subelement_name="X", got_any_raise=False,
                had_relocation=False, became_supervisor=False)
    base.update(kw)
    return base


def event(pid, kind, snap, fv=None, tv=None):
    return dict(person_id=pid, event=kind, from_snapshot=snap, to_snapshot=snap, from_value=fv, to_value=tv)


class InsightsTest(unittest.TestCase):
    def test_archetype_priority_and_tier_direction(self):
        people = pd.DataFrame([person("a"), person("b", num_raise_events=1), person("c"), person("d")])
        events = pd.DataFrame([
            event("c", "rate_tier_change", "2023-06", "RATE 01", "RATE 03"),
            event("d", "rate_tier_change", "2023-06", "RATE 03", "RATE 01"),  # downward: not a climb
        ])
        labels = t.assign_archetypes(people, events).set_index("person_id").archetype
        self.assertEqual(labels["a"], "No pay movement")
        self.assertEqual(labels["b"], "Annual raises only")
        self.assertEqual(labels["c"], "Climbed rate tiers")
        self.assertEqual(labels["d"], "No pay movement")

    def test_small_groups_never_compared(self):
        people = pd.DataFrame([person(str(i), still_present_latest=i % 2 == 0) for i in range(10)])
        events = pd.DataFrame(columns=["person_id", "event", "from_snapshot", "to_snapshot", "from_value", "to_value"])
        result = t.build(people, events)
        self.assertEqual(result["leaver_vs_stayer"], [])
        self.assertEqual(result["exit_by_tier"]["rows"], [])

    def test_early_window_ignores_late_events(self):
        rows, evs = [], []
        for i in range(20):  # leavers: pay increase only after month 12
            rows.append(person(f"l{i}", still_present_latest=False))
            evs.append(event(f"l{i}", "pay_increase", "2024-06"))
        for i in range(20):  # stayers: pay increase in month 3
            rows.append(person(f"s{i}"))
            evs.append(event(f"s{i}", "pay_increase", "2023-04"))
        row = next(r for r in t.leaver_vs_stayer(t.assign_archetypes(pd.DataFrame(rows), pd.DataFrame(evs)), pd.DataFrame(evs))
                   if r["trait"] == "Pay increase")
        self.assertEqual(row["leavers_pct"], 0.0)
        self.assertEqual(row["stayers_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
