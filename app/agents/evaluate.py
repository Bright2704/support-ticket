"""
Evaluation harness (Week 8 deliverable).

Runs the triage pipeline over a gold dataset and reports the PRD acceptance
metrics:
    * category_accuracy         — exact-match on category      (target >= 0.85)
    * priority_within_one_level — |P_pred - P_gold| <= 1 level  (target >= 0.80)
    * escalation_recall         — of gold escalations, how many we caught

`passed` is True when the two hard targets are met.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from ..schemas import EvaluationReport, GoldLabel, TicketInput, TriageResult
from . import pipeline

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_GOLD_PATH = os.path.join(_DATA_DIR, "gold_tickets.json")

_PRIORITY_INDEX = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}

CATEGORY_TARGET = 0.85
PRIORITY_TARGET = 0.80


def load_gold(path: str | None = None) -> list[GoldLabel]:
    with open(path or _GOLD_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data["tickets"] if isinstance(data, dict) else data
    gold: list[GoldLabel] = []
    for row in rows:
        gold.append(
            GoldLabel(
                ticket=TicketInput(**row["ticket"]),
                category=row["category"],
                priority=row["priority"],
                assigned_queue=row.get("assigned_queue"),
                escalate=bool(row.get("escalate", False)),
            )
        )
    return gold


def run_evaluation(
    path: str | None = None,
    triage_fn: Callable[[TicketInput], TriageResult] = pipeline.triage_auto,
) -> EvaluationReport:
    """Score `triage_fn` against the gold set. Defaults to the live pipeline."""
    gold = load_gold(path)
    if not gold:
        return EvaluationReport(
            n=0, category_accuracy=0.0, priority_within_one_level=0.0,
            escalation_recall=0.0, passed=False,
        )

    cat_hits = 0
    prio_hits = 0
    esc_true_positive = 0
    esc_gold_total = 0

    for row in gold:
        result = triage_fn(row.ticket)

        if result.category == row.category:
            cat_hits += 1

        gap = abs(_PRIORITY_INDEX[result.priority.value] - _PRIORITY_INDEX[row.priority.value])
        if gap <= 1:
            prio_hits += 1

        if row.escalate:
            esc_gold_total += 1
            if result.escalate:
                esc_true_positive += 1

    n = len(gold)
    category_accuracy = cat_hits / n
    priority_within_one_level = prio_hits / n
    # Recall is undefined with no positives; report 1.0 by convention.
    escalation_recall = (esc_true_positive / esc_gold_total) if esc_gold_total else 1.0

    passed = category_accuracy >= CATEGORY_TARGET and priority_within_one_level >= PRIORITY_TARGET

    return EvaluationReport(
        n=n,
        category_accuracy=round(category_accuracy, 4),
        priority_within_one_level=round(priority_within_one_level, 4),
        escalation_recall=round(escalation_recall, 4),
        passed=passed,
    )
