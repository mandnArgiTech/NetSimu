import json
import os
import tempfile

from netops_sim.grading import grade


def _write(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f)


def test_grade_top1_correct_full_score():
    with tempfile.TemporaryDirectory() as tmp:
        rca = os.path.join(tmp, "rca.json")
        truth = os.path.join(tmp, "truth.json")

        _write(rca, {
            "incident_id": "INC-1",
            "ranked_hypotheses": [
                {"entity_id": "port-tor-01-host-01-vmnic0",
                 "score": 0.91, "rule": "R-MTU-001"},
                {"entity_id": "tep-host-01", "score": 0.05},
            ],
            "matched_anomalies": [
                {"entity": "port-tor-01-host-01-vmnic0", "metric": "in_errors"},
                {"entity": "teppair-host-01-host-02", "metric": "drop_pps"},
                {"entity": "tep-host-01", "metric": "encap_errors"},
                {"entity": "app-web", "metric": "p99_latency_ms"},
                {"entity": "app-web", "metric": "5xx_rate"},
            ],
        })
        _write(truth, {
            "scenario": "mtu_mismatch",
            "fault_time": "2026-05-05T14:32:00Z",
            "root_cause_entity": "port-tor-01-host-01-vmnic0",
            "expected_anomalies": [
                {"entity": "port-tor-01-host-01-vmnic0", "metric": "in_errors"},
                {"entity_pattern": "teppair-host-01-*", "metric": "drop_pps"},
                {"entity": "tep-host-01", "metric": "encap_errors"},
                {"entity": "app-web", "metric": "p99_latency_ms"},
                {"entity": "app-web", "metric": "5xx_rate"},
            ],
            "expected_rca_rule": "R-MTU-001",
        })

        result = grade(rca, truth)
        assert result["top1_correct"] is True
        assert result["rule_matched"] is True
        assert result["anomaly_recall"] == 1.0
        assert result["score"] == 1.0


def test_grade_top1_wrong_partial_credit_if_in_top3():
    with tempfile.TemporaryDirectory() as tmp:
        rca = os.path.join(tmp, "rca.json")
        truth = os.path.join(tmp, "truth.json")

        _write(rca, {
            "ranked_hypotheses": [
                {"entity_id": "tep-host-01", "score": 0.4},
                {"entity_id": "port-tor-01-host-01-vmnic0", "score": 0.35},
                {"entity_id": "vlan-1647", "score": 0.1},
            ],
            "matched_anomalies": [],
        })
        _write(truth, {
            "scenario": "mtu_mismatch",
            "root_cause_entity": "port-tor-01-host-01-vmnic0",
            "expected_anomalies": [],
        })

        result = grade(rca, truth)
        assert result["top1_correct"] is False
        assert result["top3_correct"] is True
        assert result["score"] == pytest_approx(0.5)


def pytest_approx(value, tol=1e-6):
    class _A:
        def __eq__(self, other):
            return abs(other - value) <= tol
    return _A()
