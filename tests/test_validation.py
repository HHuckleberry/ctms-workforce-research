import importlib.util
import json
import pathlib
import tempfile
import unittest

import pandas as pd


MODULE_PATH = pathlib.Path(__file__).parents[1] / "pull" / "ctms_validate.py"
SPEC = importlib.util.spec_from_file_location("ctms_validate", MODULE_PATH)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class ValidationTests(unittest.TestCase):
    def test_consistent_fixture_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            full = pd.DataFrame([
                {"snapshot": "2026-06", "pay_plan_code": "DC", "occupational_series_code": "2230", "agency_subelement_code": "HSCA", "service_computation_date_leave": "2020-01-01", "duty_station_city": "A", "age_bracket": "30-39", "education_level_code": "13"},
                {"snapshot": "2026-07", "pay_plan_code": "DC", "occupational_series_code": "2230", "agency_subelement_code": "HSCA", "service_computation_date_leave": "2020-01-01", "duty_station_city": "A", "age_bracket": "30-39", "education_level_code": "13"},
            ])
            full.to_csv(root / "ctms_full.csv", index=False)
            pd.DataFrame([{"snapshot": "2026-07"}]).to_csv(root / "ctms_accessions.csv", index=False)
            pd.DataFrame([{"snapshot": "2026-07"}]).to_csv(root / "ctms_separations.csv", index=False)
            pd.DataFrame([{"person_id": "P1", "first_snapshot": "2026-06", "last_snapshot": "2026-07"}]).to_csv(root / "ctms_people.csv", index=False)
            pd.DataFrame([{"person_id": "P1", "snapshot": "2026-06"}, {"person_id": "P1", "snapshot": "2026-07"}]).to_csv(root / "ctms_person_history.csv", index=False)
            pd.DataFrame([
                {"snapshot": "2026-06", "ctms_total": 1, "series_2210": 10, "component_codes": "HSCA"},
                {"snapshot": "2026-07", "ctms_total": 1, "series_2210": 11, "component_codes": "HSCA"},
            ]).to_csv(root / "ctms_vs_2210.csv", index=False)
            pd.DataFrame([
                {"snapshot": "2026-06", "component_code": "HSCA", "ctms_total": 1, "series_2210": 10},
                {"snapshot": "2026-07", "component_code": "HSCA", "ctms_total": 1, "series_2210": 11},
            ]).to_csv(root / "ctms_vs_2210_by_component.csv", index=False)
            pd.DataFrame([
                {"snapshot": "2026-06", "component_code": "HSCA", "series": "2230", "pay_plan": "DC", "headcount": 1},
                {"snapshot": "2026-07", "component_code": "HSCA", "series": "2230", "pay_plan": "DC", "headcount": 1},
            ]).to_csv(root / "ctms_dc_dl_series_audit.csv", index=False)
            (root / "pull_state.json").write_text(json.dumps({"datasets": {
                "employment": {"2026-06": "1", "2026-07": "1"},
                "accessions": {"2026-06": "1", "2026-07": "1"},
                "separations": {"2026-06": "1", "2026-07": "1"},
            }}))
            (root / "pull_changes.json").write_text(json.dumps({"full_refresh": False, "changes": []}))

            original_out = validation.OUT
            validation.OUT = str(root)
            try:
                checks, errors, warnings, monitor = validation.validate()
            finally:
                validation.OUT = original_out

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertEqual(monitor["latest_headcount"], 1)
            self.assertTrue(all(check["status"] == "pass" for check in checks))
