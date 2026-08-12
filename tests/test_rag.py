"""Tests for the vector Policy RAG agent (agents/policy_rag.py)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import policy_rag


def test_search_ranks_relevant_policy_first():
    hits = policy_rag.search("service outage, everything is down and returns 500")
    assert hits, "expected at least one hit"
    assert hits[0].policy_id == "SLA-001"
    assert hits[0].score > 0


def test_search_is_not_pure_substring():
    # No literal KB trigger word appears here, but vector similarity should
    # still surface the billing dispute policy (SLA-002).
    hits = policy_rag.search("I got two charges for one subscription", category="billing")
    ids = {h.policy_id for h in hits}
    assert "SLA-002" in ids


def test_metadata_filter_by_category():
    hits = policy_rag.search("refund my money back please", category="refund")
    assert all(h.policy_id != "SLA-001" for h in hits)  # SLA-001 is technical-only


def test_thai_query_retrieves_policy():
    hits = policy_rag.search("ระบบล่ม ใช้งานไม่ได้ เข้าไม่ได้", category="technical", tier="enterprise")
    assert any(h.policy_id == "SLA-001" for h in hits)


def test_tier_filter_excludes_enterprise_only_policy():
    hits = policy_rag.search("outage down 500", category="technical", tier="free")
    assert all(h.policy_id != "SLA-001" for h in hits)


def test_angry_ticket_retrieves_escalation_policy():
    hits = policy_rag.retrieve_for_ticket(
        "unacceptable", "I am furious, cancel my account or I sue you", "billing", "pro"
    )
    assert any(h.policy_id == "ESC-001" for h in hits)
