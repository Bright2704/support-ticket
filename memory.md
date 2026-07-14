# Project Memory — Customer Support Ticket Triage

> ไฟล์นี้เก็บบริบทของโปรเจกต์ไว้ ใช้เป็นจุดเริ่มเวลากลับมาทำต่อ (หรือให้ AI ช่วยต่อ)
> อัปเดตทุกครั้งที่มีการตัดสินใจหรือความคืบหน้าใหม่

---

## 1. โปรเจกต์นี้คืออะไร

- **วิชา:** Building AI-Enabled Software Systems (term project, 12 สัปดาห์)
- **PRD:** PRD-5 — Customer Support Ticket Triage (pattern: Routing)
- **กลุ่ม:** 9, 4
- **เป้าหมาย:** ระบบ AI ที่รับ support ticket แล้ว **จัดหมวด + ให้ priority (P1–P4) + เลือกคิว +
  แนะนำ macro** ออกเป็น "คำตัดสินการ routing แบบมีโครงสร้าง" — **ไม่ใช่** บอทตอบลูกค้า
- **เกณฑ์ผ่าน:** category accuracy ≥ 85%, priority ถูกในระยะ 1 ระดับ ≥ 80%

## 2. สถาปัตยกรรม (multi-agent pipeline)

```
TicketInput → Intent Router → Domain Expert → Policy RAG → Priority Scorer → Judge → TriageResult
```
ดูภาพ: `docs/system_flow.mermaid` · วิธีสร้างทีละขั้น: `docs/HOW_TO_BUILD.md`

## 3. Tech stack

- Python 3.10+, **Pydantic v2**, **FastAPI**
- Orchestration: **LangChain / LangGraph** (จะใช้ตอน Week 6)
- Vector DB: **ChromaDB** (local) หรือ Pinecone (cloud)
- Eval: **Ragas / DeepEval**, trace ด้วย **LangSmith**
- LLM: OpenAI หรือ Anthropic — **ยังไม่ตัดสินใจ / ยังไม่มี API key** ⬅️ ต้องเลือก

## 4. สถานะปัจจุบัน (อัปเดต 2026-06-30)

| Week | Deliverable | สถานะ |
|------|-------------|-------|
| 2 | Data schema + system flow diagram | ✅ เสร็จ |
| 3 | /triage stub | ✅ เกินเป้า — ตอนนี้เป็น pipeline จริง (rule-based) |
| 4-5 | Policy RAG (vector) | ⬜ ตอนนี้เป็น keyword match ชั่วคราว |
| 6-7 | Router + expert agents (LLM) | ⬜ ตอนนี้เป็น rule-based |
| 8 | Judge + eval report | 🟡 Judge มีแล้ว (rule-based), eval ยังเป็น stub |
| 9-12 | Dashboard UI | 🟡 มีเว็บ demo แล้ว (Next.js, ไทย/อังกฤษ) ใน `web/` |

**สำคัญ:** ตอนนี้มี **MVP ที่รันได้จริงแบบ offline (ไม่ต้องใช้ API key)** — เป็น rule-based
ทุก agent เป็นฟังก์ชันใน `app/agents/rules.py` พอได้ API key แล้วค่อยสลับไส้ในเป็น LLM
โดย **schema และ API ไม่ต้องเปลี่ยน**

## 5. แผนผังไฟล์

```
app/
  schemas.py          # Pydantic contracts (TicketInput, TriageResult, + schema ทุก agent)
  main.py             # FastAPI: /tickets/triage, /batch, /policies/search, /evaluate
  agents/
    rules.py          # ตรรกะ triage แบบ pure-python (ไส้ในที่จะถูกแทนด้วย LLM)
    pipeline.py       # ต่อ agent เป็นสายท่อ -> TriageResult
data/
  policy_kb.json      # คลังนโยบาย (SLA, escalation, macro) — ตัวอย่าง ใช้แทนของอาจารย์
  sample_tickets.example.json
docs/
  HOW_TO_BUILD.md     # คู่มือสร้าง AI ทีละขั้น
  system_flow.mermaid # system flow diagram (Week 2)
web/                  # เว็บ demo Next.js (ส่ง ticket ไทย/อังกฤษ -> ผล triage)
  app/page.jsx        #   UI ฟอร์ม + แสดงผล
  app/api/triage/route.js  # POST /api/triage
  lib/triage.mjs      #   pipeline JS (EN+TH) mirror ของฝั่ง Python
  lib/policyKb.mjs    #   policy KB + triggers ไทย
  test/triage.test.mjs
scripts/
  demo.py             # รัน 4 ฉากตาม demo script ในโจทย์
tests/
  test_schemas.py     # ต้องมี pydantic
  test_rules.py       # pure-python รันได้เลย
AI_BUILD_SPEC.md      # ⭐ spec สำหรับต่อยอดเป็น LLM backend (อ่านก่อนเริ่มต่อ)
memory.md             # ไฟล์นี้
```

## 6. วิธีรัน

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/demo.py             # ดู 4 ฉากตัวอย่าง
uvicorn app.main:app --reload      # เปิด API ที่ /docs
pytest                             # รันเทสต์
```

## 7. การตัดสินใจที่ทำไปแล้ว (decisions)

- ใช้ **enum** สำหรับ category/priority/tier เพื่อบังคับให้ผลลัพธ์อยู่ในค่าที่ถูกต้อง (กัน LLM มั่ว)
- `TriageResult` มี validator: ถ้า `escalate=True` ต้องมี `policy_citations` อย่างน้อย 1 (ตาม PRD section 8)
- แยก **rules.py (pure logic)** ออกจาก **pipeline.py (schema/agent wrapper)** เพื่อให้รัน/เทสต์ได้
  โดยไม่ต้องมี LLM และสลับเป็น LLM ทีหลังได้ง่าย
- ทำ MVP เป็น rule-based ก่อน เพราะยังไม่มี API key — ได้ของที่ demo ได้ทันที

## 8. สิ่งที่ต้องทำต่อ / คำถามค้าง

1. **ขอไฟล์จากอาจารย์:** gold tickets 30 ตัว + policy KB จริง + tier definitions + edge cases →
   วางใน `data/` แล้วแทนที่ `policy_kb.json` ตัวอย่าง
2. **เลือก LLM provider** (OpenAI / Anthropic) + ขอ API key (ใส่เป็น env var ห้าม hardcode)
3. **เทียบ schema กับ "pre-defined Pydantic shapes" ของอาจารย์** ให้ตรงกัน (eval rubric อาจตรวจตามนั้น)
4. Week 4-5: เปลี่ยน `match_policies` จาก keyword → vector search (ChromaDB)
5. Week 6-7: เปลี่ยน `classify` / expert / priority จาก rule → LLM agent (LangGraph)
6. Week 8: เขียน `/evaluate` จริงให้วัดกับ gold dataset
```
```
