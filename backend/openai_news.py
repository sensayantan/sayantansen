"""
Researches and writes one news section using OpenAI's web search tool
(Responses API), as an alternative to claude_news.py.

Mirrors claude_news.py's interface exactly — research_section(section,
since_iso) -> list[dict] — so generate_news.py can pick either provider
based on AI_PROVIDER in .env without any other code changes.

Caveat: some of OpenAI's own documentation pages were unreachable from
the environment this was written in, so the exact tool name/model pairing
below is a best-effort default grounded in current examples rather than
something directly verified end-to-end. If MODEL_ID or WEB_SEARCH_TOOL_TYPE
don't match what your account/models support, the API error message will
say so directly — treat this the same as any other first-run bug: paste
the error and we'll adjust the .env values (no code change needed).
"""

import json
import os
import re

from openai import OpenAI

from config import Section

client = OpenAI()

MODEL_ID = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
# If your account's models use the newer non-preview tool instead, set
# OPENAI_WEB_SEARCH_TOOL=web_search in .env.
WEB_SEARCH_TOOL_TYPE = os.environ.get("OPENAI_WEB_SEARCH_TOOL", "web_search_preview")

SYSTEM_PROMPT = """You are a research assistant compiling one section of a \
personal "Morning Intelligence Edition" news brief. You must use the web \
search tool to find CURRENT, VERIFIABLE news — never invent or guess at \
stories, facts, prices, scores, or dates. If you cannot find enough genuine, \
well-sourced stories for this section in the given time window, return fewer \
stories (or none) rather than filling space with filler, opinion, or recycled \
old news presented as new.

Rules for every story:
- Reconcile the story across multiple reputable publishers when possible.
- Write an ORIGINAL headline and a short paragraph-length synthesis in your own \
words — do not copy sentences verbatim from a source.
- Include every materially relevant source link, favoring primary sources and \
original reporting over aggregators.
- Avoid duplicated wire-service stories, exhaustive search process commentary, \
and marketing language.
- Never include private personal information (email addresses, phone numbers, \
home addresses) about any private individual.

Output format — this is critical:
Respond with ONLY a JSON array, no prose before or after it, no markdown code \
fences. Each element must have exactly these keys:
  "category": short label (2-4 words),
  "headline": your original headline (string),
  "summary": one paragraph synthesis (string),
  "sources": array of {"label": short source name, "url": the article URL}
If there is nothing genuinely new and well-sourced to report, respond with: []
"""


def _build_user_prompt(section: Section, since_iso: str) -> str:
    sources = ", ".join(section.preferred_sources)
    story_range = (
        f"{section.min_stories}-{section.max_stories}"
        if section.min_stories
        else f"up to {section.max_stories}"
    )
    guidance = f"\n\nAdditional guidance: {section.guidance}" if section.guidance else ""
    return f"""Section: "{section.label}"

Search for news published since {since_iso} (UTC). If that window has too little \
genuine news, you may look back up to 3 days, but prefer the most recent.

Preferred sources for this section: {sources}.
Aim for {story_range} stories. It is better to return fewer stories than to pad \
the section with weak or filler material.{guidance}

Remember: output ONLY the JSON array described in your instructions."""


def _extract_json_array(text: str) -> list:
    """Same tolerant extraction as claude_news.py — pulls the substring
    between the first '[' and last ']' rather than assuming the model's
    final answer is pure JSON with nothing else around it."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("No JSON array found in response", cleaned, 0)

    return json.loads(cleaned[start : end + 1])


def research_section(section: Section, since_iso: str) -> list[dict]:
    """Returns a list of story dicts for this section (possibly empty)."""
    response = client.responses.create(
        model=MODEL_ID,
        tools=[{"type": WEB_SEARCH_TOOL_TYPE}],
        instructions=SYSTEM_PROMPT,
        input=_build_user_prompt(section, since_iso),
        max_output_tokens=4000,
    )

    final_text = response.output_text

    try:
        stories = _extract_json_array(final_text)
    except (json.JSONDecodeError, ValueError):
        print(
            f"  [{section.id}] Could not parse a JSON array from the response — "
            f"skipping this section. First 300 chars of raw output:\n"
            f"  {final_text[:300]!r}"
        )
        return []

    if not isinstance(stories, list):
        print(f"  [{section.id}] Response was valid JSON but not a list — skipping.")
        return []

    return stories
