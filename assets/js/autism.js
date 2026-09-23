// Paste the deployed Worker URL here to switch the free-text box on, e.g.
// "https://sayantansen-autism-search.<account>.workers.dev/api/ask".
// Left empty the box stays hidden and the prepared-question dropdown still
// works, because that is precomputed and needs no backend at all.
const ASK_ENDPOINT = "";

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

// Two different score scales end up on this page, and they are not
// comparable. The prepared answers were scored offline by
// sentence-transformers; the live ones are scored by Workers AI. Run on the
// same question, Workers AI comes back about 0.065 lower — 0.742 against
// 0.812 for "is autism genetic". One set of bands would label every live
// result a grade weaker than the identical prepared one, which is worse
// than useless on a page about showing its working.
//
// Local bands come from experiments/autism-rag/calibrate.py; the Worker's
// are that measurement shifted by the offset above.
const SCORE_SCALES = {
  local: { strong: 0.8, moderate: 0.72 },
  worker: { strong: 0.735, moderate: 0.655 },
};

function scoreLabel(score, scale) {
  if (score >= scale.strong) return "strong match";
  if (score >= scale.moderate) return "moderate match";
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

const PREPARED_PREFIX = "prepared-result-";
const SOURCE_PREFIX = "source-";

function renderResults(entry, idPrefix, scale) {
  if (!entry.results.length) {
    return '<p class="placeholder">Nothing in the corpus scored above the relevance floor for this question.</p>';
  }

  return entry.results
    .map((r, i) => {
      const url = safeUrl(r.source_url);
      const title = esc(r.title);
      const cite = citation(r);
      return `
      <article class="result-card" id="${idPrefix}${i + 1}">
        <div class="result-rank">#${i + 1}</div>
        <div class="result-body">
          <div class="result-meta">
            <span class="result-score">${r.score.toFixed(3)}</span>
            <span class="result-score-label">${scoreLabel(r.score, scale)}</span>
            <span class="result-category">${esc(SOURCE_LABELS[r.source] || r.source || (r.category || "").replace(/_/g, " "))}</span>
          </div>
          <h3 class="result-title">${
            url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${title}</a>` : title
          }</h3>
          <p class="result-text is-clamped">${esc(r.text)}</p>
          ${cite ? `<p class="result-source">${cite}</p>` : ""}
        </div>
      </article>`;
    })
    .join("");
}

// Only appended when the Worker is actually wired up: until then nothing on
// the page is model-written, and the warning should not claim otherwise.
// renderProvenance() and initAsk() both call this and either may run first,
// so the data attribute makes the second call a no-op.
function applyAskNotice() {
  if (!ASK_ENDPOINT) return;
  const banner = document.getElementById("experiment-warning");
  if (banner.dataset.askNotice === "1") return;
  banner.dataset.askNotice = "1";
  banner.insertAdjacentHTML(
    "beforeend",
    " When you ask your own question a language model writes the summary at the top. " +
      "It is told to use only the retrieved records and to cite them, but it can still " +
      "misread them \u2014 the numbered citations go to the real papers, and those are " +
      "the record."
  );
}

// The corpus can be either the real fetched one or the old hand-written
// placeholder set, and the warning on the page has to stay true to whichever
// is actually loaded. Only build_page_data.py writes `meta`, so its presence
// is the signal that these results came from real, citable sources.
function renderProvenance(meta) {
  applyAskNotice();
  if (!meta) return;

  const counts = Object.entries(meta.counts || {})
    .map(([source, n]) => `${n} from ${esc(SOURCE_LABELS[source] || source)}`)
    .join(", ");
  document.getElementById("experiment-provenance").textContent =
    `Corpus: ${meta.document_count} documents (${counts}). ` +
    `Embedded with ${meta.model}. Built ${meta.generated}.`;
}

// Only the abstracts that genuinely overflow get a toggle. Measuring beats
// a character-count guess: four clamped lines hold far less text on a phone
// than on a desktop, so a fixed threshold would either add useless buttons
// or hide text with no way to reach it.
function addToggles(container) {
  container.querySelectorAll(".result-text").forEach((textEl) => {
    if (textEl.scrollHeight <= textEl.clientHeight + 2) {
      textEl.classList.remove("is-clamped");
      return;
    }
    const button = document.createElement("button");
    button.className = "result-toggle";
    button.type = "button";
    button.textContent = "Show more";
    button.setAttribute("aria-expanded", "false");
    button.addEventListener("click", () => {
      const clamped = textEl.classList.toggle("is-clamped");
      button.textContent = clamped ? "Show more" : "Show less";
      button.setAttribute("aria-expanded", String(!clamped));
    });
    textEl.insertAdjacentElement("afterend", button);
  });
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
      results.innerHTML = renderResults(faqData[Number(event.target.value)], PREPARED_PREFIX, SCORE_SCALES.local);
      addToggles(results);
    });
  } catch (err) {
    console.error(err);
    document.getElementById("results").innerHTML =
      '<p class="placeholder">Could not load the retrieval results.</p>';
  }
}

// ---------------------------------------------------------------- free text

function renderAnswer(data) {
  // Escape first, then linkify: the [n] markers survive escaping intact, so
  // turning them into links afterwards can't smuggle markup through.
  const body = esc(data.answer).replace(
    /\[(\d+)\]/g,
    (match, n) => `<a class="citation" href="#${SOURCE_PREFIX}${n}">[${n}]</a>`
  );

  const caveat = data.answer_is_generated
    ? `<p class="answer-caveat">Written by a language model from the sources below and
       nothing else. It can still misread them &mdash; the numbered links go to the
       actual papers, and those are the record.</p>`
    : "";

  return `
    <div class="answer-card">
      <p class="answer-label">${data.answer_is_generated ? "AI-written summary" : "No summary"}</p>
      <p class="answer-text">${body}</p>
      ${caveat}
    </div>`;
}

async function ask(question) {
  const button = document.getElementById("ask-button");
  const answerEl = document.getElementById("answer");
  const resultsEl = document.getElementById("ask-results");

  button.disabled = true;
  answerEl.innerHTML = '<p class="placeholder">Searching 1900 records\u2026</p>';
  resultsEl.innerHTML = "";

  try {
    const response = await fetch(ASK_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);

    answerEl.innerHTML = renderAnswer(data);
    resultsEl.innerHTML = renderResults({ results: data.results }, SOURCE_PREFIX, SCORE_SCALES.worker);
    addToggles(resultsEl);
  } catch (err) {
    console.error(err);
    answerEl.innerHTML = `<p class="ask-error">${esc(err.message)}</p>`;
  } finally {
    button.disabled = false;
  }
}

function initAsk() {
  if (!ASK_ENDPOINT) return;
  document.getElementById("ask-form").hidden = false;
  document.getElementById("ask-unavailable").hidden = true;
  applyAskNotice();
  document.getElementById("ask-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const question = document.getElementById("ask-input").value.trim();
    if (question) ask(question);
  });
}

loadFaq();
initAsk();
