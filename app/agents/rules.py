"""
Rule-based triage logic — the "brains" of the MVP.

This module is INTENTIONALLY pure Python (no Pydantic, no LLM, no network) so
the whole pipeline runs offline and is easy to unit-test. In weeks 6-8 each
function here gets replaced by an LLM-backed agent that returns the SAME shape
(see docs/HOW_TO_BUILD.md). The schemas and the API don't change — only the
guts of these functions do.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_KB_PATH = os.path.join(_DATA_DIR, "policy_kb.json")

# Keyword cues per category. Order matters: first category with the most hits
# wins. This is a deliberately simple stand-in for the LLM Intent Router.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "billing": ["charge", "charged", "invoice", "bill", "billed", "payment", "card", "subscription", "overcharged",
                "เรียกเก็บ", "ค่าบริการ", "บิล", "ใบแจ้งหนี้", "ตัดเงิน", "ตัดบัตร", "คิดเงิน", "ชำระเงิน"],
    "technical": ["error", "bug", "down", "outage", "500", "crash", "not working", "can't log in", "cannot log in", "broken", "api",
                  "ล่ม", "ใช้งานไม่ได้", "ระบบล่ม", " error", "ขัดข้อง", "เข้าไม่ได้", "แอปพัง", "บั๊ก"],
    "refund": ["refund", "money back", "return", "cancel order", "reimburse",
               "คืนเงิน", "ขอเงินคืน", "ยกเลิกคำสั่งซื้อ", "รีฟันด์"],
    "account": ["password", "reset", "login", "log in", "2fa", "locked out", "account access", "username",
                "รหัสผ่าน", "ลืมรหัส", "ล็อกอิน", "เข้าสู่ระบบ", "บัญชีถูกล็อก", "รีเซ็ตรหัส"],
    "shipping": ["shipping", "delivery", "tracking", "package", "parcel", "courier", "not arrived",
                 "จัดส่ง", "พัสดุ", "ติดตามพัสดุ", "ของยังไม่มาถึง", "ขนส่ง", "เลขพัสดุ", "ไม่ได้รับของ"],
}

# Sub-intent cues -> a short label.
SUB_INTENT_KEYWORDS: dict[str, list[str]] = {
    "double_charge": ["charged twice", "double charge", "two charges", "billed twice", "ตัดเงินสองครั้ง", "เรียกเก็บซ้ำ", "คิดเงินสองรอบ"],
    "wrong_amount": ["wrong amount", "overcharged", "incorrect charge", "ยอดผิด", "เก็บเงินเกิน", "จำนวนเงินผิด"],
    "service_outage": ["outage", "down", "500", "cannot log in", "can't log in", "not working", "ล่ม", "ระบบล่ม", "ใช้งานไม่ได้", "เข้าไม่ได้"],
    "password_reset": ["password", "reset", "locked out", "2fa", "รหัสผ่าน", "ลืมรหัส", "รีเซ็ตรหัส", "บัญชีถูกล็อก"],
    "refund_request": ["refund", "money back", "reimburse", "คืนเงิน", "ขอเงินคืน"],
    "lost_package": ["not arrived", "lost", "missing package", "where is my", "ยังไม่มาถึง", "ของหาย", "พัสดุหาย", "ไม่ได้รับของ"],
}

PRIORITY_ORDER = ["P1", "P2", "P3", "P4"]


@lru_cache(maxsize=1)
def load_kb() -> dict:
    with open(_KB_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _text(subject: str, body: str) -> str:
    return f"{subject}\n{body}".lower()


def classify(subject: str, body: str) -> tuple[str, str, float]:
    """Intent Router stand-in -> (category, sub_intent, confidence)."""
    text = _text(subject, body)

    scores = {
        cat: sum(1 for kw in kws if kw in text)
        for cat, kws in CATEGORY_KEYWORDS.items()
    }
    best_cat = max(scores, key=scores.get)
    best_hits = scores[best_cat]

    if best_hits == 0:
        return "other", "unclassified", 0.30

    # Confidence grows with hit count and with the margin over the runner-up.
    ordered = sorted(scores.values(), reverse=True)
    margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0)
    confidence = min(0.95, 0.5 + 0.15 * best_hits + 0.1 * margin)

    sub_intent = "general_inquiry"
    for intent, kws in SUB_INTENT_KEYWORDS.items():
        if any(kw in text for kw in kws):
            sub_intent = intent
            break

    return best_cat, sub_intent, round(confidence, 2)


def is_multi_issue(subject: str, body: str) -> bool:
    """Rough multi-issue detector (PRD edge case)."""
    text = _text(subject, body)
    hit_categories = sum(
        1 for kws in CATEGORY_KEYWORDS.values() if any(kw in text for kw in kws)
    )
    return hit_categories >= 2


def match_policies(category: str, subject: str, body: str, tier: str | None) -> list[dict]:
    """Policy RAG stand-in: keyword match instead of vector search."""
    text = _text(subject, body)
    hits: list[dict] = []
    for pol in load_kb()["policies"]:
        if category not in pol["applies_to"]:
            continue
        trigger_match = (not pol["triggers"]) or any(t in text for t in pol["triggers"])
        tier_ok = ("tier" not in pol) or (tier in pol.get("tier", []))
        if trigger_match and tier_ok:
            hits.append(pol)

    # Sentiment/churn escalation policy applies across categories.
    for pol in load_kb()["policies"]:
        if pol["policy_id"] == "ESC-001" and any(t in text for t in pol["triggers"]):
            if pol not in hits:
                hits.append(pol)
    return hits


def decide_priority(
    category: str, subject: str, body: str, tier: str | None, policies: list[dict]
) -> tuple[str, bool, str]:
    """Priority Scorer stand-in -> (priority, escalate, justification)."""
    # Start from the strongest priority any matched policy demands.
    priority = "P3"
    escalate = False
    reasons: list[str] = []

    for pol in policies:
        if pol.get("priority"):
            if PRIORITY_ORDER.index(pol["priority"]) < PRIORITY_ORDER.index(priority):
                priority = pol["priority"]
                reasons.append(f"{pol['policy_id']} sets {pol['priority']}")
        if pol.get("escalate"):
            escalate = True
            reasons.append(f"{pol['policy_id']} requires escalation")

    # Churn/anger bumps one level up (toward P1).
    if any(p["policy_id"] == "ESC-001" for p in policies):
        idx = max(0, PRIORITY_ORDER.index(priority) - 1)
        if PRIORITY_ORDER[idx] != priority:
            reasons.append(f"bumped {priority}->{PRIORITY_ORDER[idx]} (negative sentiment)")
            priority = PRIORITY_ORDER[idx]

    if not reasons:
        reasons.append("no specific SLA matched; default P3")

    return priority, escalate, "; ".join(reasons)


def assign_queue(category: str) -> str:
    return load_kb()["queues"].get(category, "general")


def suggest_macro(category: str) -> str | None:
    return load_kb()["macros"].get(category)
