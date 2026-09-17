# Customer Support Ticket Triage (PRD-5)

ระบบคัดแยกและจัดเส้นทาง support ticket อัตโนมัติ ด้วย multi-agent + RAG
**ไม่ใช่** บอทตอบลูกค้า แต่ออก "คำตัดสินการ routing แบบมีโครงสร้าง" ให้เจ้าหน้าที่

## โครงสร้างโปรเจกต์

```
.
├── app/
│   ├── schemas.py        # Pydantic data contracts  ← งาน Week 2 (เสร็จแล้ว)
│   ├── main.py           # FastAPI endpoints (stub)  ← Week 3
│   └── agents/           # โค้ดของแต่ละ agent         ← Week 6-8
├── data/                 # gold tickets + policy KB (อาจารย์ให้)
├── docs/
│   ├── HOW_TO_BUILD.md   # คู่มือสร้าง AI แบบทีละขั้น  ← อ่านอันนี้
│   └── system_flow.mermaid  # system flow diagram      ← งาน Week 2
├── tests/
└── requirements.txt
```

## เริ่มใช้งาน

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# รัน API (ตอนนี้เป็น stub)
uvicorn app.main:app --reload
# เปิด http://127.0.0.1:8000/docs

# รันเทสต์
pytest
```

## สถานะตาม milestone (PRD section 9)

| Week | Deliverable | สถานะ |
|------|-------------|-------|
| 2 | Data schema + system flow diagram | ✅ เสร็จ |
| 3 | /triage stub | ✅ เสร็จ |
| 4-5 | Policy RAG ingestion | ✅ เสร็จ (`app/agents/policy_rag.py`) |
| 6-7 | Router + expert agents | ✅ เสร็จ (`app/agents/llm_agents.py`) |
| 8 | Judge + eval report | ✅ เสร็จ (`app/agents/evaluate.py`) |
| 9-12 | Agent dashboard UI | ✅ เสร็จ (`web/`) |

ดูวิธีทำแต่ละขั้นใน [`docs/HOW_TO_BUILD.md`](docs/HOW_TO_BUILD.md)

**จะต่อยอดเป็น LLM backend?** อ่าน [`AI_BUILD_SPEC.md`](AI_BUILD_SPEC.md) ก่อน — เป็น spec ที่บอกเป้าหมายระบบ, contract ที่ห้ามแก้, และ checklist งานที่ต้องทำเพื่อเปลี่ยนจาก rule-based ไปใช้ LLM จริง
