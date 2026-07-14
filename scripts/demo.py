"""
Demo script — runs the 4 scenarios from the PRD demo script (section 10)
through the triage pipeline and prints the routing decisions.

Run from the project root:
    python scripts/demo.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import pipeline  # noqa: E402
from app.schemas import TicketInput  # noqa: E402

SCENARIOS = [
    TicketInput(
        subject="I was charged twice this month",
        body="My Pro plan shows two $20 charges. Please fix and refund one.",
        customer_tier="pro",
    ),
    TicketInput(
        subject="URGENT: production is down",
        body="Our whole team can't log in and the API returns 500 errors.",
        customer_tier="enterprise",
    ),
    TicketInput(
        subject="question",
        body="Hi, just wondering about a thing with my stuff.",
        customer_tier="free",
    ),
    TicketInput(
        subject="This is unacceptable, I want a refund",
        body="I am furious. The package never arrived and I want my money back or I'll cancel my account.",
        customer_tier="pro",
    ),
]


def main() -> None:
    for i, ticket in enumerate(SCENARIOS, 1):
        result = pipeline.triage(ticket)
        print(f"\n=== Scenario {i}: {ticket.subject!r} ===")
        print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
