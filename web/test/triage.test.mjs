// Offline unit test for the triage logic — run with: npm test  (or: node test/triage.test.mjs)
import { triage } from "../lib/triage.mjs";
import assert from "node:assert";

let passed = 0;
function check(name, fn) {
  fn();
  passed++;
  console.log("PASS", name);
}

check("EN billing double charge", () => {
  const r = triage({ subject: "Charged twice", body: "two $20 charges on my card", customer_tier: "pro" });
  assert.equal(r.category, "billing");
  assert.equal(r.priority, "P2");
});

check("EN enterprise outage -> P1 escalate", () => {
  const r = triage({ subject: "production is down", body: "can't log in, API 500", customer_tier: "enterprise" });
  assert.equal(r.category, "technical");
  assert.equal(r.priority, "P1");
  assert.equal(r.escalate, true);
  assert.ok(r.policy_citations.includes("SLA-001"));
});

check("TH billing double charge", () => {
  const r = triage({ subject: "โดนเก็บเงินซ้ำ", body: "โดนคิดค่าบริการซ้ำสองรอบ", customer_tier: "pro" });
  assert.equal(r.category, "billing");
  assert.equal(r.priority, "P2");
});

check("TH outage enterprise -> P1 escalate", () => {
  const r = triage({ subject: "ระบบล่ม", body: "ล็อกอินไม่ได้ ขึ้น error 500", customer_tier: "enterprise" });
  assert.equal(r.category, "technical");
  assert.equal(r.priority, "P1");
  assert.equal(r.escalate, true);
});

check("TH angry refund -> escalate + multi-issue", () => {
  const r = triage({ subject: "แย่มาก ขอเงินคืน", body: "โมโหมาก พัสดุไม่ได้รับของ ขอเงินคืนไม่งั้นจะยกเลิกบัญชี", customer_tier: "pro" });
  assert.equal(r.category, "refund");
  assert.equal(r.escalate, true);
  assert.ok(r.policy_citations.includes("ESC-001"));
});

check("TH password reset -> account P3", () => {
  const r = triage({ subject: "ลืมรหัสผ่าน", body: "เข้าสู่ระบบไม่ได้ ขอรีเซ็ตรหัส", customer_tier: "free" });
  assert.equal(r.category, "account");
  assert.equal(r.priority, "P3");
});

check("Ambiguous -> other, low confidence", () => {
  const r = triage({ subject: "question", body: "just wondering", customer_tier: "free" });
  assert.equal(r.category, "other");
  assert.ok(r.confidence < 0.5);
});

check("Escalation always has a citation", () => {
  const r = triage({ subject: "ระบบล่ม", body: "error 500", customer_tier: "enterprise" });
  if (r.escalate) assert.ok(r.policy_citations.length > 0);
});

console.log(`\n${passed} tests passed.`);
