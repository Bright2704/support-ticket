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

from .agents import evaluate as evaluation
from .agents import pipeline, policy_rag
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
    return pipeline.triage_auto(ticket)


@app.post("/tickets/triage/batch", response_model=list[TriageResult])
def triage_batch(tickets: list[TicketInput]) -> list[TriageResult]:
    """Batch version of /tickets/triage."""
    return [pipeline.triage_auto(t) for t in tickets]


@app.get("/policies/search", response_model=list[PolicyHit])
def policies_search(q: str, k: int = 5) -> list[PolicyHit]:
    """RAG debug endpoint — vector-search the policy KB for a free-text query."""
    return policy_rag.search(q, k=k)


@app.post("/evaluate", response_model=EvaluationReport)
def evaluate() -> EvaluationReport:
    """Run the pipeline over the gold dataset and report accuracy (PRD section 7)."""
    return evaluation.run_evaluation()
