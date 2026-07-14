// Rule-based triage pipeline (JS port, EN + TH).
// Mirrors the Python app/agents/{rules,pipeline}.py so the web demo runs the
// full architecture — Intent Router -> Domain Expert -> Policy RAG ->
// Priority Scorer -> Judge -> TriageResult — with no API key or backend.

import { POLICIES, QUEUES, MACROS } from "./policyKb.mjs";

const CATEGORY_KEYWORDS = {
  billing: [
    "charge", "charged", "invoice", "bill", "billed", "payment", "card", "subscription", "overcharged",
    "เรียกเก็บ", "คิดเงิน", "เก็บเงิน", "บิล", "ใบแจ้งหนี้", "ตัดบัตร", "ชำระเงิน", "ค่าบริการ", "ชาร์จ",
  ],
  technical: [
    "error", "bug", "down", "outage", "500", "crash", "not working", "can't log in", "cannot log in", "broken", "api",
    "ใช้งานไม่ได้", "ล่ม", "เข้าไม่ได้", "ระบบล้ม", "บั๊ก", "ขัดข้อง", "ล็อกอินไม่ได้", "เข้าสู่ระบบไม่ได้", "error",
  ],
  refund: [
    "refund", "money back", "return", "cancel order", "reimburse",
    "คืนเงิน", "เงินคืน", "ขอเงินคืน", "รีฟันด์", "ยกเลิกคำสั่งซื้อ", "คืนสินค้า",
  ],
  account: [
    "password", "reset", "login", "log in", "2fa", "locked out", "account access", "username",
    "รหัสผ่าน", "ลืมรหัส", "รีเซ็ตรหัส", "เข้าสู่ระบบ", "บัญชีถูกล็อก", "ชื่อผู้ใช้",
  ],
  shipping: [
    "shipping", "delivery", "tracking", "package", "parcel", "courier", "not arrived",
    "จัดส่ง", "พัสดุ", "ขนส่ง", "ติดตามพัสดุ", "ยังไม่มาส่ง", "ไม่ได้รับของ", "ของหาย",
  ],
};

const SUB_INTENT_KEYWORDS = {
  double_charge: ["charged twice", "double charge", "two charges", "billed twice", "เก็บเงินซ้ำ", "คิดเงินซ้ำ", "ตัดบัตรสองครั้ง", "จ่ายซ้ำ"],
  wrong_amount: ["wrong amount", "overcharged", "incorrect charge", "ยอดผิด", "คิดเงินเกิน"],
  service_outage: ["outage", "down", "500", "cannot log in", "can't log in", "not working", "ล่ม", "ใช้งานไม่ได้", "เข้าไม่ได้"],
  password_reset: ["password", "reset", "locked out", "2fa", "รหัสผ่าน", "ลืมรหัส", "รีเซ็ต"],
  refund_request: ["refund", "money back", "reimburse", "คืนเงิน", "เงินคืน", "ขอเงินคืน"],
  lost_package: ["not arrived", "lost", "missing package", "where is my", "ยังไม่มาส่ง", "ของหาย", "ไม่ได้รับ"],
};

const PRIORITY_ORDER = ["P1", "P2", "P3", "P4"];

function norm(subject, body) {
  return `${subject}\n${body}`.toLowerCase();
}

function countHits(text, keywords) {
  return keywords.reduce((n, kw) => (text.includes(kw.toLowerCase()) ? n + 1 : n), 0);
}

// --- Intent Router ---------------------------------------------------------
export function classify(subject, body) {
  const text = norm(subject, body);
  const scores = {};
  for (const [cat, kws] of Object.entries(CATEGORY_KEYWORDS)) scores[cat] = countHits(text, kws);

  const bestCat = Object.keys(scores).reduce((a, b) => (scores[b] > scores[a] ? b : a));
  const bestHits = scores[bestCat];

  if (bestHits === 0) return { category: "other", sub_intent: "unclassified", confidence: 0.3, scores };

  const ordered = Object.values(scores).sort((a, b) => b - a);
  const margin = ordered[0] - (ordered[1] ?? 0);
  const confidence = Math.min(0.95, 0.5 + 0.15 * bestHits + 0.1 * margin);

  let sub_intent = "general_inquiry";
  for (const [intent, kws] of Object.entries(SUB_INTENT_KEYWORDS)) {
    if (kws.some((kw) => text.includes(kw.toLowerCase()))) { sub_intent = intent; break; }
  }
  return { category: bestCat, sub_intent, confidence: Math.round(confidence * 100) / 100, scores };
}

