"""
Fetches autism-related clinical trial records into corpus/trials.jsonl.

ClinicalTrials.gov is the US registry of clinical studies. Its v2 REST API
is free, needs no key, returns JSON, and pages with an opaque
`nextPageToken` rather than numeric offsets.

Why this source is here alongside PubMed: papers describe what was *found*,
trials describe what is being *tried*, and — the part that matters for the
longer-term geographic-directory idea — each trial lists the real
institutions running it, with city, state and country. That is the closest
thing to a free, structured list of places doing autism work.

Every record carries a source_url to the study's own page.

Run manually:
    python3 fetch_trials.py
    python3 fetch_trials.py --max-records 1000 --condition "autism spectrum disorder"

Writes corpus/trials.jsonl (one JSON record per line). Re-run to refresh;
the file is overwritten, not appended to.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
OUTPUT_PATH = CORPUS_DIR / "trials.jsonl"

API_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 200          # API allows up to 1000; 200 keeps responses small
SLEEP_BETWEEN_PAGES = 0.3
MAX_LOCATIONS = 8        # a few large trials list hundreds of sites


def _get_page(condition: str, page_token: str | None) -> dict:
    params = {
        "query.cond": condition,
        "pageSize": PAGE_SIZE,
        "format": "json",
    }
    if page_token:
        params["pageToken"] = page_token
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read())


def fetch_studies(condition: str, max_records: int) -> list[dict]:
    """Pages through the API until max_records studies are collected."""
    studies: list[dict] = []
    page_token = None
    while len(studies) < max_records:
        payload = _get_page(condition, page_token)
        batch = payload.get("studies", [])
        if not batch:
            break
        studies.extend(batch)
        print(f"  {len(studies)} studies collected")
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
        time.sleep(SLEEP_BETWEEN_PAGES)
    return studies[:max_records]


# ------------------------------------------------------------- JSON parsing
# Pure function over the API payload so test_parsers.py can exercise it
# against a fixture without touching the network.

def _format_locations(locations: list[dict]) -> list[str]:
    formatted = []
    for loc in locations[:MAX_LOCATIONS]:
        parts = [loc.get(key) for key in ("facility", "city", "state", "country")]
        label = ", ".join(p for p in parts if p)
        if label:
            formatted.append(label)
    return formatted


def parse_studies(studies: list[dict]) -> list[dict]:
    """Turns raw API study objects into corpus records.

    Studies with no brief summary are dropped — the title alone is too thin
    to embed, the same rule fetch_pubmed.py applies to abstract-less records.
    """
    records = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        description = protocol.get("descriptionModule", {})
        design = protocol.get("designModule", {})
        sponsors = protocol.get("sponsorCollaboratorsModule", {})
        contacts = protocol.get("contactsLocationsModule", {})
        conditions = protocol.get("conditionsModule", {})

        nct_id = ident.get("nctId")
        summary = (description.get("briefSummary") or "").strip()
        if not nct_id or not summary:
            continue

        # Conditions and phase are folded into the embedded text, not left as
        # metadata only: a question like "trials for autism in teenagers" has
        # to match against something, and the summary alone often omits them.
        conditions_list = conditions.get("conditions") or []
        phases = design.get("phases") or []
        context = []
        if conditions_list:
            context.append(f"Conditions: {', '.join(conditions_list)}.")
        if phases:
            context.append(f"Phase: {', '.join(phases)}.")
        text = " ".join([*context, " ".join(summary.split())])

        sponsor = (sponsors.get("leadSponsor") or {}).get("name", "")
        records.append({
            "id": f"nct-{nct_id}",
            "source": "clinicaltrials",
            "title": ident.get("briefTitle") or ident.get("officialTitle") or nct_id,
            "text": text,
            "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
            "publication_date": (status.get("startDateStruct") or {}).get("date", ""),
            "authors": [sponsor] if sponsor else [],
            "venue": "ClinicalTrials.gov",
            "status": status.get("overallStatus", ""),
            "phases": phases,
            "locations": _format_locations(contacts.get("locations") or []),
        })
    return records


# ---------------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--condition", default="autism", help="Condition to search for (default: autism)")
    parser.add_argument("--max-records", type=int, default=400, help="Maximum studies to fetch (default: 400)")
    args = parser.parse_args()

    print(f'Searching ClinicalTrials.gov for condition: {args.condition}')
    studies = fetch_studies(args.condition, args.max_records)
    if not studies:
        raise SystemExit("No studies matched — try a broader --condition.")

    records = parse_studies(studies)

    CORPUS_DIR.mkdir(exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    dropped = len(studies) - len(records)
    print(f"\nWrote {len(records)} records -> {OUTPUT_PATH}")
    if dropped:
        print(f"({dropped} studies skipped — no brief summary in the record)")
    print("Next: python3 build_index.py")


if __name__ == "__main__":
    main()
