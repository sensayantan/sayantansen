"""
Fetches real autism-related paper records from PubMed into corpus/pubmed.jsonl.

PubMed is the US National Library of Medicine's biomedical literature
database. Its public HTTP API ("E-utilities") is free, needs no account,
and is used here in the standard two-call pattern:

  1. esearch.fcgi  -> given a search term, returns a list of PMIDs
  2. efetch.fcgi   -> given those PMIDs, returns the full records as XML

Only *abstracts* are fetched, not full text. Abstracts are unrestricted;
full text lives in a separate database (PMC) with per-article licensing,
which is deliberately out of scope here.

Every record written carries a source_url pointing at the real paper, which
is the whole reason this script exists — it replaces the hand-written
placeholder corpus that had nothing citable in it.

Rate limits: NCBI allows 3 requests/second anonymously, or 10/second with a
free API key. This script sleeps between requests to stay under the
anonymous limit. To use a key, set NCBI_API_KEY in your environment (never
commit one — put it in .env, which is gitignored).

NCBI also asks callers to identify themselves. Set NCBI_EMAIL and NCBI_TOOL
in your environment if you want to; both are omitted when unset.

Run manually:
    python3 fetch_pubmed.py
    python3 fetch_pubmed.py --max-records 3000 --since 2018
    python3 fetch_pubmed.py --term "autism AND early intervention[tiab]"

Writes corpus/pubmed.jsonl (one JSON record per line). Re-run to refresh;
the file is overwritten, not appended to.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
OUTPUT_PATH = CORPUS_DIR / "pubmed.jsonl"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# "hasabstract" matters: a PubMed record without an abstract is just a title,
# which is far too thin to embed usefully. English-only for the same reason —
# an embedding model given mixed languages produces a muddled vector space.
DEFAULT_TERM = 'autism spectrum disorder[MeSH Terms] AND hasabstract AND english[Language]'

# Anonymous limit is 3 req/sec; 0.4s leaves headroom for clock jitter.
SLEEP_ANONYMOUS = 0.4
SLEEP_WITH_KEY = 0.15

ESEARCH_PAGE = 1000   # max PMIDs esearch will return per call that we ask for
EFETCH_BATCH = 200    # records per efetch call; larger risks NCBI timeouts

MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


# ---------------------------------------------------------------- HTTP layer

def _shared_params() -> dict:
    """NCBI's optional identification params, included only when set."""
    params = {}
    for env_name, param_name in (
        ("NCBI_API_KEY", "api_key"),
        ("NCBI_EMAIL", "email"),
        ("NCBI_TOOL", "tool"),
    ):
        value = os.environ.get(env_name)
        if value:
            params[param_name] = value
    return params


def _sleep() -> None:
    time.sleep(SLEEP_WITH_KEY if os.environ.get("NCBI_API_KEY") else SLEEP_ANONYMOUS)


def _get(endpoint: str, params: dict) -> bytes:
    query = urllib.parse.urlencode({**params, **_shared_params()})
    url = f"{EUTILS}/{endpoint}?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def search_pmids(term: str, max_records: int) -> list[str]:
    """Pages through esearch until max_records PMIDs are collected."""
    pmids: list[str] = []
    retstart = 0
    while len(pmids) < max_records:
        retmax = min(ESEARCH_PAGE, max_records - len(pmids))
        raw = _get("esearch.fcgi", {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retstart": retstart,
            "retmax": retmax,
            "sort": "date",
        })
        result = json.loads(raw)["esearchresult"]
        batch = result.get("idlist", [])
        if not batch:
            break
        pmids.extend(batch)
        retstart += len(batch)
        total = int(result.get("count", 0))
        print(f"  esearch: {len(pmids)} of {total} matching PMIDs collected")
        if retstart >= total:
            break
        _sleep()
    return pmids[:max_records]


def fetch_records(pmids: list[str]) -> list[dict]:
    """efetch in batches, parsing each batch's XML into records."""
    records: list[dict] = []
    for start in range(0, len(pmids), EFETCH_BATCH):
        batch = pmids[start:start + EFETCH_BATCH]
        raw = _get("efetch.fcgi", {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        })
        parsed = parse_pubmed_xml(raw)
        records.extend(parsed)
        print(f"  efetch: {len(records)} records parsed ({start + len(batch)} of {len(pmids)} PMIDs)")
        if start + EFETCH_BATCH < len(pmids):
            _sleep()
    return records


