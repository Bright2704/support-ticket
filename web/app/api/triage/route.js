// POST /api/triage  — { subject, body, customer_tier } -> TriageResult
//
// Uses the LLM pipeline when an API key is configured (see web/.env.local),
// otherwise falls back to the rule-based pipeline. Either way the response
// shape is the same, plus an `engine` field ("llm" | "rules") so the UI can
// show which one processed the ticket.

import { triageLLM } from "../../../lib/llmTriage.mjs";

export async function POST(request) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const subject = typeof payload.subject === "string" ? payload.subject : "";
  const body = typeof payload.body === "string" ? payload.body : "";

  if (!subject.trim() && !body.trim()) {
    return Response.json({ error: "subject or body is required" }, { status: 422 });
  }

  try {
    const result = await triageLLM({
      subject,
      body,
      customer_tier: payload.customer_tier ?? null,
    });
    return Response.json(result);
  } catch (err) {
    return Response.json({ error: String(err.message || err) }, { status: 500 });
  }
}
