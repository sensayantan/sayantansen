// Contact-form Worker for sensayantan.com.
//
// GitHub Pages serves files and cannot send email, so the form on
// Privacy/index.html posts here. This Worker checks the Cloudflare
// Turnstile token (the free "are you human" check), then emails the
// message to the owner through Cloudflare Email Routing. Nothing is stored:
// the message exists only in the email that arrives.
//
// The owner's address is never in this public repository. It lives in the
// CONTACT_TO secret, set in the Cloudflare dashboard, and Email Routing only
// delivers to destination addresses the owner has verified there.

import { EmailMessage } from "cloudflare:email";

const DEFAULT_ORIGINS = "https://sensayantan.com";
const LIMITS = { name: 100, email: 200, message: 5000, minMessage: 10 };
const EMAIL_RE = /^[^\s@<>"',;]+@[^\s@<>"',;]+\.[^\s@<>"',;]+$/;

function allowedOrigins(env) {
  return (env.SITE_ORIGINS || DEFAULT_ORIGINS).split(",").map((o) => o.trim()).filter(Boolean);
}

function corsHeaders(request, env) {
  const origins = allowedOrigins(env);
  const origin = request.headers.get("Origin");
  return {
    "Access-Control-Allow-Origin": origins.includes(origin) ? origin : origins[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}

function json(body, request, env, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(request, env) },
  });
}

// One line, no control characters: these values end up in email headers,
// and a stray CR/LF would let a visitor inject headers of their own.
function oneLine(value) {
  return String(value || "").replace(/[\u0000-\u001f\u007f]+/g, " ").trim();
}

// RFC 2047 encoded-word, so a non-ASCII name survives in the Subject.
function encodeHeader(text) {
  return /^[\x20-\x7e]*$/.test(text) ? text : `=?UTF-8?B?${base64(text)}?=`;
}

function base64(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}

function buildEmail({ from, to, replyTo, name, email, message, origin }) {
  const body = [
    `From:    ${name}`,
    `Email:   ${email || "(not given)"}`,
    `Sent:    ${new Date().toUTCString()}`,
    `Page:    ${origin}/Privacy/`,
    "",
    message,
    "",
    "—",
    "Sent from the contact form on sensayantan.com. Reply to answer the sender directly" +
      (email ? "." : " (they left no email address, so there is no one to reply to)."),
  ].join("\r\n");
  const headers = [
    `From: ${encodeHeader("sensayantan.com contact form")} <${from}>`,
    `To: <${to}>`,
    replyTo ? `Reply-To: <${replyTo}>` : null,
    `Subject: ${encodeHeader(`Contact form: ${name}`)}`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: <${crypto.randomUUID()}@${from.split("@")[1]}>`,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=UTF-8",
    "Content-Transfer-Encoding: base64",
  ].filter(Boolean);
  const encoded = base64(body).replace(/.{1,76}/g, "$&\r\n");
  return headers.join("\r\n") + "\r\n\r\n" + encoded;
}

// Returns Turnstile's verdict and its error codes. The codes are what tell a
// wrong secret ("invalid-input-secret") apart from an expired or reused token
// ("timeout-or-duplicate") or a page on an unlisted hostname, so they are
// passed back to the form and logged rather than collapsed into a yes/no.
async function verifyTurnstile(token, ip, env) {
  const form = new FormData();
  form.append("secret", String(env.TURNSTILE_SECRET).trim());
  form.append("response", token);
  if (ip) form.append("remoteip", ip);
  const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body: form,
  });
  const result = await res.json();
  return {
    success: result.success === true,
    codes: result["error-codes"] || [],
    hostname: result.hostname || null,
  };
}

async function handleContact(request, env) {
  if (!env.TURNSTILE_SECRET || !env.CONTACT_TO || !env.SEND_EMAIL) {
    return json({ error: "The contact form is not set up yet." }, request, env, 503);
  }

  let data;
  try {
    data = await request.json();
  } catch {
    return json({ error: "Could not read the form." }, request, env, 400);
  }

  const name = oneLine(data.name).slice(0, LIMITS.name);
  const email = oneLine(data.email).slice(0, LIMITS.email);
  const message = String(data.message || "").replace(/\r\n?/g, "\n").trim();

  if (!name) return json({ error: "Please add your name." }, request, env, 400);
  if (email && !EMAIL_RE.test(email)) {
    return json({ error: "That email address doesn't look right." }, request, env, 400);
  }
  if (message.length < LIMITS.minMessage) {
    return json({ error: "Please write a little more." }, request, env, 400);
  }
  if (message.length > LIMITS.message) {
    return json({ error: `Please keep the message under ${LIMITS.message} characters.` }, request, env, 400);
  }

  const ip = request.headers.get("CF-Connecting-IP");
  if (!data.turnstileToken) {
    return json({ error: "The human check didn't pass. Please try again.", reason: "missing-token" }, request, env, 403);
  }
  const check = await verifyTurnstile(data.turnstileToken, ip, env);
  if (!check.success) {
    console.warn("turnstile rejected:", check.codes.join(","), "hostname:", check.hostname);
    return json(
      { error: "The human check didn't pass. Please try again.", reason: check.codes.join(",") || "rejected" },
      request,
      env,
      403,
    );
  }

  const from = env.FROM_ADDRESS || "contact-form@sensayantan.com";
  const raw = buildEmail({
    from,
    to: env.CONTACT_TO,
    replyTo: email || null,
    name,
    email,
    message,
    origin: allowedOrigins(env)[0],
  });

  try {
    await env.SEND_EMAIL.send(new EmailMessage(from, env.CONTACT_TO, raw));
  } catch (error) {
    console.error("send failed:", error);
    // Email Routing's message says what is wrong (an unverified destination,
    // a sender off the domain, ...). Addresses are masked before it reaches
    // the page, so the owner's address can never be shown to a visitor.
    const reason = String((error && error.message) || error)
      .replace(/[^\s<>"']+@[^\s<>"']+/g, "[address]")
      .slice(0, 200);
    return json({ error: "The message couldn't be sent. Please try again later.", reason }, request, env, 502);
  }
  return json({ ok: true }, request, env);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS" && url.pathname === "/api/contact") {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }
    if (url.pathname === "/api/contact" && request.method === "POST") {
      return handleContact(request, env);
    }
    if (url.pathname === "/api/health") {
      // Verifying a dummy token tells a wrong secret apart from a right one
      // without revealing it: a bad secret is reported as
      // "invalid-input-secret", a good one only rejects the dummy token.
      let turnstileSecretValid = null;
      if (env.TURNSTILE_SECRET) {
        const probe = await verifyTurnstile("health-check-dummy-token", null, env);
        turnstileSecretValid = !probe.codes.includes("invalid-input-secret");
      }
      return json(
        {
          ok: Boolean(env.TURNSTILE_SECRET && env.CONTACT_TO && env.SEND_EMAIL && turnstileSecretValid),
          turnstileSecret: Boolean(env.TURNSTILE_SECRET),
          turnstileSecretValid,
          contactTo: Boolean(env.CONTACT_TO),
          emailBinding: Boolean(env.SEND_EMAIL),
        },
        request,
        env,
      );
    }
    return env.ASSETS.fetch(request);
  },
};