# --------------------------------------------------------------- XML parsing
# Kept as pure functions over bytes so test_parsers.py can exercise them
# against fixture XML without touching the network.

def _text(element: ET.Element | None) -> str:
    """Flattens an element's text including nested markup (<i>, <sup>, ...).

    PubMed abstracts and titles routinely contain inline markup, so reading
    element.text alone silently truncates at the first nested tag.
    """
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def parse_abstract(article: ET.Element) -> str:
    """Joins the AbstractText parts, preserving structured-abstract labels."""
    parts = []
    for node in article.findall("./Abstract/AbstractText"):
        body = _text(node)
        if not body:
            continue
        label = node.get("Label")
        parts.append(f"{label.strip().title()}: {body}" if label else body)
    return " ".join(parts)


def parse_authors(article: ET.Element) -> list[str]:
    authors = []
    for node in article.findall("./AuthorList/Author"):
        collective = _text(node.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last = _text(node.find("LastName"))
        initials = _text(node.find("Initials"))
        if last:
            authors.append(f"{last} {initials}".strip())
    return authors


def parse_pub_date(article: ET.Element) -> str:
    """Returns the best available ISO-ish date, or "" if PubMed has none.

    PubDate is not a reliable ISO date: it may be Year/Month/Day, Year alone,
    or a free-text MedlineDate like "2024 Jan-Feb". Partial dates are returned
    partial (YYYY or YYYY-MM) rather than being padded into a false precision.
    """
    pub_date = article.find("./Journal/JournalIssue/PubDate")
    if pub_date is None:
        return ""

    year = _text(pub_date.find("Year"))
    if not year:
        # e.g. "2024 Jan-Feb" or "2023 Winter" — take the leading 4-digit year.
        medline = _text(pub_date.find("MedlineDate"))
        head = medline.split(" ")[0] if medline else ""
        return head if len(head) == 4 and head.isdigit() else ""

    raw_month = _text(pub_date.find("Month"))
    month = MONTHS.get(raw_month[:3].lower()) if raw_month else None
    if month is None and raw_month.isdigit():
        month = raw_month.zfill(2)
    if not month:
        return year

    day = _text(pub_date.find("Day"))
    return f"{year}-{month}-{day.zfill(2)}" if day.isdigit() else f"{year}-{month}"


def parse_pubmed_xml(raw: bytes) -> list[dict]:
    """Turns one efetch XML response into corpus records.

    Records without an abstract are dropped: the search term filters for
    hasabstract, but a custom --term may not, and a title-only record is not
    worth embedding.
    """
    root = ET.fromstring(raw)
    records = []
    for entry in root.findall(".//PubmedArticle"):
        citation = entry.find("MedlineCitation")
        if citation is None:
            continue
        article = citation.find("Article")
        if article is None:
            continue

        pmid = _text(citation.find("PMID"))
        abstract = parse_abstract(article)
        if not pmid or not abstract:
            continue

        records.append({
            "id": f"pmid-{pmid}",
            "source": "pubmed",
            "title": _text(article.find("ArticleTitle")),
            "text": abstract,
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "publication_date": parse_pub_date(article),
            "authors": parse_authors(article),
            "venue": _text(article.find("./Journal/Title")),
        })
    return records


# ---------------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--term", default=DEFAULT_TERM, help="PubMed search term (default: autism MeSH, with abstract, English)")
    parser.add_argument("--since", type=int, default=2016, help="Earliest publication year to include (default: 2016)")
    parser.add_argument("--max-records", type=int, default=1500, help="Maximum records to fetch (default: 1500)")
    args = parser.parse_args()

    term = f"{args.term} AND {args.since}:3000[dp]"
    print(f'Searching PubMed for: {term}')

    pmids = search_pmids(term, args.max_records)
    if not pmids:
        raise SystemExit("No PMIDs matched — check the --term syntax against pubmed.ncbi.nlm.nih.gov.")

    print(f"Fetching {len(pmids)} records...")
    records = fetch_records(pmids)

    CORPUS_DIR.mkdir(exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    dropped = len(pmids) - len(records)
    print(f"\nWrote {len(records)} records -> {OUTPUT_PATH}")
    if dropped:
        print(f"({dropped} PMIDs skipped — no abstract in the record)")
    print("Next: python3 build_index.py")


if __name__ == "__main__":
    main()
