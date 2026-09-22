// Single Worker entry point, following the same shape as oauth-proxy/: one
// script handles every request and decides what to do with it, with anything
// unrouted handed to the static assets binding.
//
// This Worker is deliberately separate from the OAuth proxy rather than a
// couple of extra routes on it. That one holds GitHub client secrets and
// guards admin login; this one is a public, unauthenticated endpoint that
// burns AI inference on whatever a stranger types. They should not be able
// to take each other down.
import { search } from "./search.js";
import { generateAnswer } from "./answer.js";

const ALLOWED_ORIGINS = [
  "https://sensayantan.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const MAX_QUESTION_CHARS = 300;
const TOP_K = 4;

// Per-IP cap. The Cache API is per-colocation rather than global, so this is
// a soft limit that a determined caller could spread across regions — it is
// there to stop a stuck loop or a curious scraper from burning the daily
// Workers AI allowance, not to stop an attacker.
const RATE_LIMIT = 20;
const RATE_WINDOW_SECONDS = 60;

function corsHeaders(request) {
  const origin = request.headers.get("Origin");
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(body, request, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(request) },
  });
}

async function withinRateLimit(request) {
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const key = new Request(`https://ratelimit.local/${encodeURIComponent(ip)}`);
  const cache = caches.default;

  const hit = await cache.match(key);
  const count = hit ? Number(await hit.text()) || 0 : 0;
  if (count >= RATE_LIMIT) return false;

  await cache.put(
    key,
    new Response(String(count + 1), {
      headers: { "Cache-Control": `max-age=${RATE_WINDOW_SECONDS}` },
    })
  );
  return true;
}

async function handleAsk(request, env) {
  if (request.method !== "POST") {
    return json({ error: "Use POST." }, request, 405);
  }
  if (!(await withinRateLimit(request))) {
    return json(
      { error: "Too many questions in a short time. Wait a minute and try again." },
      request,
      429
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Expected a JSON body." }, request, 400);
  }

  const question = typeof body?.question === "string" ? body.question.trim() : "";
  if (!question) {
    return json({ error: "Ask a question." }, request, 400);
  }
  if (question.length > MAX_QUESTION_CHARS) {
    return json(
      { error: `Keep it under ${MAX_QUESTION_CHARS} characters.` },
      request,
      400
    );
  }

  try {
    const results = await search(env, question, TOP_K);
    const answer = await generateAnswer(env, question, results);
    return json(
      {
        question,
        answer: answer.text,
        // The page shows a different, stronger warning when a model wrote
        // the text than when it only ranked documents.
        answer_is_generated: answer.generated,
        results: results.map((r) => ({ score: Number(r.score.toFixed(3)), ...r.doc })),
      },
      request
    );
  } catch (error) {
    console.error(error);
    return json({ error: "Search failed. Try again shortly." }, request, 500);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (url.pathname === "/api/ask") {
      return handleAsk(request, env);
    }

    // Cheap diagnostic: confirms the assets loaded and reports what the
    // index actually contains, without running an embedding.
    if (url.pathname === "/api/health") {
      try {
        const results = await search(env, "autism", 1);
        return json(
          { ok: true, sample_score: Number(results[0]?.score?.toFixed(3) ?? 0) },
          request
        );
      } catch (error) {
        return json({ ok: false, error: String(error.message || error) }, request, 500);
      }
    }

    return env.ASSETS.fetch(request);
  },
};
