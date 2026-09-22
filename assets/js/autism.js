let faqData = [];

const SOURCE_LABELS = {
  pubmed: "PubMed",
  clinicaltrials: "ClinicalTrials.gov",
};

// Every field below comes from PubMed or ClinicalTrials.gov, not from this
// repo, so nothing is interpolated into innerHTML unescaped.
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// Only ever link out to the two registries the corpus is built from.
function safeUrl(url) {
  return /^https:\/\/(pubmed\.ncbi\.nlm\.nih\.gov|clinicaltrials\.gov)\//.test(url) ? url : "";
}

// Dense embeddings sit in a much narrower band than the old TF-IDF scores —
// unrelated text still scores around 0.6, so these bands start higher.
// They are calibrated by eye and worth re-checking against real output.
function scoreLabel(score) {
  if (score >= 0.75) return "strong match";
  if (score >= 0.65) return "moderate match";
  return "weak match";
}

// `source_note` is the phase-1 shape: a hand-written provenance sentence
// rather than a real citation. Kept so the published page stays correct
// until data/autism-faq.json is regenerated from the real corpus.
function citation(r) {
  const bits = [r.authors, r.venue, r.publication_date].filter(Boolean);
  if (bits.length) return esc(bits.join(" · "));
  return r.source_note ? esc(r.source_note) : "";
}

function renderResults(entry) {
  if (!entry.results.length) {
    return '<p class="placeholder">Nothing in the corpus scored above the relevance floor for this question.</p>';
  }

  return entry.results
    .map((r, i) => {
      const url = safeUrl(r.source_url);
      const title = esc(r.title);
      const cite = citation(r);
      return `
      <article class="result-card">
        <div class="result-rank">#${i + 1}</div>
        <div class="result-body">
          <div class="result-meta">
            <span class="result-score">${r.score.toFixed(3)}</span>
            <span class="result-score-label">${scoreLabel(r.score)}</span>
            <span class="result-category">${esc(SOURCE_LABELS[r.source] || r.source || (r.category || "").replace(/_/g, " "))}</span>
          </div>
          <h3 class="result-title">${
            url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${title}</a>` : title
          }</h3>
          <p class="result-text">${esc(r.text)}</p>
          ${cite ? `<p class="result-source">${cite}</p>` : ""}
        </div>
      </article>`;
    })
    .join("");
}

// The corpus can be either the real fetched one or the old hand-written
// placeholder set, and the warning on the page has to stay true to whichever
// is actually loaded. Only build_page_data.py writes `meta`, so its presence
// is the signal that these results came from real, citable sources.
function renderProvenance(meta) {
  const banner = document.getElementById("experiment-warning");
  const provenance = document.getElementById("experiment-provenance");
  if (!meta) return;

  banner.innerHTML =
    "<strong>This is a retrieval experiment, not health information.</strong> " +
    "These are real published abstracts and trial records, returned verbatim by " +
    "a similarity search — they are not reviewed, ranked for quality, or checked " +
    "for whether they reflect current consensus. A high score means wording that " +
    "matched, nothing more. For actual guidance, talk to a paediatrician or a " +
    "developmental specialist.";

  const counts = Object.entries(meta.counts || {})
    .map(([source, n]) => `${n} from ${esc(SOURCE_LABELS[source] || source)}`)
    .join(", ");
  provenance.textContent =
    `Corpus: ${meta.document_count} documents (${counts}). ` +
    `Embedded with ${meta.model}. Built ${meta.generated}.`;
}

async function loadFaq() {
  try {
    const response = await fetch("data/autism-faq.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load autism-faq.json (${response.status})`);
    const data = await response.json();
    faqData = data.questions || [];
    renderProvenance(data.meta);

    const select = document.getElementById("question-select");
    faqData.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = entry.question;
      select.appendChild(option);
    });

    select.addEventListener("change", (event) => {
      const results = document.getElementById("results");
      if (event.target.value === "") {
        results.innerHTML = "";
        return;
      }
      results.innerHTML = renderResults(faqData[Number(event.target.value)]);
    });
  } catch (err) {
    console.error(err);
    document.getElementById("results").innerHTML =
      '<p class="placeholder">Could not load the retrieval results.</p>';
  }
}

loadFaq();
