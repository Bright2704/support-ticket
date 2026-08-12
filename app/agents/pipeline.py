"""
Triage pipeline — orchestrates the agents end to end.

Flow (matches docs/system_flow.mermaid):
    TicketInput
      -> Intent Router      (rules.classify)
      -> Domain Expert      (rules.* signal extraction)
      -> Policy RAG Agent   (rules.match_policies)
      -> Priority Scorer    (rules.decide_priority)
      -> Judge Agent        (validate routing vs citations)
      -> TriageResult

Today the agents are rule-based (see rules.py). Swapping in LLM agents later
means changing the bodies of these functions, not this orchestration.
"""

from __future__ import annotations

from ..schemas import (
    ExpertSignal,
    JudgeVerdict,
    PolicyHit,
    PriorityDecision,
    RouterOutput,
    TicketInput,
    TriageResult,
)
from . import policy_rag, rules


def run_router(ticket: TicketInput) -> RouterOutput:
    category, sub_intent, confidence = rules.classify(ticket.subject, ticket.body)
    return RouterOutput(
        category=category,
        sub_intent=sub_intent,
        confidence=confidence,
        is_multi_issue=rules.is_multi_issue(ticket.subject, ticket.body),
    )


def run_expert(ticket: TicketInput, routed: RouterOutput) -> list[ExpertSignal]:
    """Domain Expert stand-in: emit a couple of category-specific signals."""
    signals = [
        ExpertSignal(
            expert=routed.category.value,
            signal="sub_intent",
            value=routed.sub_intent,
            weight=1.0,
        )
    ]
    if ticket.customer_tier:
        signals.append(
            ExpertSignal(
                expert=routed.category.value,
                signal="customer_tier",
                value=ticket.customer_tier.value,
                weight=1.5,
            )
        )
    return signals


def run_policy_rag(ticket: TicketInput, routed: RouterOutput) -> list[PolicyHit]:
    """Policy RAG agent — real vector retrieval (see agents/policy_rag.py)."""
    tier = ticket.customer_tier.value if ticket.customer_tier else None
    return policy_rag.retrieve_for_ticket(
        ticket.subject, ticket.body, routed.category.value, tier
    )


def run_priority(
    ticket: TicketInput, routed: RouterOutput, policies: list[PolicyHit]
) -> PriorityDecision:
    tier = ticket.customer_tier.value if ticket.customer_tier else None
    raw_policies = [p.model_dump() for p in policies]
    # decide_priority needs the original KB rows (with priority/escalate fields).
    kb_rows = [pol for pol in rules.load_kb()["policies"] if pol["policy_id"] in {p["policy_id"] for p in raw_policies}]
    priority, escalate, justification = rules.decide_priority(
        routed.category.value, ticket.subject, ticket.body, tier, kb_rows
    )
    return PriorityDecision(priority=priority, escalate=escalate, justification=justification)


def run_judge(
    routed: RouterOutput, decision: PriorityDecision, policies: list[PolicyHit]
) -> JudgeVerdict:
    """Validate the routing against the cited policies (PRD section 8)."""
    issues: list[str] = []
    citations = [p.policy_id for p in policies]

    if decision.escalate and not citations:
        issues.append("escalation has no policy citation")
    if decision.priority == "P1" and not citations:
        issues.append("P1 assigned without supporting policy")

    approved = not issues
    # Lower confidence a bit when the judge is unhappy or the router was unsure.
    adjusted = routed.confidence if approved else max(0.0, routed.confidence - 0.3)
    return JudgeVerdict(approved=approved, issues=issues, adjusted_confidence=round(adjusted, 2))


def triage_auto(ticket: TicketInput) -> TriageResult:
    """Use the LLM pipeline when configured; fall back to rules otherwise.

    This is what the API calls. It never raises on LLM problems — it degrades
    to the deterministic rule-based pipeline so the service stays up.
    """
    from ..config import load_llm_config

    cfg = load_llm_config()
    if not cfg.configured:
        return triage(ticket)

    try:
        return _triage_llm(ticket)
    except Exception:  # noqa: BLE001 — any LLM/network error -> safe fallback
        return triage(ticket)


def _triage_llm(ticket: TicketInput) -> TriageResult:
    from . import llm_agents

    routed = llm_agents.route(ticket)
    try:
        signals = llm_agents.expert(ticket, routed)
    except Exception:  # noqa: BLE001 — expert is advisory; rules fallback
        signals = run_expert(ticket, routed)
    policies = run_policy_rag(ticket, routed)  # vector RAG
    decision, cited = llm_agents.score_priority(ticket, routed, policies)
    verdict = llm_agents.judge(routed, decision, cited)

    escalate = decision.escalate and bool(cited)
    signal_note = ", ".join(f"{s.signal}={s.value}" for s in signals if s.value) if signals else ""
    notes = (
        f"[LLM] router={routed.category.value}/{routed.sub_intent} "
        f"(conf {routed.confidence}); priority: {decision.justification}"
    )
    if signal_note:
        notes += f"; expert: {signal_note}"
    if verdict.issues:
        notes += f"; JUDGE FLAGS: {', '.join(verdict.issues)}"
    if routed.is_multi_issue:
        notes += "; multi-issue ticket — review manually"

    return TriageResult(
        category=routed.category,
        sub_intent=routed.sub_intent,
        priority=decision.priority,
        assigned_queue=rules.assign_queue(routed.category.value),
        suggested_macro_id=rules.suggest_macro(routed.category.value),
        internal_notes=notes,
        policy_citations=cited,
        confidence=verdict.adjusted_confidence,
        escalate=escalate,
    )


def triage(ticket: TicketInput) -> TriageResult:
    routed = run_router(ticket)
    _signals = run_expert(ticket, routed)
    policies = run_policy_rag(ticket, routed)
    decision = run_priority(ticket, routed, policies)
    verdict = run_judge(routed, decision, policies)

    citations = [p.policy_id for p in policies]
    # Guarantee the escalation-needs-citation invariant before constructing.
    escalate = decision.escalate and bool(citations)

    notes = (
        f"router={routed.category.value}/{routed.sub_intent} "
        f"(conf {routed.confidence}); priority: {decision.justification}"
    )
    if verdict.issues:
        notes += f"; JUDGE FLAGS: {', '.join(verdict.issues)}"
    if routed.is_multi_issue:
        notes += "; multi-issue ticket — review manually"

    return TriageResult(
        category=routed.category,
        sub_intent=routed.sub_intent,
        priority=decision.priority,
        assigned_queue=rules.assign_queue(routed.category.value),
        suggested_macro_id=rules.suggest_macro(routed.category.value),
        internal_notes=notes,
        policy_citations=citations,
        confidence=verdict.adjusted_confidence,
        escalate=escalate,
    )
