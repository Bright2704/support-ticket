---
marp: true
theme: default
paginate: true
backgroundColor: #fff
style: |
  section {
    font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
  }
  h1 { color: #2563eb; }
  h2 { color: #1e40af; }
  code { background: #f1f5f9; padding: 2px 8px; border-radius: 4px; }
  pre { background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 8px; }
  .columns { display: flex; gap: 20px; }
  .column { flex: 1; }
  strong { color: #dc2626; }
  .highlight { background: #fef3c7; padding: 10px; border-radius: 8px; }
---

# Customer Support Ticket Triage

## ระบบคัดแยก Support Ticket อัตโนมัติ

![bg right:40% 80%](https://img.icons8.com/fluency/512/artificial-intelligence.png)

**PRD-5** | Multi-Agent AI System

---

# ปัญหาที่ต้องแก้

## Support ticket เข้ามาเยอะมาก!

- เจ้าหน้าที่ต้องอ่านทีละใบ
- ต้องตัดสินใจเองว่าเป็นเรื่องอะไร
- บางทีส่งไปผิดทีม ต้องส่งใหม่
- Ticket ด่วนอาจถูกมองข้าม

![bg right:35% 90%](https://img.icons8.com/color/512/complaint.png)

---

# Solution: ใช้ AI ช่วยคัดแยก

## ระบบทำอะไรบ้าง?

| ทำอะไร | ตัวอย่าง |
|--------|----------|
| **จัดหมวดหมู่** | billing, technical, refund... |
| **กำหนดความเร่งด่วน** | P1 (ด่วนมาก) → P4 (ปกติ) |
| **ส่งต่อให้ทีมที่ถูกต้อง** | billing → ทีมบัญชี |
| **อ้างอิง Policy** | SLA-001, ESC-001... |

---

# ภาพรวมระบบ (System Flow)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ticket    │ --> │  Intent     │ --> │   Policy    │
│   Input     │     │  Router     │     │    RAG      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           v                   v
                    ┌─────────────┐     ┌─────────────┐
                    │  Priority   │ <-- │   Judge     │
                    │   Scorer    │     │   Agent     │
                    └─────────────┘     └─────────────┘
                           │
                           v
                    ┌─────────────┐
                    │   ผลลัพธ์    │
                    │ TriageResult│
                    └─────────────┘
```

---

# Tech Stack ที่ใช้

## เครื่องมือหลัก

| ส่วน | เทคโนโลยี | ทำไมถึงเลือก |
|------|-----------|-------------|
| **Backend** | FastAPI (Python) | เร็ว, เขียนง่าย |
| **Data Validation** | Pydantic | ตรวจสอบข้อมูลอัตโนมัติ |
| **Vector Search** | TF-IDF | ค้นหา Policy ที่เกี่ยวข้อง |
| **Frontend** | Next.js | UI สวย, ใช้งานง่าย |

---

# โครงสร้างโปรเจกต์

```
support-ticket/
├── app/
│   ├── schemas.py      # กำหนดรูปแบบข้อมูล
│   ├── main.py         # API endpoints
│   └── agents/
│       ├── pipeline.py # ควบคุม flow ทั้งหมด
│       ├── rules.py    # กฎการจัดหมวดหมู่
│       └── policy_rag.py # ค้นหา Policy
├── data/
│   └── policy_kb.json  # ฐานข้อมูล Policy
└── web/                # หน้าเว็บ UI
```

---

# 1. Schemas: กำหนดรูปแบบข้อมูล

## ข้อมูลเข้า (TicketInput)

```python
class TicketInput(BaseModel):
    subject: str      # หัวข้อ ticket
    body: str         # เนื้อหา ticket
    customer_tier: str | None  # ระดับลูกค้า
```

**ทำไมต้องมี?** → ทำให้ข้อมูลมีรูปแบบชัดเจน ป้องกัน error

---

# 1. Schemas: ผลลัพธ์ที่ได้

## ข้อมูลออก (TriageResult)

```python
class TriageResult(BaseModel):
    category: str           # หมวดหมู่ (billing, technical...)
    priority: str           # P1, P2, P3, P4
    assigned_queue: str     # ทีมที่รับผิดชอบ
    escalate: bool          # ต้อง escalate ไหม
    policy_citations: list  # Policy ที่อ้างอิง
    confidence: float       # ความมั่นใจ 0-1
```

---

# 2. API: จุดเชื่อมต่อระบบ

## FastAPI Endpoint

```python
@app.post("/tickets/triage")
def triage(ticket: TicketInput) -> TriageResult:
    """รับ ticket เข้ามา → ส่งผลลัพธ์กลับ"""
    return pipeline.triage_auto(ticket)
```

**ง่ายมาก!** แค่ 3 บรรทัด
- รับ ticket เข้ามา
- ส่งเข้า pipeline
- ส่งผลลัพธ์กลับ

---

# 3. Intent Router: จัดหมวดหมู่

## ใช้ Keyword Matching

```python
CATEGORY_KEYWORDS = {
    "billing": ["charge", "invoice", "payment", "ค่าบริการ"],
    "technical": ["error", "bug", "ล่ม", "ใช้งานไม่ได้"],
    "refund": ["refund", "money back", "คืนเงิน"],
    ...
}
```

**วิธีทำงาน:** นับว่า ticket มี keyword ของหมวดไหนมากที่สุด

---

# 3. Intent Router: ตัวอย่าง

## Input:
> "ระบบเรียกเก็บเงินผมสองครั้ง ช่วยคืนเงินด้วย"

## Process:
- พบ "เรียกเก็บเงิน" → **billing** (1 คะแนน)
- พบ "คืนเงิน" → **refund** (1 คะแนน)
- **เสมอกัน** → เลือก billing (มาก่อน)

## Output:
```
category: "billing"
sub_intent: "double_charge"
```

---

# 4. Policy RAG: ค้นหากฎที่เกี่ยวข้อง

## Policy KB (ฐานข้อมูลกฎ)

```json
{
  "policy_id": "SLA-001",
  "title": "Enterprise outage SLA",
  "snippet": "ลูกค้า Enterprise ที่ระบบล่ม
              ต้องตั้งเป็น P1 และ escalate ภายใน 15 นาที",
  "applies_to": ["technical"],
  "priority": "P1",
  "escalate": true
}
```

---

# 4. Policy RAG: วิธีการค้นหา

## TF-IDF Vector Search

```python
def search(query: str, k: int = 5) -> list[PolicyHit]:
    """ค้นหา Policy ที่ใกล้เคียงกับ query"""
    ranked = _store().query(query)  # คำนวณความคล้าย
    return [hit for hit in ranked if hit.score > 0.06]
```

**หลักการ:** แปลงข้อความเป็นตัวเลข → เปรียบเทียบความคล้าย

---

# 5. Priority Scorer: กำหนดความเร่งด่วน

## ตัดสินใจจาก Policy ที่เจอ

```python
def decide_priority(category, policies):
    priority = "P3"  # ค่าเริ่มต้น

    for pol in policies:
        if pol["priority"] == "P1":
            priority = "P1"  # ปรับเป็นด่วนที่สุด
        if pol["escalate"]:
            escalate = True  # ต้องส่งต่อหัวหน้า

    return priority, escalate
```

---

# 6. Judge Agent: ตรวจสอบความถูกต้อง

## ป้องกันการตัดสินใจผิดพลาด

```python
def run_judge(decision, policies):
    issues = []

    # ถ้า escalate แต่ไม่มี policy รองรับ = ผิด
    if decision.escalate and not policies:
        issues.append("escalation ไม่มี policy อ้างอิง")

    approved = len(issues) == 0
    return JudgeVerdict(approved=approved, issues=issues)
```

---

# ตัวอย่างการทำงานจริง

## Input Ticket:
> **Subject:** ระบบล่มมาสองวันแล้ว
> **Body:** ผมเป็นลูกค้า Enterprise ระบบใช้งานไม่ได้มาสองวันแล้ว ช่วยด่วนด้วย

---

# ตัวอย่าง: ผลลัพธ์

```json
{
  "category": "technical",
  "priority": "P1",
  "assigned_queue": "infra",
  "escalate": true,
  "policy_citations": ["SLA-001"],
  "confidence": 0.85,
  "internal_notes": "Enterprise outage - escalate immediately"
}
```

**ระบบตัดสินได้ถูกต้อง!** ลูกค้า Enterprise + ระบบล่ม = P1 + Escalate

---

# หน้าจอ Demo (Web UI)

## Next.js Frontend

- รองรับภาษาไทย/อังกฤษ
- มี template ตัวอย่าง ticket
- แสดงผลแบบ real-time
- ดู JSON response ได้

![bg right:45% 90%](https://img.icons8.com/color/512/web-design.png)

---

# Evaluation: วัดผลความแม่นยำ

## เป้าหมาย (PRD Section 7)

| Metric | เป้าหมาย | ความหมาย |
|--------|----------|----------|
| Category Accuracy | ≥ 85% | จัดหมวดถูก |
| Priority ±1 Level | ≥ 80% | P2 ผิดเป็น P1/P3 ยังโอเค |
| Escalation Recall | สูงที่สุด | ไม่พลาด case ด่วน |

---

# สรุป

## ระบบนี้ช่วยให้:

1. **จัดหมวดหมู่อัตโนมัติ** - ไม่ต้องอ่านเอง
2. **กำหนด Priority ถูกต้อง** - อ้างอิง Policy
3. **ส่งต่อทีมที่ถูกต้อง** - ลดเวลา
4. **ตรวจสอบได้** - มี confidence score

![bg right:30% 80%](https://img.icons8.com/fluency/512/checked-2.png)

---

# Q&A

## ขอบคุณครับ/ค่ะ

![bg right:50% 80%](https://img.icons8.com/fluency/512/questions.png)

**GitHub:** support-ticket
**Tech Stack:** FastAPI + Pydantic + Next.js
