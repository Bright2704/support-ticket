"""Tests for the pure-Python triage logic (no pydantic needed)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import rules


def test_billing_double_charge():
    cat, sub, conf = rules.classify("Charged twice", "Two charges of $20 on my card this month")
    assert cat == "billing"
    assert sub == "double_charge"
    assert conf > 0.5


def test_enterprise_outage_is_p1_escalation():
    pols = rules.match_policies("technical", "production is down", "API returns 500, can't log in", "enterprise")
    prio, esc, _ = rules.decide_priority("technical", "down", "500 can't log in", "enterprise", pols)
    assert prio == "P1"
    assert esc is True


def test_unknown_ticket_falls_back_to_other():
    cat, sub, conf = rules.classify("question", "wondering about a thing")
    assert cat == "other"
    assert conf < 0.5


def test_angry_ticket_bumps_priority():
    pols = rules.match_policies("refund", "unacceptable", "I am furious, money back or I cancel my account", "pro")
    prio, esc, reason = rules.decide_priority("refund", "unacceptable", "furious cancel my account", "pro", pols)
    assert esc is True
    assert prio in {"P1", "P2"}  # bumped up from the refund default of P3


def test_queue_assignment():
    assert rules.assign_queue("technical") == "infra"
    assert rules.assign_queue("refund") == "refunds"
