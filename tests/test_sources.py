import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pull"))
import ctms_sources  # noqa: E402


def sample_report(r24=None, accessions=(5, 10)):
    return {
        "coverage": {"first": "2022-06", "last": "2026-08"},
        "accountability_metrics": {
            "peak_headcount": 215, "peak_month": "2024-12", "peak_to_latest_pct": -44.7,
            "months_from_june_2024_to_peak": 6,
            "retention_24m": r24 or {"eligible": 100, "retained": 62, "pct": 62.0},
        },
        "flow": {"accessions": list(accessions)},
        "major_exit_event": None,
    }


class SourcesTest(unittest.TestCase):
    def test_every_shipped_source_resolves_without_placeholders(self):
        cards, _ = ctms_sources.resolve(sample_report())
        for card in cards:
            self.assertNotIn("{", card["context"] or "")

    def test_retention_claim_mismatch_and_match(self):
        _, checks = ctms_sources.resolve(sample_report())
        ret = next(c for c in checks if c["source_id"] == "retention-94")
        self.assertEqual(ret["verdict"], "mismatch")
        _, checks = ctms_sources.resolve(sample_report(r24={"eligible": 50, "retained": 47, "pct": 94.0}))
        ret = next(c for c in checks if c["source_id"] == "retention-94")
        self.assertEqual(ret["verdict"], "match")

    def test_missing_retention_group_is_not_comparable(self):
        _, checks = ctms_sources.resolve(sample_report(r24={"eligible": 0, "retained": 0, "pct": None}))
        ret = next(c for c in checks if c["source_id"] == "retention-94")
        self.assertEqual(ret["verdict"], "not_comparable")

    def test_unverified_claims_listed_and_stale_flag(self):
        cards, checks = ctms_sources.resolve(sample_report())
        self.assertTrue(any(c["verdict"] == "unverified" for c in checks))
        self.assertTrue(next(c for c in cards if c["id"] == "hysen-2024")["stale"])


if __name__ == "__main__":
    unittest.main()
