// Provider-agnostic LLM client (server-side only).
//
// Works with any OpenAI-compatible chat-completions endpoint:
//   - Groq   (default)  https://api.groq.com/openai/v1
//   - OpenAI            https://api.openai.com/v1
//   - Ollama (local)    http://localhost:11434/v1
//   - OpenRouter, etc.
//
// Config via env (set in web/.env.local — NEVER commit, NEVER expose to browser):
//   LLM_PROVIDER = groq | openai | ollama | custom   (default: groq)
//   LLM_API_KEY  = ...        (or GROQ_API_KEY / OPENAI_API_KEY)
//   LLM_MODEL    = ...        (default depends on provider)
//   LLM_BASE_URL = ...        (override for custom/self-hosted)

export class LLMUnavailable extends Error {}

const PROVIDER_DEFAULTS = {
  groq: { baseUrl: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile", keyEnv: "GROQ_API_KEY" },
  openai: { baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini", keyEnv: "OPENAI_API_KEY" },
  ollama: { baseUrl: "http://localhost:11434/v1", model: "llama3.1", keyEnv: null },
  custom: { baseUrl: "", model: "", keyEnv: null },
};

export function getLLMConfig() {
  const provider = (process.env.LLM_PROVIDER || "groq").toLowerCase();
  const d = PROVIDER_DEFAULTS[provider] || PROVIDER_DEFAULTS.groq;
  const apiKey =
    process.env.LLM_API_KEY ||
    (d.keyEnv ? process.env[d.keyEnv] : "") ||
    "";
  return {
    provider,
    baseUrl: process.env.LLM_BASE_URL || d.baseUrl,
    model: process.env.LLM_MODEL || d.model,
    apiKey,
    // Ollama needs no key; everyone else does.
    requiresKey: provider !== "ollama",
  };
}

export function llmConfigured() {
  const c = getLLMConfig();
  return !c.requiresKey || Boolean(c.apiKey);
}

/**
 * Call the LLM and return parsed JSON. Retries once on invalid JSON.
 * Throws LLMUnavailable if no key is configured (caller should fall back).
 */
export async function callLLMJson({ system, user, temperature = 0, maxRetries = 1 }) {
  const cfg = getLLMConfig();
  if (cfg.requiresKey && !cfg.apiKey) {
    throw new LLMUnavailable(`No API key for provider "${cfg.provider}".`);
  }

  let lastErr;
  let userMsg = user;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await fetch(`${cfg.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cfg.apiKey ? { Authorization: `Bearer ${cfg.apiKey}` } : {}),
      },
      body: JSON.stringify({
        model: cfg.model,
        temperature,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: system },
          { role: "user", content: userMsg },
        ],
      }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`LLM HTTP ${res.status}: ${text.slice(0, 300)}`);
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content ?? "";
    try {
      return JSON.parse(content);
    } catch (e) {
      lastErr = e;
      // Ask the model to fix its JSON on the next attempt.
      userMsg = `${user}\n\nYour previous reply was not valid JSON. Reply with ONLY a valid JSON object, no prose.`;
    }
  }
  throw new Error(`LLM returned invalid JSON after retries: ${lastErr}`);
}
