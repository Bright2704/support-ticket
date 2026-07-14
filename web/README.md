# Ticket Triage Console (Next.js demo)

หน้าเว็บสำหรับ **ส่ง support ticket จำลอง (ไทย/อังกฤษ) แล้วดูผลการ routing อัตโนมัติ**
ครอบคลุม pipeline ทั้งหมดของ PRD-5: Intent Router → Domain Expert → Policy RAG →
Priority Scorer → Judge → `TriageResult`

ประมวลผลจริงในตัวเอง (rule-based) — **ไม่ต้องใช้ API key และไม่ต้องรัน Python backend**

## วิธีรัน

```bash
cd web
npm install
npm run dev
# เปิด http://localhost:3000
```

รันเทสต์ตรรกะ (ไม่ต้องมี Next):

```bash
npm test      # หรือ node test/triage.test.mjs
```

## โครงสร้าง

```
web/
├── app/
│   ├── page.jsx            # UI: ฟอร์มส่ง ticket + แสดงผล
│   ├── layout.jsx          # ฟอนต์ Inter + Noto Sans Thai
│   ├── globals.css         # design system (ธีม minimal SaaS)
│   └── api/triage/route.js # POST /api/triage -> เรียก pipeline
├── lib/
│   ├── triage.mjs          # pipeline (EN + TH) — mirror ของ Python app/agents/
│   └── policyKb.mjs         # policy KB (SLA/escalation/macro) + triggers ไทย
└── test/triage.test.mjs    # unit test (8 เคส ไทย/อังกฤษ)
```

## หมายเหตุด้านสถาปัตยกรรม

- ตรรกะใน `lib/triage.mjs` เป็น **rule-based** (keyword) เพื่อให้ demo ได้ทันทีแบบ offline
  ตรง concept เดียวกับฝั่ง Python (`app/agents/`)
- ในโปรเจกต์จริง (Week 6+) จะสลับไส้ในเป็น **LLM agent** โดย UI และรูปแบบผลลัพธ์ไม่ต้องเปลี่ยน
- ถ้าต้องการให้เว็บเรียก FastAPI backend จริงแทน ก็เปลี่ยนแค่ `app/api/triage/route.js`
  ให้ proxy ไปที่ `POST /tickets/triage` ของฝั่ง Python
