// Policy knowledge base for the triage demo (EN + TH triggers).
// Mirrors ../../data/policy_kb.json but with Thai keyword triggers added so the
// rule-based demo works for Thai tickets too. In the real project this is
// replaced by a vector store (ChromaDB) over the instructor's policy KB.

export const POLICIES = [
  {
    policy_id: "SLA-001",
    title: "Enterprise outage SLA",
    snippet:
      "Enterprise customers reporting a full service outage must be set to P1 and escalated to the infra on-call within 15 minutes.",
    applies_to: ["technical"],
    triggers: [
      "outage", "down", "500", "cannot log in", "can't log in", "not working",
      "ล่ม", "ใช้งานไม่ได้", "เข้าไม่ได้", "ระบบล้ม", "ล็อกอินไม่ได้", "เข้าสู่ระบบไม่ได้",
    ],
    tier: ["enterprise"],
    priority: "P1",
    escalate: true,
  },
  {
    policy_id: "SLA-002",
    title: "Billing dispute handling",
    snippet:
      "Billing disputes (double charge, wrong amount) are routed to the billing queue at P2. Refund eligibility is checked before any credit.",
    applies_to: ["billing"],
    triggers: [
      "charged twice", "double charge", "wrong amount", "overcharged", "billed",
      "เก็บเงินซ้ำ", "คิดเงินซ้ำ", "โดนชาร์จ", "ตัดบัตร", "ยอดผิด", "จ่ายซ้ำ",
    ],
    priority: "P2",
    escalate: false,
  },
  {
    policy_id: "SLA-003",
    title: "Refund request window",
    snippet:
      "Refund requests within 30 days are routed to the refunds queue at P3. Outside the window requires lead approval.",
    applies_to: ["refund"],
    triggers: [
      "refund", "money back", "cancel order", "return",
      "คืนเงิน", "เงินคืน", "ขอเงินคืน", "รีฟันด์", "ยกเลิกคำสั่งซื้อ", "คืนสินค้า",
    ],
    priority: "P3",
    escalate: false,
  },
  {
    policy_id: "SLA-004",
    title: "Account access default",
    snippet: "Account/login issues (non-outage) default to the account queue at P3.",
    applies_to: ["account"],
    triggers: [
      "password", "reset", "login", "2fa", "locked out",
      "รหัสผ่าน", "ลืมรหัส", "รีเซ็ตรหัส", "บัญชีถูกล็อก",
    ],
    priority: "P3",
    escalate: false,
  },
  {
    policy_id: "SLA-005",
    title: "Shipping inquiry default",
    snippet:
      "Shipping/delivery inquiries default to the logistics queue at P4 unless lost/damaged, then P3.",
    applies_to: ["shipping"],
    triggers: [
      "shipping", "delivery", "tracking", "package", "not arrived", "lost", "damaged",
      "จัดส่ง", "พัสดุ", "ขนส่ง", "ติดตามพัสดุ", "ยังไม่มาส่ง", "ไม่ได้รับของ", "ของหาย", "ชำรุด",
    ],
    priority: "P4",
    escalate: false,
  },
  {
    policy_id: "ESC-001",
    title: "Angry / churn-risk escalation",
    snippet:
      "Tickets with strong negative sentiment or explicit cancellation threats are bumped one priority level and flagged for lead review.",
    applies_to: ["billing", "technical", "refund", "account", "shipping", "other"],
    triggers: [
      "angry", "furious", "unacceptable", "terrible", "cancel my account", "lawyer", "sue",
      "แย่มาก", "รับไม่ได้", "โมโห", "โกรธ", "ยกเลิกบัญชี", "ฟ้อง", "ทนาย", "ห่วยแตก",
    ],
    priority: null,
    escalate: true,
  },
  {
    policy_id: "GEN-000",
    title: "Uncategorised default",
    snippet:
      "Tickets that do not match a known category are routed to the general queue at P3 for manual triage.",
    applies_to: ["other"],
    triggers: [],
    priority: "P3",
    escalate: false,
  },
];

export const QUEUES = {
  billing: "billing",
  technical: "infra",
  refund: "refunds",
  account: "account",
  shipping: "logistics",
  other: "general",
};

export const MACROS = {
  billing: "MACRO-BILL-01",
  technical: "MACRO-TECH-01",
  refund: "MACRO-REFUND-01",
  account: "MACRO-ACCT-01",
  shipping: "MACRO-SHIP-01",
  other: null,
};
