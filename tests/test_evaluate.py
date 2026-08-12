"""Integration test: run the rule-based pipeline over the gold set and check
it meets the PRD acceptance thresholds (category >= 0.85, priority >= 0.80)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import evaluate, pipeline


def test_gold_set_loads_30_rows():
    gold = evaluate.load_gold()
    assert len(gold) == 30


def test_rule_pipeline_meets_thresholds():
    # Force the deterministic rule pipeline (no API key needed) for a stable CI.
    report = evaluate.run_evaluation(triage_fn=pipeline.triage)
    assert report.n == 30
    assert report.category_accuracy >= 0.85, report
    assert report.priority_within_one_level >= 0.80, report
    assert report.escalation_recall >= 0.80, report
    assert report.passed is True