// Tighter multi-issue: a *second* category must also have >= 2 keyword hits.
export function isMultiIssue(scores, bestCat) {
  return Object.entries(scores).some(([cat, n]) => cat !== bestCat && n >= 2);
}

// --- Policy RAG ------------------------------------------------------------
export function matchPolicies(category, subject, body, tier) {
  const text = norm(subject, body);
  const hits = [];
  for (const pol of POLICIES) {
    if (!pol.applies_to.includes(category)) continue;
    const triggerMatch = pol.triggers.length === 0 || pol.triggers.some((t) => text.includes(t.toLowerCase()));
    const tierOk = !pol.tier || pol.tier.includes(tier);
    if (triggerMatch && tierOk) hits.push(pol);
  }
  for (const pol of POLICIES) {
    if (pol.policy_id === "ESC-001" && pol.triggers.some((t) => text.includes(t.toLowerCase()))) {
      if (!hits.includes(pol)) hits.push(pol);
    }
  }
  return hits;
}

// --- Priority Scorer -------------------------------------------------------
export function decidePriority(category, subject, body, tier, policies) {
  let priority = "P3";
  let escalate = false;
  const reasons = [];

  for (const pol of policies) {
    if (pol.priority && PRIORITY_ORDER.indexOf(pol.priority) < PRIORITY_ORDER.indexOf(priority)) {
      priority = pol.priority;
      reasons.push(`${pol.policy_id} sets ${pol.priority}`);
    }
    if (pol.escalate) { escalate = true; reasons.push(`${pol.policy_id} requires escalation`); }
  }

  if (policies.some((p) => p.policy_id === "ESC-001")) {
    const idx = Math.max(0, PRIORITY_ORDER.indexOf(priority) - 1);
    if (PRIORITY_ORDER[idx] !== priority) {
      reasons.push(`bumped ${priority}->${PRIORITY_ORDER[idx]} (negative sentiment)`);
      priority = PRIORITY_ORDER[idx];
    }
  }
  if (reasons.length === 0) reasons.push("no specific SLA matched; default P3");
  return { priority, escalate, justification: reasons.join("; ") };
}

// --- Judge -----------------------------------------------------------------
export function judge(routed, decision, citations) {
  const issues = [];
  if (decision.escalate && citations.length === 0) issues.push("escalation has no policy citation");
  if (decision.priority === "P1" && citations.length === 0) issues.push("P1 assigned without supporting policy");
  const approved = issues.length === 0;
  const adjusted = approved ? routed.confidence : Math.max(0, routed.confidence - 0.3);
  return { approved, issues, adjusted_confidence: Math.round(adjusted * 100) / 100 };
}

// --- Full pipeline ---------------------------------------------------------
export function triage(ticket) {
  const subject = ticket.subject ?? "";
  const body = ticket.body ?? "";
  const tier = ticket.customer_tier ?? null;

  const routed = classify(subject, body);
  const multi = isMultiIssue(routed.scores, routed.category);
  const policies = matchPolicies(routed.category, subject, body, tier);
  const citations = policies.map((p) => p.policy_id);
  const decision = decidePriority(routed.category, subject, body, tier, policies);
  const verdict = judge(routed, decision, citations);

  const escalate = decision.escalate && citations.length > 0;

  let notes = `router=${routed.category}/${routed.sub_intent} (conf ${routed.confidence}); priority: ${decision.justification}`;
  if (verdict.issues.length) notes += `; JUDGE FLAGS: ${verdict.issues.join(", ")}`;
  if (multi) notes += "; multi-issue ticket — review manually";

  return {
    category: routed.category,
    sub_intent: routed.sub_intent,
    priority: decision.priority,
    assigned_queue: QUEUES[routed.category] ?? "general",
    suggested_macro_id: MACROS[routed.category] ?? null,
    internal_notes: notes,
    policy_citations: citations,
    policy_hits: policies.map((p) => ({ policy_id: p.policy_id, title: p.title, snippet: p.snippet })),
    confidence: verdict.adjusted_confidence,
    escalate,
    is_multi_issue: multi,
    judge_approved: verdict.approved,
  };
}
