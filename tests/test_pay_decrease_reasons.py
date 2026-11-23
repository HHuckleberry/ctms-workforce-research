import os
import sys
import unittest
from unittest import mock

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pull"))
import ctms_track_individuals as t  # noqa: E402

DC_METRO = "WASHINGTON-BALTIMORE-ARLINGTON, DC-MD-VA-WV-PA"
REST = "REST OF THE UNITED STATES AND ITS TERRITORIES AND POSSESSIONS"


def history(pid, months):
    """months: list of (snapshot, salary, locality, city, rate_tier, years_of_service)."""
    return pd.DataFrame([{
        "person_id": pid, "snapshot": snap, "salary_num": float(sal),
        "locality_pay_area": loc, "duty_station_city": city, "step_or_rate_type": tier,
        "length_of_service_years": str(los), "pay_plan_code": "DC", "is_supervisor": False,
        "agency_subelement_code": "HSCA", "agency_subelement": "CISA", "age_bracket": "35-39",
        "education_level_bracket": "BACHELORS DEGREE", "veteran_indicator": "N",
    } for snap, sal, loc, city, tier, los in months])


def decrease_reasons(df):
    with mock.patch.object(t, "load_accession_lookup", return_value={}), \
         mock.patch.object(t, "load_separation_lookup", return_value={}):
        _, events = t.build_people_and_events(df)
    dec = events[events.event == "pay_decrease"]
    return dict(zip(dec.person_id, dec.decrease_reason)), dict(zip(dec.person_id, dec.decrease_detail))


class PayDecreaseReasonTest(unittest.TestCase):
    def test_each_rule(self):
        df = pd.concat([
            # cut in the same month as the locality change
            history("2010-01-01|A|35-39|13", [
                ("2023-01", 110000, DC_METRO, "WASHINGTON", "RATE 01", 5),
                ("2023-02", 100000, REST, "PENSACOLA", "RATE 01", 5)]),
            # moved first, cut posted a month later in the new location (the Pensacola case)
            history("2011-01-01|B|35-39|13", [
                ("2023-01", 110000, DC_METRO, "ARLINGTON", "RATE 02", 5),
                ("2023-02", 110000, REST, "PENSACOLA", "RATE 02", 5),
                ("2023-03", 100000, REST, "PENSACOLA", "RATE 01", 5)]),
            # up one month, down the next, still above the start (the West Saint Paul case)
            history("2012-01-01|C|35-39|13", [
                ("2023-01", 80000, REST, "ST PAUL", "RATE 01", 5),
                ("2023-02", 99000, REST, "ST PAUL", "RATE 01", 5),
                ("2023-03", 86000, REST, "ST PAUL", "RATE 02", 5)]),
            # genuine same-location tier change, no spike, no move
            history("2013-01-01|D|35-39|13", [
                ("2023-01", 90000, REST, "DENVER", "RATE 02", 5),
                ("2023-02", 90000, REST, "DENVER", "RATE 02", 5),
                ("2023-03", 85000, REST, "DENVER", "RATE 01", 5)]),
            # new hire, nothing else changed
            history("2014-01-01|E|35-39|13", [
                ("2023-01", 80000, REST, "BOISE", "RATE 01", 0.1),
                ("2023-02", 79000, REST, "BOISE", "RATE 01", 0.2)]),
            # established employee, nothing changed at all
            history("2015-01-01|F|35-39|13", [
                ("2023-01", 120400, REST, "BOISE", "RATE 02", 3),
                ("2023-02", 120200, REST, "BOISE", "RATE 02", 3)]),
        ], ignore_index=True)
        reasons, details = decrease_reasons(df)
        self.assertEqual(reasons, {
            "2010-01-01|A|35-39|13": "relocation_lower_locality",
            "2011-01-01|B|35-39|13": "relocation_lagged",
            "2012-01-01|C|35-39|13": "reverses_prior_spike",
            "2013-01-01|D|35-39|13": "rate_tier_change",
            "2014-01-01|E|35-39|13": "new_hire_pay_correction",
            "2015-01-01|F|35-39|13": "unexplained",
        })
        self.assertEqual(details["2011-01-01|B|35-39|13"],
                         "moved Arlington → Pensacola in 2023-02; pay adjusted in 2023-03")
        self.assertIn("net +7.5% since 2023-01", details["2012-01-01|C|35-39|13"])

    def test_spike_that_ends_below_start_is_not_excused(self):
        # up then down to *below* where it started is a real net cut, not a spike reversal
        df = history("2016-01-01|G|35-39|13", [
            ("2023-01", 90000, REST, "BOISE", "RATE 02", 5),
            ("2023-02", 95000, REST, "BOISE", "RATE 02", 5),
            ("2023-03", 85000, REST, "BOISE", "RATE 02", 5)])
        reasons, _ = decrease_reasons(df)
        self.assertEqual(reasons["2016-01-01|G|35-39|13"], "unexplained")


if __name__ == "__main__":
    unittest.main()
