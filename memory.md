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
- LLM: **Groq** (เลือกแล้ว, OpenAI-compatible, ฟรี) — ต่อโค้ดเสร็จแล้ว รอแค่ใส่ API key
  ยังรองรับ OpenAI/Ollama ได้ด้วย (provider-agnostic) · วิธีตั้งค่า: `SETUP_LLM.md`

## 4. สถานะปัจจุบัน (อัปเดต 2026-07-14)

| Week | Deliverable | สถานะ |
|------|-------------|-------|
| 2 | Data schema + system flow diagram | ✅ เสร็จ |
| 3 | /triage stub | ✅ เกินเป้า — เป็น pipeline จริง |
| 4-5 | Policy RAG (vector) | ✅ เสร็จ — vector search (TF-IDF cosine, รองรับ ChromaDB) `app/agents/policy_rag.py` |
| 6-7 | Router + expert agents (LLM) | ✅ Router/Expert/Priority/Judge เป็น LLM (Groq) ครบ + fallback |
| 8 | Judge + eval report | ✅ `/evaluate` จริง วัดกับ gold 30 ตัว (cat 100%, prio±1 90%, esc recall 100% บน rule engine) |
| 9-12 | Dashboard UI | 🟡 เว็บ demo (Next.js ไทย/อังกฤษ) ใน `web/` — ยังเป็น demo ไม่ใช่ dashboard เต็ม |

**สำคัญ:** รันได้ 2 โหมด — **offline rule-based** (ไม่ต้องมี key) และ **LLM (Groq)** เมื่อมี key
โดย schema/API เดิมไม่เปลี่ยน. RAG เป็น vector search จริงแล้ว (ไม่ใช่ keyword match)
Prompt แยกเป็นไฟล์ version ที่ `app/agents/prompts/*_v1.txt`

**ยังค้าง:** gold tickets + policy KB ของ *อาจารย์จริง* (ตอนนี้เป็น synthetic placeholder),
ยืนยัน schema กับ pre-defined shapes, และ dashboard UI เต็ม

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
