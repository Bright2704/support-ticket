"""Quick checks that the Week 2 schemas behave as intended."""

import pytest
from pydantic import ValidationError

from app.schemas import TicketInput, TriageResult


def test_ticket_input_minimal():
    t = TicketInput(subject="Charged twice", body="I was billed two times this month.")
    assert t.customer_tier is None
    assert t.metadata is None


def test_empty_subject_edge_case():
    # PRD edge case: empty subject should not crash.
    t = TicketInput(subject=None, body="no subject here")  # type: ignore[arg-type]
    assert t.subject == ""


def test_triage_result_ok():
    r = TriageResult(
        category="billing",
        sub_intent="double_charge",
        priority="P2",
        assigned_queue="billing",
        confidence=0.91,
    )
    assert r.escalate is False
    assert r.policy_citations == []


def test_escalation_requires_citation():
    with pytest.raises(ValidationError):
        TriageResult(
            category="technical",
            sub_intent="outage",
            priority="P1",
            assigned_queue="infra",
            confidence=0.95,
            escalate=True,          # escalate but no citation -> must fail
            policy_citations=[],
        )


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        TriageResult(
            category="not_a_real_category",
            sub_intent="x",
            priority="P3",
            assigned_queue="general",
            confidence=0.5,
        )
