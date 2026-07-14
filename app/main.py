"""
FastAPI application.

The triage endpoints now run a real (rule-based) agent pipeline — see
app/agents/pipeline.py. It works fully offline with no API key. In weeks 6-8
the rule-based agents get swapped for LLM agents without touching this file.

Run locally:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI

from .agents import pipeline, rules
from .schemas import (
    EvaluationReport,
    PolicyHit,
    TicketInput,
    TriageResult,
)

app = FastAPI(
    title="Customer Support Ticket Triage",
    version="0.1.0",
    description="Classify, prioritise and route support tickets (PRD-5).",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tickets/triage", response_model=TriageResult)
def triage(ticket: TicketInput) -> TriageResult:
    """Single ticket -> routing decision."""
    return pipeline.triage(ticket)


@app.post("/tickets/triage/batch", response_model=list[TriageResult])
def triage_batch(tickets: list[TicketInput]) -> list[TriageResult]:
    """Batch version of /tickets/triage."""
    return [pipeline.triage(t) for t in tickets]


@app.get("/policies/search", response_model=list[PolicyHit])
def policies_search(q: str, k: int = 5) -> list[PolicyHit]:
    """RAG debug endpoint — returns the policy chunks a query would retrieve.

    Rule-based keyword match for now; swap for vector search in weeks 4-5.
    """
    hits = []
    for cat in ["billing", "technical", "refund", "account", "shipping", "other"]:
        for p in rules.match_policies(cat, q, q, None):
            if p["policy_id"] not in {h.policy_id for h in hits}:
                hits.append(PolicyHit(policy_id=p["policy_id"], title=p["title"], snippet=p["snippet"], score=1.0))
    return hits[:k]


@app.post("/evaluate", response_model=EvaluationReport)
def evaluate() -> EvaluationReport:
    """Run the pipeline over the gold dataset and report accuracy.

    Stub for now; implemented in week 8 once the pipeline exists.
    """
    return EvaluationReport(
        n=0,
        category_accuracy=0.0,
        priority_within_one_level=0.0,
        escalation_recall=0.0,
        passed=False,
    )
