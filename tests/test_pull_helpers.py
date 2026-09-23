import importlib.util
import pathlib
import unittest

import pandas as pd


MODULE_PATH = pathlib.Path(__file__).parents[1] / "pull" / "opm_ctms_pull.py"
SPEC = importlib.util.spec_from_file_location("opm_ctms_pull", MODULE_PATH)
pull = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pull)


class IncrementalPullTests(unittest.TestCase):
    def test_only_new_or_revised_versions_are_selected(self):
        available = [
            ("2026", "05", 1),
            ("2026", "06", 2),
            ("2026", "07", 1),
        ]
        completed = {"2026-05": "1", "2026-06": "1"}

        result = pull.snapshots_to_update(available, completed)

        self.assertEqual(result, [("2026", "06", 2), ("2026", "07", 1)])

    def test_revised_snapshot_replaces_rows_instead_of_appending(self):
        old = pd.DataFrame([
            {"snapshot": "2026-06", "value": "old"},
            {"snapshot": "2026-07", "value": "keep"},
        ])
        revised = pd.DataFrame([{"snapshot": "2026-06", "value": "new"}])

        result = pull.replace_snapshots(old, revised, {"2026-06"})

        self.assertEqual(result[result.snapshot == "2026-06"]["value"].tolist(), ["new"])
        self.assertEqual(result[result.snapshot == "2026-07"]["value"].tolist(), ["keep"])

    def test_revised_empty_snapshot_removes_prior_rows(self):
        old = pd.DataFrame([
            {"snapshot": "2026-06", "value": "remove"},
            {"snapshot": "2026-07", "value": "keep"},
        ])

        result = pull.replace_snapshots(old, None, {"2026-06"})

        self.assertEqual(result["snapshot"].tolist(), ["2026-07"])

    def test_comparison_is_aggregated_only_for_ctms_using_components(self):
        raw = pd.DataFrame([
            {"agency_subelement_code": "HSCA", "occupational_series_code": "2230", "pay_plan_code": "DC"},
            {"agency_subelement_code": "HSAD", "occupational_series_code": "2212", "pay_plan_code": "DL"},
            {"agency_subelement_code": "HSBB", "occupational_series_code": "2210", "pay_plan_code": "GS"},
            {"agency_subelement_code": "ARAA", "occupational_series_code": "2210", "pay_plan_code": "GS"},
        ])

        detail = pd.DataFrame(pull.comparison_rows(raw, "2026-07"))
        result = pull.aggregate_comparison(detail).iloc[0]

        self.assertEqual(result["ctms_total"], 2)
        self.assertEqual(result["series_2210"], 0)
        self.assertEqual(result["component_codes"], "HSAD,HSCA")

    def test_component_scope_is_fixed_across_months(self):
        detail = pd.DataFrame([
            {"snapshot": "2026-06", "component_code": "HSAD", "ctms_total": 0, "series_2210": 5},
            {"snapshot": "2026-06", "component_code": "HSBB", "ctms_total": 0, "series_2210": 9},
            {"snapshot": "2026-07", "component_code": "HSAD", "ctms_total": 1, "series_2210": 6},
            {"snapshot": "2026-07", "component_code": "HSBB", "ctms_total": 0, "series_2210": 10},
        ])

        result = pull.aggregate_comparison(detail).set_index("snapshot")

        self.assertEqual(result.loc["2026-06", "series_2210"], 5)
        self.assertEqual(result.loc["2026-07", "series_2210"], 6)
        self.assertEqual(result.loc["2026-06", "component_codes"], "HSAD")

    def test_series_audit_keeps_codes_outside_current_rule(self):
        raw = pd.DataFrame([
            {"agency_subelement_code": "HSCA", "occupational_series_code": "2230", "pay_plan_code": "DC"},
            {"agency_subelement_code": "HSCA", "occupational_series_code": "2299", "pay_plan_code": "DL"},
            {"agency_subelement_code": "HSCA", "occupational_series_code": "2210", "pay_plan_code": "GS"},
            {"agency_subelement_code": "ARAA", "occupational_series_code": "2299", "pay_plan_code": "DC"},
        ])

        result = pd.DataFrame(pull.dc_dl_series_rows(raw, "2026-07"))

        self.assertEqual(set(result["series"]), {"2230", "2299"})
        self.assertEqual(result["headcount"].sum(), 2)

    def test_change_log_distinguishes_revised_snapshot(self):
        old = pd.DataFrame([
            {"snapshot": "2026-06"}, {"snapshot": "2026-06"},
            {"snapshot": "2026-07"},
        ])
        new = pd.DataFrame([{"snapshot": "2026-06"}])

        result = pull.change_records(
            "employment", {"2026-06": "2"}, {"2026-06": "1", "2026-07": "1"}, old, new
        )[0]

        self.assertEqual(result["change_type"], "revised")
        self.assertEqual(result["filtered_row_change"], -1)


if __name__ == "__main__":
    unittest.main()
