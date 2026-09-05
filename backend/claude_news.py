"""
Researches and writes one news section using Claude's web search tool.

Each section gets its own API call. Claude searches the web itself (the
API runs the searches server-side — see the web_search tool docs), then
writes its final answer as a JSON array matching our story schema. We
parse that JSON directly rather than using structured outputs, because
structured outputs are incompatible with citations, and citations are
always on for web search — this way we keep the citation guarantee (every
claim traceable to a real, fetched source) without fighting the API over
response format.
"""

import json
import re

import anthropic

from config import MODEL_ID, Section

client = anthropic.Anthropic()

WEB_SEARCH_TOOL_TYPE = "web_search_20260209"  # dynamic filtering, current models

SYSTEM_PROMPT = """You are a research assistant compiling one section of a \
personal "Morning Intelligence Edition" news brief. You must use the web_search \
tool to find CURRENT, VERIFIABLE news — never invent or guess at stories, facts, \
prices, scores, or dates. If you cannot find enough genuine, well-sourced stories \
for this section in the given time window, return fewer stories (or none) rather \
than filling space with filler, opinion, or recycled old news presented as new.

Rules for every story:
- Reconcile the story across multiple reputable publishers when possible.
- Write an ORIGINAL headline and a short paragraph-length synthesis in your own \
words — do not copy sentences verbatim from a source.
- Include every materially relevant source link, favoring primary sources and \
original reporting over aggregators.
- Avoid duplicated wire-service stories, exhaustive search process commentary, \
connector diagnostics, and marketing language.
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
    """
    Pull a JSON array out of Claude's response text, tolerating a leading/
    trailing sentence around it (e.g. "Here are the stories:\n[...]") even
    though the prompt asks for JSON only — models don't always follow that
    instruction strictly, especially right after using a tool.
    """
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
    messages = [
        {"role": "user", "content": _build_user_prompt(section, since_iso)}
    ]
    tools = [
        {
            "type": WEB_SEARCH_TOOL_TYPE,
            "name": "web_search",
            "max_uses": section.max_searches,
        }
    ]

    request_kwargs = dict(
        model=MODEL_ID,
        max_tokens=16000,
        # Low effort: this is research/summarization, not hard reasoning —
        # keeps thinking-token spend down (cost) and leaves more of the
        # max_tokens budget free for the actual output (fewer truncations).
        output_config={"effort": "low"},
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )
    response = client.messages.create(**request_kwargs)

    # A long research turn can pause mid-way (server-side search loop hit its
    # step limit) — resend the paused assistant turn unchanged to resume.
    restarts = 0
    while response.stop_reason == "pause_turn" and restarts < 5:
        messages.append({"role": "assistant", "content": response.content})
        response = client.messages.create(**{**request_kwargs, "messages": messages})
        restarts += 1

    final_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    try:
        stories = _extract_json_array(final_text)
    except (json.JSONDecodeError, ValueError):
        print(
            f"  [{section.id}] Could not parse a JSON array from the response — "
            f"skipping this section.\n"
            f"  stop_reason: {response.stop_reason}\n"
            f"  First 300 chars of raw output:\n"
            f"  {final_text[:300]!r}"
        )
        return []

    if not isinstance(stories, list):
        print(f"  [{section.id}] Response was valid JSON but not a list — skipping.")
        return []

    return stories
