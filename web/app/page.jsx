"use client";

import { useState } from "react";

const SAMPLES = [
  {
    label: "🇹🇭 โดนเก็บเงินซ้ำ",
    subject: "โดนเก็บเงินซ้ำ",
    body: "เดือนนี้โดนคิดค่าบริการซ้ำสองรอบ ช่วยตรวจสอบและคืนเงินให้ด้วยครับ",
    customer_tier: "pro",
  },
  {
    label: "🇹🇭 ระบบล่ม (องค์กร)",
    subject: "ระบบล่ม เข้าใช้งานไม่ได้",
    body: "ทั้งทีมล็อกอินไม่ได้เลย ขึ้น error 500 ตลอด เราเป็นลูกค้าองค์กร ด่วนมาก",
    customer_tier: "enterprise",
  },
  {
    label: "🇹🇭 โกรธ + ขอเงินคืน",
    subject: "แย่มาก ขอเงินคืน",
    body: "โมโหมาก พัสดุไม่ได้รับของสักที ขอเงินคืนไม่งั้นจะยกเลิกบัญชี",
    customer_tier: "pro",
  },
  {
    label: "🇹🇭 ลืมรหัสผ่าน",
    subject: "ลืมรหัสผ่าน",
    body: "เข้าสู่ระบบไม่ได้เพราะลืมรหัสผ่าน ขอวิธีรีเซ็ตรหัสหน่อยครับ",
    customer_tier: "free",
  },
  {
    label: "🇬🇧 Charged twice",
    subject: "I was charged twice this month",
    body: "My Pro plan shows two $20 charges on my card. Please refund one.",
    customer_tier: "pro",
  },
  {
    label: "🇬🇧 Ambiguous",
    subject: "question",
    body: "Hi, just wondering about a thing with my stuff.",
    customer_tier: "free",
  },
];

const PIPELINE = ["Intent Router", "Domain Expert", "Policy RAG", "Priority Scorer", "Judge"];

function Badge({ className, children }) {
  return <span className={`badge ${className || ""}`}>{children}</span>;
}

export default function Home() {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [tier, setTier] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function loadSample(s) {
    setSubject(s.subject);
    setBody(s.body);
    setTier(s.customer_tier);
    setResult(null);
    setError("");
  }

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, body, customer_tier: tier || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="wrap">
      <header className="top">
        <div className="eyebrow">PRD-5 · Customer Support Ticket Triage</div>
        <h1>Ticket Triage Console</h1>
        <p>
          ส่ง ticket (ไทยหรืออังกฤษ) แล้วระบบจะจัดหมวด กำหนดความด่วน เลือกคิว และอ้างอิงนโยบาย
          โดยอัตโนมัติ — ประมวลผลผ่าน pipeline แบบ multi-agent ด้วย LLM (Groq) เมื่อตั้งค่า API key
          และถอยกลับเป็น rule-based อัตโนมัติเมื่อไม่มีคีย์
        </p>
      </header>

      <div className="grid">
        {/* ------------------------------- Input ------------------------------- */}
        <section className="card">
          <h2>ส่ง Ticket</h2>

          <div className="samples">
            {SAMPLES.map((s) => (
              <button key={s.label} type="button" className="chip" onClick={() => loadSample(s)}>
                {s.label}
              </button>
            ))}
          </div>

          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="subject">หัวข้อ (Subject)</label>
              <input
                id="subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="เช่น โดนเก็บเงินซ้ำ / Charged twice"
              />
            </div>

            <div className="field">
              <label htmlFor="body">รายละเอียด (Body)</label>
              <textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="พิมพ์ข้อความจากลูกค้าที่นี่…"
              />
            </div>

            <div className="field">
              <label htmlFor="tier">ระดับลูกค้า (Customer tier)</label>
              <select id="tier" value={tier} onChange={(e) => setTier(e.target.value)}>
                <option value="">— ไม่ระบุ —</option>
                <option value="free">free</option>
                <option value="pro">pro</option>
                <option value="enterprise">enterprise</option>
              </select>
            </div>

            <button className="btn" type="submit" disabled={loading}>
              {loading ? "กำลังประมวลผล…" : "ประมวลผล Triage"}
            </button>
          </form>

          {error && (
            <p className="small" style={{ color: "var(--p1)", marginTop: 12 }}>
              ⚠️ {error}
            </p>
          )}
        </section>

        {/* ------------------------------- Result ------------------------------ */}
        <section className="card">
          <h2>ผลการ Triage</h2>

          {!result && !loading && (
            <div className="result-empty">
              ยังไม่มีผลลัพธ์ — เลือกตัวอย่างด้านซ้าย หรือพิมพ์ ticket แล้วกด “ประมวลผล Triage”
            </div>
          )}

          {result && (
            <>
              <div className="decision-head">
                <Badge className="cat">หมวด: {result.category}</Badge>
                <Badge className={result.priority.toLowerCase()}>ความด่วน: {result.priority}</Badge>
                {result.escalate ? (
                  <Badge className="esc">⚡ Escalate</Badge>
                ) : (
                  <Badge className="ok">ปกติ</Badge>
                )}
                {result.is_multi_issue && <Badge>หลายประเด็น</Badge>}
                <Badge className={result.engine === "llm" ? "cat" : ""}>
                  {result.engine === "llm" ? "🤖 LLM" : "⚙️ rule-based"}
                </Badge>
              </div>

              {result.engine_note && (
                <p className="small muted" style={{ marginTop: -4, marginBottom: 8 }}>
                  {result.engine_note}
                </p>
              )}

              <dl className="kv">
                <dt>Sub-intent</dt>
                <dd>{result.sub_intent}</dd>
                <dt>คิวที่รับผิดชอบ</dt>
                <dd>{result.assigned_queue}</dd>
                <dt>Macro แนะนำ</dt>
                <dd>{result.suggested_macro_id || <span className="muted">—</span>}</dd>
                <dt>Judge</dt>
                <dd>
                  {result.judge_approved ? (
                    <span style={{ color: "var(--success)" }}>อนุมัติ ✓</span>
                  ) : (
                    <span style={{ color: "var(--p1)" }}>ตีกลับให้ตรวจ</span>
                  )}
                </dd>
              </dl>

              <div>
                <span className="small muted">ความมั่นใจ (confidence): {Math.round(result.confidence * 100)}%</span>
                <div className="confbar">
                  <span style={{ width: `${Math.round(result.confidence * 100)}%` }} />
                </div>
              </div>

              <div className="section-label">นโยบายที่อ้างอิง (Policy citations)</div>
              {result.policy_hits && result.policy_hits.length ? (
                result.policy_hits.map((p) => (
                  <div className="policy" key={p.policy_id}>
                    <div className="pid">{p.policy_id} · {p.title}</div>
                    <div className="snip">{p.snippet}</div>
                  </div>
                ))
              ) : (
                <p className="small muted">ไม่มี</p>
              )}

              <div className="section-label">บันทึกภายใน (Internal notes)</div>
              <div className="notes">{result.internal_notes}</div>

              <div className="pipeline">
                {PIPELINE.map((step, i) => (
                  <span key={step} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <span className="step active">{step}</span>
                    {i < PIPELINE.length - 1 && <span className="arrow">→</span>}
                  </span>
                ))}
              </div>

              <details className="raw">
                <summary>ดู JSON ดิบ (TriageResult)</summary>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </details>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
