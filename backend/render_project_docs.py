"""
Turns content/project-docs.yml into data/project-docs.json for
projectdocs.html (SenProjectDocumentation).

The shape mirrors DAYBREAK-EPICS-AND-STORIES.md — document purpose, product
vision, core principles, then epics numbered 1..N holding stories numbered
N.M with a narrative and acceptance criteria. Epics carry a `project` field
so two independently numbered sets can share one page without either being
renumbered.

Markdown is allowed in the prose fields (purpose, vision, principles,
narrative) because the reference document uses bold for emphasis; it is
rendered here rather than in the browser, so the page needs no markdown
library.

Run manually:
    python3 backend/render_project_docs.py

In production this runs from .github/workflows/render-content.yml on any
push touching content/**.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import markdown as markdown_lib
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "content" / "project-docs.yml"
DATA_PATH = ROOT / "data" / "project-docs.json"

# Anything outside this set is rendered as a neutral chip rather than being
# dropped, so a status Codex introduces still displays.
KNOWN_STATUSES = {"Done", "In progress", "Blocked"}

# Same tolerance pattern as story status: an unrecognised backlog type still
# renders, as a neutral chip, rather than being dropped.
KNOWN_BACKLOG_TYPES = {"Technical Debt", "Feature Enhancement", "Feature Development"}


def inline(text) -> str:
    """Markdown for a run of prose, with the wrapping paragraph removed."""
    if not text:
        return ""
    html = markdown_lib.markdown(str(text).strip())
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html


def story(raw: dict, epic_number, index: int) -> dict:
    number = raw.get("number") or f"{epic_number}.{index}"
    status = raw.get("status") or "Open"
    return {
        "number": str(number),
        "title": raw.get("title") or "Untitled story",
        "status": status,
        "known_status": status in KNOWN_STATUSES,
        "narrative": inline(raw.get("narrative") or raw.get("description")),
        "acceptance_criteria": [inline(x) for x in raw.get("acceptance_criteria") or []],
        "assumptions": [inline(x) for x in raw.get("assumptions") or []],
        "notes": inline(raw.get("notes")),
    }


def backlog_item(raw: dict, index: int) -> dict:
    epic_name = raw.get("epic")
    title = raw.get("title")
    item_type = raw.get("type") or "Feature Development"
    date = raw.get("date")
    if not epic_name or not title:
        raise ValueError(f"backlog[{index}] needs both epic and title")
    return {
        "epic": epic_name,
        "title": title,
        "description": inline(raw.get("description")),
        "type": str(item_type),
        "known_type": str(item_type) in KNOWN_BACKLOG_TYPES,
        # ISO text is fine as-is for both sorting and display; nothing here
        # needs it as a real date object.
        "date": str(date) if date else "",
    }


def epic(raw: dict) -> dict:
    number = raw.get("number")
    stories = [story(s, number, i + 1) for i, s in enumerate(raw.get("stories") or [])]
    done = sum(1 for s in stories if s["status"] == "Done")
    return {
        "project": raw.get("project") or "Unassigned",
        "number": number,
        "key": f"Epic {number}" if number is not None else "Epic",
        "title": raw.get("title") or "Untitled epic",
        "summary": inline(raw.get("summary")),
        "status": raw.get("status") or "Open",
        "stories": stories,
        "done": done,
        "total": len(stories),
    }


def main() -> int:
    if not SOURCE.exists():
        print(f"No {SOURCE} — nothing to render.")
        return 0

    try:
        source = yaml.safe_load(SOURCE.read_text()) or {}
    except yaml.YAMLError as exc:
        print(f"FAIL — {SOURCE.name} is not valid YAML:\n  {exc}")
        return 1

    doc = source.get("document") or {}
    epics = [epic(e) for e in source.get("epics") or []]
    if not epics:
        print(f"FAIL — {SOURCE.name} defines no epics.")
        return 1

    # Group by project, keeping the order each project first appears in, so
    # appending a second set never reorders the first.
    projects: list[dict] = []
    seen: dict[str, dict] = {}
    for item in epics:
        name = item["project"]
        if name not in seen:
            seen[name] = {"name": name, "epics": []}
            projects.append(seen[name])
        seen[name]["epics"].append(item)

    backlog_raw = source.get("backlog") or []
    backlog = [backlog_item(b, i) for i, b in enumerate(backlog_raw)]
    # Most recently identified first, matching how a backlog is normally read.
    backlog.sort(key=lambda b: b["date"], reverse=True)

    stories_total = sum(e["total"] for e in epics)
    output = {
        "title": doc.get("title") or "Project documentation",
        "purpose": inline(doc.get("purpose")),
        "vision": inline(doc.get("vision")),
        "principles": [inline(p) for p in doc.get("principles") or []],
        "projects": projects,
        "backlog": backlog,
        "definition_of_done": [inline(x) for x in source.get("definition_of_done") or []],
        "out_of_scope": [inline(x) for x in source.get("out_of_scope") or []],
        "totals": {
            "epics": len(epics),
            "stories": stories_total,
            "done": sum(e["done"] for e in epics),
            "backlog": len(backlog),
        },
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, indent=2) + "\n")
    print(
        f"Wrote {DATA_PATH.relative_to(ROOT)} "
        f"({len(projects)} project(s), {len(epics)} epics, {stories_total} stories, "
        f"{len(backlog)} backlog item(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
