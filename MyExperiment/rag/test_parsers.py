"""
Exercises the fetch scripts' parsing logic against fixture payloads.

The fetch scripts can't be tested by running them — that would hit NCBI and
ClinicalTrials.gov for real. But parsing is where the bugs actually live:
PubMed XML in particular is full of shapes that a naive parser silently
mangles (structured abstracts, inline markup, non-ISO dates, group authors).
So the parsers are pure functions over bytes/dicts, and this script feeds
them fixtures modelled on those real shapes.

Run manually (no network, no dependencies beyond the standard library):
    python3 test_parsers.py

Exits 0 if every check passes, 1 with a diff-style report if not.
"""

from __future__ import annotations

import sys

from fetch_pubmed import parse_pubmed_xml
from fetch_trials import parse_studies

# A deliberately awkward efetch response:
#   - article 1: structured abstract with Labels, inline <i> markup in the
#     title, a group (CollectiveName) author, full Year/Month/Day date
#   - article 2: single unlabelled abstract, numeric Month, no Day
#   - article 3: MedlineDate instead of Year ("2023 Jan-Feb")
#   - article 4: no abstract at all -> must be dropped
PUBMED_FIXTURE = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">38212345</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><Year>2024</Year><Month>Jan</Month><Day>5</Day></PubDate></JournalIssue>
          <Title>Journal of Autism and Developmental Disorders</Title>
        </Journal>
        <ArticleTitle>Early markers in <i>ASD</i>: a cohort study</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Screening remains inconsistent.</AbstractText>
          <AbstractText Label="METHODS">We followed 400 <sup>children</sup> to age 6.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>Jane</ForeName><Initials>J</Initials></Author>
          <Author><CollectiveName>The ADDM Study Group</CollectiveName></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="2">38198877</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><Year>2023</Year><Month>11</Month></PubDate></JournalIssue>
          <Title>Pediatrics</Title>
        </Journal>
        <ArticleTitle>Parent-mediated intervention outcomes</ArticleTitle>
        <Abstract><AbstractText>A randomised trial of parent coaching.</AbstractText></Abstract>
        <AuthorList><Author><LastName>Doe</LastName><Initials>A</Initials></Author></AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>37000111</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><MedlineDate>2023 Jan-Feb</MedlineDate></PubDate></JournalIssue>
          <Title>Autism Research</Title>
        </Journal>
        <ArticleTitle>Sensory profiles across the lifespan</ArticleTitle>
        <Abstract><AbstractText>Sensory differences persist into adulthood.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>36000222</PMID>
      <Article>
        <Journal><JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue><Title>Letters</Title></Journal>
        <ArticleTitle>Correspondence: a reply</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

TRIALS_FIXTURE = [
    {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT01234567", "briefTitle": "Parent Coaching for Toddlers With ASD"},
            "statusModule": {"overallStatus": "RECRUITING", "startDateStruct": {"date": "2024-03"}},
            "descriptionModule": {"briefSummary": "  This study tests a   parent coaching model.  "},
            "conditionsModule": {"conditions": ["Autism Spectrum Disorder", "Developmental Delay"]},
            "designModule": {"phases": ["PHASE2"]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "University of Example"}},
            "contactsLocationsModule": {
                "locations": [
                    {"facility": "Example Children's Hospital", "city": "Boston", "state": "Massachusetts", "country": "United States"},
                    {"city": "Bengaluru", "country": "India"},
                ]
            },
        }
    },
    # No brief summary -> must be dropped.
    {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT07654321", "briefTitle": "Registry Only"},
            "statusModule": {"overallStatus": "COMPLETED"},
        }
    },
    # Minimal but valid: no conditions, no phases, no locations, no sponsor.
    {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT09999999", "officialTitle": "An Observational Study of Sleep"},
            "statusModule": {"overallStatus": "UNKNOWN"},
            "descriptionModule": {"briefSummary": "Observational sleep study."},
        }
    },
]


failures: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual != expected:
        failures.append(f"  {label}\n    expected: {expected!r}\n    actual:   {actual!r}")


def test_pubmed() -> None:
    records = parse_pubmed_xml(PUBMED_FIXTURE)
    check("abstract-less record is dropped", len(records), 3)

    first = records[0]
    check("id", first["id"], "pmid-38212345")
    check("source_url", first["source_url"], "https://pubmed.ncbi.nlm.nih.gov/38212345/")
    check("title keeps text inside inline markup",
          first["title"], "Early markers in ASD: a cohort study")
    check("structured abstract labels are preserved",
          first["text"],
          "Background: Screening remains inconsistent. Methods: We followed 400 children to age 6.")
    check("group author survives", first["authors"], ["Smith J", "The ADDM Study Group"])
    check("full date", first["publication_date"], "2024-01-05")
    check("venue", first["venue"], "Journal of Autism and Developmental Disorders")

    check("numeric month, no day", records[1]["publication_date"], "2023-11")
    check("unlabelled abstract", records[1]["text"], "A randomised trial of parent coaching.")
    check("MedlineDate falls back to year", records[2]["publication_date"], "2023")
    check("missing AuthorList is empty, not an error", records[2]["authors"], [])


def test_trials() -> None:
    records = parse_studies(TRIALS_FIXTURE)
    check("summary-less study is dropped", len(records), 2)

    first = records[0]
    check("id", first["id"], "nct-NCT01234567")
    check("source_url", first["source_url"], "https://clinicaltrials.gov/study/NCT01234567")
    check("conditions and phase are folded into embedded text",
          first["text"],
          "Conditions: Autism Spectrum Disorder, Developmental Delay. Phase: PHASE2. "
          "This study tests a parent coaching model.")
    check("sponsor becomes authors", first["authors"], ["University of Example"])
    check("start date", first["publication_date"], "2024-03")
    check("locations formatted, partial ones tolerated",
          first["locations"],
          ["Example Children's Hospital, Boston, Massachusetts, United States", "Bengaluru, India"])

    second = records[1]
    check("officialTitle used when briefTitle absent", second["title"], "An Observational Study of Sleep")
    check("no conditions/phase means text is just the summary",
          second["text"], "Observational sleep study.")
    check("empty locations", second["locations"], [])


def test_schema_alignment() -> None:
    """Both sources must produce the same required keys — build_index.py
    reads them uniformly and would fail per-record otherwise."""
    required = {"id", "source", "title", "text", "source_url", "publication_date", "authors", "venue"}
    for record in parse_pubmed_xml(PUBMED_FIXTURE) + parse_studies(TRIALS_FIXTURE):
        missing = required - set(record)
        check(f"{record['id']} has all required keys", missing, set())


def main() -> None:
    test_pubmed()
    test_trials()
    test_schema_alignment()

    if failures:
        print(f"FAILED ({len(failures)} check(s)):\n")
        print("\n".join(failures))
        sys.exit(1)
    print("All parser checks passed.")


if __name__ == "__main__":
    main()
