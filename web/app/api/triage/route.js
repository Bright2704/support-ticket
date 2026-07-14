// POST /api/triage  — { subject, body, customer_tier } -> TriageResult
// Runs the rule-based pipeline (lib/triage.mjs). No API key needed.

import { triage } from "../../../lib/triage.mjs";

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

  const result = triage({
    subject,
    body,
    customer_tier: payload.customer_tier ?? null,
  });

  return Response.json(result);
}
