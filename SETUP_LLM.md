# ตั้งค่า LLM (Groq) ให้ระบบประมวลผลด้วย AI จริง

ระบบต่อ LLM ให้แล้ว รองรับทั้ง **เว็บ (Next.js)** และ **backend (FastAPI)**
ค่าเริ่มต้นคือ **Groq** (ฟรี, เร็ว) และถ้าไม่มีคีย์ ระบบจะ **ถอยกลับเป็น rule-based อัตโนมัติ** ไม่พัง

---

## ขั้นที่ 1 — ขอ API key ฟรีจาก Groq

1. เข้า **https://console.groq.com** แล้วล็อกอิน (ใช้ Google/GitHub ได้ ฟรี ไม่ต้องใส่บัตร)
2. เมนูซ้าย → **API Keys** → **Create API Key**
3. ตั้งชื่อ (อะไรก็ได้) แล้วกดสร้าง → **คัดลอกคีย์** (ขึ้นต้นด้วย `gsk_...`)
   > ⚠️ คีย์จะแสดงครั้งเดียว ถ้าหายให้สร้างใหม่ · **อย่าเอาคีย์ไปแชร์/commit ขึ้น git**

---

## ขั้นที่ 2 — ใส่คีย์แล้วรัน

### ก) เว็บ (Next.js) — แนะนำสำหรับ demo

```bash
cd "web"
cp .env.local.example .env.local     # สร้างไฟล์จริงจากตัวอย่าง
# เปิด .env.local แล้ววาง key ตรง GROQ_API_KEY=gsk_...
npm install
npm run dev                          # http://localhost:3000
```

ส่ง ticket แล้วดูป้ายมุมผลลัพธ์:
- **🤖 LLM** = ประมวลผลด้วย Groq สำเร็จ
- **⚙️ rule-based** = ยังไม่มีคีย์/LLM มีปัญหา (fallback)

### ข) Backend (FastAPI) — สำหรับส่งงานตามหลักสูตร

```bash
cp .env.example .env                 # ที่ root ของโปรเจกต์
# เปิด .env แล้ววาง GROQ_API_KEY=gsk_...
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
```

ลองยิงที่ `/docs` → `POST /tickets/triage` ผลลัพธ์ `internal_notes` จะขึ้น `[LLM] ...` เมื่อใช้ AI

---

## เปลี่ยน provider (ถ้าต้องการ)

แก้ใน `.env` / `.env.local`:

```bash
# OpenAI (เสียเงิน)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Ollama (รันในเครื่อง ฟรี ไม่ต้องคีย์ — ต้องมี `ollama serve`)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
```

โค้ดเป็น **provider-agnostic** (รองรับทุก endpoint แบบ OpenAI-compatible) เปลี่ยนแค่ env ไม่ต้องแก้โค้ด

---

## ระบบทำงานยังไงเมื่อเปิด LLM

```
ticket → [LLM] Intent Router → ค้น policy (keyword RAG) →
         [LLM] Priority Scorer → [LLM] Judge → TriageResult
```

- ทุก agent ถูกบังคับให้ตอบเป็น **JSON** (structured output) แล้ว validate — ถ้าเพี้ยนจะ retry
- มี **guardrail กัน prompt injection** (ครอบ ticket ด้วย `<ticket>` + สั่งห้ามทำตามคำสั่งในเนื้อความ)
- การ escalate/P1 ต้อง **อ้าง policy_id จริง** ที่ค้นเจอ ไม่งั้น Judge จะทัก
- ผิดพลาดเมื่อไหร่ (ไม่มีคีย์/เน็ตหลุด/quota หมด) → **fallback rule-based** อัตโนมัติ

> อยากเปลี่ยน RAG จาก keyword เป็น vector search จริง (ChromaDB) และทำ `/evaluate`
> ให้วัดกับ gold dataset — ดูขั้นตอนใน `AI_BUILD_SPEC.md` ข้อ 6 และ 8
