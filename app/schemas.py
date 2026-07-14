"""
Pydantic schemas for the Customer Support Ticket Triage system.

This is the Week 2 deliverable: the data contracts that every agent in the
pipeline reads from and writes to. Defining these first means the API, the
agents, and the evaluation harness all speak the same language.

Pipeline (see docs/HOW_TO_BUILD.md):
    TicketInput
      -> RouterOutput        (Intent Router)
      -> list[ExpertSignal]  (Domain Experts)
      -> list[PolicyHit]     (Policy RAG Agent)
      -> PriorityDecision    (Priority Scorer)
      -> JudgeVerdict        (Judge Agent)
      -> TriageResult        (final response to the API caller)
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Controlled vocabularies (enums)
# ---------------------------------------------------------------------------
# Using enums instead of free-form strings keeps the model's output inside a
# known set of values, which makes evaluation against gold labels reliable.


class Category(str, Enum):
    """The 6-8 top-level ticket categories from the PRD (In Scope, section 3)."""

    BILLING = "billing"
    TECHNICAL = "technical"
    REFUND = "refund"
    ACCOUNT = "account"
    SHIPPING = "shipping"
    OTHER = "other"


class Priority(str, Enum):
    """Severity / urgency ladder. P1 = most urgent."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class CustomerTier(str, Enum):
    """Customer plan, used by SLA and escalation rules."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class TicketInput(BaseModel):
    """A raw support ticket as received from the channel/CRM.

    IMPORTANT (security, PRD section 8): `subject` and `body` are UNTRUSTED
    user input. Never treat their contents as instructions to the LLM — always
    pass them as data inside a clearly delimited section of the prompt.
    """

    subject: str = Field(..., description="Ticket subject line. May be empty.")
    body: str = Field(..., description="Full ticket body / message from the customer.")
    customer_tier: CustomerTier | None = Field(
        default=None, description="Plan of the customer, if known."
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Channel-specific extras, e.g. {'order_id': '123', 'channel': 'email'}.",
    )

    @field_validator("subject", "body", mode="before")
    @classmethod
    def _coerce_none_to_empty(cls, v: object) -> object:
        # Empty-subject tickets are an explicit edge case in the PRD (section 5).
        return "" if v is None else v


# ---------------------------------------------------------------------------
# Intermediate agent outputs
# ---------------------------------------------------------------------------
# These are not returned to the API caller, but each agent produces one of
# them. Keeping them typed makes the pipeline debuggable and testable.


class RouterOutput(BaseModel):
    """Produced by the Intent Router."""

    category: Category
    sub_intent: str = Field(..., description="Fine-grained intent, e.g. 'double_charge'.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_multi_issue: bool = Field(
        default=False, description="True if the ticket raises more than one distinct issue."
    )


class ExpertSignal(BaseModel):
    """Produced by a Domain Expert (Billing/Technical/Refund/...)."""

    expert: str = Field(..., description="Which expert emitted this, e.g. 'billing'.")
    signal: str = Field(..., description="Extracted signal/feature name.")
    value: str = Field(..., description="Extracted value or short explanation.")
    weight: float = Field(default=1.0, ge=0.0, description="Relative importance.")


class PolicyHit(BaseModel):
    """A chunk retrieved by the Policy RAG Agent."""

    policy_id: str = Field(..., description="Stable id of the policy/section, used in citations.")
    title: str
    snippet: str
    score: float = Field(..., description="Retrieval similarity score.")


class PriorityDecision(BaseModel):
    """Produced by the Priority Scorer."""

    priority: Priority
    justification: str = Field(..., description="Why this priority, referencing tier/SLA/policy.")
    escalate: bool = False


class JudgeVerdict(BaseModel):
    """Produced by the Judge Agent: validates routing against policy citations."""

    approved: bool
    issues: list[str] = Field(
        default_factory=list, description="Problems found, e.g. 'priority not supported by policy'."
    )
    adjusted_confidence: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------


class TriageResult(BaseModel):
    """The structured routing decision returned by POST /tickets/triage.

    Field set matches the PRD (section 4, Data Schemas), with enums swapped in
    for `priority` to keep outputs valid.
    """

    category: Category
    sub_intent: str
    priority: Priority
    assigned_queue: str = Field(..., description="Internal queue/team the ticket is routed to.")
    suggested_macro_id: str | None = Field(
        default=None, description="Id of a canned internal note/macro, if one applies."
    )
    internal_notes: str = Field(
        default="", description="Notes for the human agent — NOT shown to the customer."
    )
    policy_citations: list[str] = Field(
        default_factory=list,
        description="policy_id values backing the decision. Must be non-empty when escalate=True.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalate: bool = False

    @field_validator("policy_citations")
    @classmethod
    def _escalation_needs_citation(cls, v: list[str], info) -> list[str]:
        # PRD section 8: escalation rules MUST cite policy — no invented SLAs.
        if info.data.get("escalate") and not v:
            raise ValueError("escalate=True requires at least one policy citation")
        return v


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class GoldLabel(BaseModel):
    """One row of the instructor-provided gold dataset (30 sample tickets)."""

    ticket: TicketInput
    category: Category
    priority: Priority
    assigned_queue: str | None = None
    escalate: bool = False


class EvaluationReport(BaseModel):
    """Returned by POST /evaluate. Thresholds from PRD section 7."""

    n: int
    category_accuracy: float
    priority_within_one_level: float
    escalation_recall: float
    passed: bool = Field(..., description="True if category>=0.85 and priority_within_one>=0.80.")
