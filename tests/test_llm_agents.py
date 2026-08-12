"""Unit tests for the LLM agents, with the network call mocked out.

We patch `llm_agents.call_llm_json` so no API key or network is needed; the
tests check that each agent parses/validates the model output correctly and
enforces its guardrails (enum clamping, citation filtering, weight coercion).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import llm_agents
from app.schemas import PolicyHit, PriorityDecision, RouterOutput, TicketInput


def _ticket():
    return TicketInput(subject="s", body="b", customer_tier="pro")


def test_router_parses_and_clamps(monkeypatch):
    monkeypatch.setattr(
        llm_agents, "call_llm_json",
        lambda *a, **k: {"category": "billing", "sub_intent": "double_charge", "confidence": 1.4, "is_multi_issue": True},
    )
    out = llm_agents.route(_ticket())
    assert out.category.value == "billing"
    assert out.sub_intent == "double_charge"
    assert out.confidence == 1.0  # clamped into 0..1
    assert out.is_multi_issue is True


def test_router_bad_category_falls_back_to_other(monkeypatch):
    monkeypatch.setattr(llm_agents, "call_llm_json", lambda *a, **k: {"category": "nonsense", "confidence": 0.9})
    out = llm_agents.route(_ticket())
    assert out.category.value == "other"


def test_expert_returns_signals(monkeypatch):
    monkeypatch.setattr(
        llm_agents, "call_llm_json",
        lambda *a, **k: {"signals": [{"signal": "amount", "value": "$40", "weight": "2"}, {"bad": "row"}]},
    )
    routed = RouterOutput(category="billing", sub_intent="x", confidence=0.9)
    signals = llm_agents.expert(_ticket(), routed)
    assert len(signals) == 1
    assert signals[0].signal == "amount"
    assert signals[0].weight == 2.0  # coerced from string


def test_priority_filters_uncited_policies(monkeypatch):
    monkeypatch.setattr(
        llm_agents, "call_llm_json",
        lambda *a, **k: {"priority": "P1", "escalate": True, "cited_policy_ids": ["SLA-001", "HALLUCINATED"], "justification": "j"},
    )
    routed = RouterOutput(category="technical", sub_intent="outage", confidence=0.9)
    policies = [PolicyHit(policy_id="SLA-001", title="t", snippet="s", score=0.5)]
    decision, cited = llm_agents.score_priority(_ticket(), routed, policies)
    assert decision.priority.value == "P1"
    assert cited == ["SLA-001"]  # invented id dropped


def test_judge_clamps_confidence(monkeypatch):
    monkeypatch.setattr(
        llm_agents, "call_llm_json",
        lambda *a, **k: {"approved": False, "issues": ["no citation"], "adjusted_confidence": -3},
    )
    routed = RouterOutput(category="billing", sub_intent="x", confidence=0.8)
    decision = PriorityDecision(priority="P1", justification="j", escalate=True)
    verdict = llm_agents.judge(routed, decision, [])
    assert verdict.approved is False
    assert verdict.adjusted_confidence == 0.0
