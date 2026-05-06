"""Score RCA engine output against scenario ground truth.

Expected RCA output format (JSON):
{
  "incident_id": "...",
  "ranked_hypotheses": [
    {"entity_id": "port-tor-01-host-01-vmnic0", "score": 0.91, "rule": "R-MTU-001"},
    {"entity_id": "tep-host-01", "score": 0.05},
    ...
  ],
  "matched_anomalies": [
    {"entity": "port-tor-01-host-01-vmnic0", "metric": "in_errors"},
    ...
  ]
}

Truth file format: see scenarios.py return values.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path


def grade(rca_path: str, truth_path: str) -> dict:
    rca = json.loads(Path(rca_path).read_text())
    truth = json.loads(Path(truth_path).read_text())

    expected_root = truth["root_cause_entity"]
    expected_rule = truth.get("expected_rca_rule")
    expected_anomalies = truth.get("expected_anomalies", [])

    ranked = rca.get("ranked_hypotheses", [])
    if not ranked:
        return {
            "scenario": truth["scenario"],
            "top1_correct": False,
            "top3_correct": False,
            "top1_entity": None,
            "expected_root": expected_root,
            "rule_matched": False,
            "anomaly_recall": 0.0,
            "score": 0.0,
        }

    top1 = ranked[0]["entity_id"]
    top3 = [h["entity_id"] for h in ranked[:3]]

    top1_correct = top1 == expected_root
    top3_correct = expected_root in top3

    top_rule = ranked[0].get("rule")
    rule_matched = expected_rule == top_rule if expected_rule else False

    matched_set = set(
        (a.get("entity"), a.get("metric"))
        for a in rca.get("matched_anomalies", [])
    )
    expected_count = 0
    matched_count = 0
    for ea in expected_anomalies:
        expected_count += 1
        ent = ea.get("entity") or ea.get("entity_pattern", "")
        metric = ea.get("metric", "")
        for m_ent, m_metric in matched_set:
            if metric == m_metric and (
                m_ent == ent or fnmatch.fnmatch(m_ent or "", ent)
            ):
                matched_count += 1
                break
    anomaly_recall = matched_count / expected_count if expected_count else 1.0

    score = (
        (0.5 if top1_correct else 0.2 if top3_correct else 0.0)
        + (0.2 if rule_matched else 0.0)
        + 0.3 * anomaly_recall
    )

    return {
        "scenario": truth["scenario"],
        "top1_correct": top1_correct,
        "top3_correct": top3_correct,
        "top1_entity": top1,
        "expected_root": expected_root,
        "rule_matched": rule_matched,
        "anomaly_recall": round(anomaly_recall, 3),
        "score": round(score, 3),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Grade RCA output vs ground truth.")
    p.add_argument("rca_json", help="Path to RCA engine output")
    p.add_argument("truth_json", help="Path to scenario .truth.json")
    args = p.parse_args()

    result = grade(args.rca_json, args.truth_json)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["top1_correct"] else 1)


if __name__ == "__main__":
    main()
