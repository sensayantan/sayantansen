"""
Section definitions for the Morning Intelligence Edition.

Each Section describes one block of news.html: which category it renders
as, and the guidance (preferred sources, story count) fed into the prompt
in claude_news.py. Add or edit sections here — nothing else needs to
change for a new text-based section to show up on the site.
"""

import os
from dataclasses import dataclass, field

AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")
MODEL_ID = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


@dataclass
class Section:
    id: str
    label: str
    kicker: str
    preferred_sources: list[str]
    guidance: str = ""
    max_searches: int = 8
    min_stories: int = 5
    max_stories: int = 7


# Sections researched and written by Claude via web search.
# Money/Markets is deliberately NOT here — it needs a real market-data API,
# not LLM search/synthesis, and is handled separately (see MARKETS_PLACEHOLDER
# in generate_news.py).
TEXT_SECTIONS: list[Section] = [
    Section(
        id="top-news",
        label="Top News",
        kicker="The signals shaping today",
        preferred_sources=["AP", "Reuters", "primary/official sources"],
        guidance="The single most important, broadly significant stories of the window, regardless of category.",
    ),
    Section(
        id="us-news",
        label="US News",
        kicker="Policy, economy and events across America",
        preferred_sources=[
            "CNN", "Fox News", "CNBC", "The Washington Post", "AP", "Reuters",
            "government or company sources",
        ],
    ),
    Section(
        id="world-news",
        label="World News",
        kicker="International developments",
        preferred_sources=[
            "BBC", "Reuters", "Al Jazeera", "CNN", "Fox News",
            "credible regional publishers from China, Singapore, the Middle East, Europe and Africa",
        ],
    ),
    Section(
        id="india-news",
        label="India News",
        kicker="Policy, economy and national developments",
        preferred_sources=[
            "Republic World", "Times Now", "Hindustan Times", "The Indian Express",
            "primary/government sources",
        ],
    ),
    Section(
        id="tech-innovation",
        label="Technology & Innovation",
        kicker="Products, platforms and execution",
        preferred_sources=[
            "official product announcements", "release notes", "engineering blogs",
            "research papers", "respected technology publications",
        ],
    ),
    Section(
        id="ai-tracker",
        label="AI Model & Product Updates",
        kicker="New releases across the AI industry",
        preferred_sources=["official vendor announcements and release notes only"],
        guidance=(
            "Check for genuinely NEW announcements (not older news recycled as new) from: "
            "OpenAI/ChatGPT/Codex, Google Gemini, Anthropic Claude, Perplexity, xAI Grok, "
            "Cursor, DeepSeek, Alibaba Qwen, Moonshot Kimi, Zhipu GLM, MiniMax, Baidu ERNIE, "
            "and other globally significant AI models/tools. For each update, state: vendor "
            "and product/model, release date, features/capabilities, availability, practical "
            "importance, and whether it is a model, app, agent, developer tool, or integration."
        ),
        min_stories=0,
    ),
    Section(
        id="sports",
        label="Sports",
        kicker="Verified schedules and completed results",
        preferred_sources=["official league/federation sites", "AP", "Reuters", "BBC Sport"],
        guidance=(
            "Prioritize cricket, soccer, swimming, badminton, and basketball. Use only "
            "verified schedules and completed results — never describe an unfinished "
            "event as final."
        ),
        min_stories=0,
    ),
]
