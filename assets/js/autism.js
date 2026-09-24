// The deployed Worker URL. Both question modes go through it: the dropdown
// and the free-text box ask the same endpoint, so both get the same
// retrieval, the same prompt and the same model.
//
// Left empty, or if the request fails, the dropdown falls back to the
// precomputed results in data/autism-faq.json — ranked sources, no summary —
// so the page keeps working without a backend. The free-text box has no such
// fallback and hides itself.
const ASK_ENDPOINT = "https://sayantansen-autism-search.sen-sayantan.workers.dev/api/ask";

let faqData = [];

const SOURCE_LABELS = {
  pubmed: "PubMed",
  clinicaltrials: "ClinicalTrials.gov",
};

// The two panels render into different containers and namespace their card
// ids separately — with two sets of cards on one page a shared "result-N"
// scheme collides, and getElementById returns the first match, which sent
// every citation to the wrong section's card.
const SECTIONS = {
  prepared: { answer: "prepared-answer", results: "results", prefix: "prepared-source-" },
  ask: { answer: "answer", results: "ask-results", prefix: "source-" },
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

// Two score scales can appear on this page and they are not comparable. Live
// answers are scored by Workers AI; the fallback data was scored offline by
// sentence-transformers. On the same question Workers AI comes back about
// 0.065 lower — 0.742 against 0.812 for "is autism genetic" — so one set of
// bands would label a live result a grade weaker than the identical cached
// one.
//
// Local bands come from experiments/autism-rag/calibrate.py; the Worker's are
// that measurement shifted by the offset above.
const SCORE_SCALES = {
  local: { strong: 0.8, moderate: 0.72 },
  worker: { strong: 0.735, moderate: 0.655 },
};

function scoreLabel(score, scale) {
  if (score >= scale.strong) return "strong match";
  if (score >= scale.moderate) return "moderate match";
  return "weak match";
}

function citation(r) {
  const bits = [r.authors, r.venue, r.publication_date].filter(Boolean);
  return bits.length ? esc(bits.join(" · ")) : "";
}

// ------------------------------------------------------------------ sources

function renderSources(results, idPrefix, scale) {
  if (!results.length) {
    return '<p class="placeholder">Nothing in the corpus scored above the relevance floor for this question.</p>';
  }

  const cards = results
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
            <span class="result-category">${esc(SOURCE_LABELS[r.source] || r.source || "")}</span>
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

  // Open by default — the citations in the summary link into these cards, so
  // a collapsed block would make every one of them jump into hidden content.
  // Collapsible because most readers want the summary, not ten abstracts.
  const noun = results.length === 1 ? "record" : "records";
  return `
    <details class="sources-block" open>
      <summary class="sources-summary">Sources<span class="sources-hint">${results.length} ${noun}, ranked by similarity</span></summary>
      <div class="sources-list">${cards}</div>
    </details>`;
}

// Only the abstracts that genuinely overflow get a toggle. Measuring beats a
// character-count guess: four clamped lines hold far less text on a phone
// than on a desktop, so a fixed threshold would either add useless buttons or
// hide text with no way to reach it.
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

// ------------------------------------------------------------------- answer

function renderAnswer(data, idPrefix) {
  // Escape first, then linkify: the [n] markers survive escaping intact, so
  // turning them into links afterwards can't smuggle markup through.
  //
  // Only numbers matching a real source become links. The model is told how
  // many sources it has and still overshoots — a real answer closed with
  // "[5]" against four sources — and a citation pointing at a card that
  // isn't there is worse than no link at all on a page whose whole promise is
  // that every claim is checkable. Out-of-range markers stay plain text.
  const sourceCount = (data.results || []).length;
  const body = esc(data.answer).replace(/\[(\d+)\]/g, (match, n) => {
    const index = Number(n);
    if (index < 1 || index > sourceCount) return match;
    return `<a class="citation" href="#${idPrefix}${index}">[${index}]</a>`;
  });

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

// One path for both panels. The dropdown and the free-text box differ only in
// where they put the result and whether a cached answer exists to fall back
// on.
async function answerQuestion(question, section, fallbackEntry) {
  const answerEl = document.getElementById(section.answer);
  const resultsEl = document.getElementById(section.results);

  answerEl.innerHTML = '<p class="placeholder">Searching 1,900 records…</p>';
  resultsEl.innerHTML = "";

  try {
    if (!ASK_ENDPOINT) throw new Error("Search service not configured.");
    const response = await fetch(ASK_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);

    answerEl.innerHTML = renderAnswer(data, section.prefix);
    resultsEl.innerHTML = renderSources(data.results, section.prefix, SCORE_SCALES.worker);
    addToggles(resultsEl);
  } catch (err) {
    console.error(err);
    if (!fallbackEntry) {
      answerEl.innerHTML = `<p class="ask-error">${esc(err.message)}</p>`;
      return;
    }
    // The precomputed results carry no summary, so say so rather than
    // leaving a blank space where one usually is.
    answerEl.innerHTML =
      '<p class="ask-error">The live search is unavailable, so this is the stored ' +
      'result for this question: the same ranked sources, without a summary.</p>';
    resultsEl.innerHTML = renderSources(fallbackEntry.results, section.prefix, SCORE_SCALES.local);
    addToggles(resultsEl);
  }
}

// -------------------------------------------------------------- page wiring

// Only appended when the Worker is wired up: until then nothing on the page
// is model-written and the warning should not claim otherwise. Both callers
// may run first, so the data attribute makes the second call a no-op.
function applyAskNotice() {
  if (!ASK_ENDPOINT) return;
  const banner = document.getElementById("experiment-warning");
  if (banner.dataset.askNotice === "1") return;
  banner.dataset.askNotice = "1";
  banner.insertAdjacentHTML(
    "beforeend",
    " Whichever way you ask, a language model writes the summary at the top. " +
      "It is told to use only the retrieved records and to cite them, but it can still " +
      "misread them — the numbered citations go to the real papers, and those are " +
      "the record."
  );
}

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

async function loadFaq() {
  const select = document.getElementById("question-select");
  try {
    const response = await fetch("data/autism-faq.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load autism-faq.json (${response.status})`);
    const data = await response.json();
    faqData = data.questions || [];
    renderProvenance(data.meta);

    faqData.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = entry.question;
      select.appendChild(option);
    });

    select.addEventListener("change", (event) => {
      if (event.target.value === "") {
        document.getElementById(SECTIONS.prepared.answer).innerHTML = "";
        document.getElementById(SECTIONS.prepared.results).innerHTML = "";
        return;
      }
      const entry = faqData[Number(event.target.value)];
      answerQuestion(entry.question, SECTIONS.prepared, entry);
    });
  } catch (err) {
    console.error(err);
    document.getElementById(SECTIONS.prepared.results).innerHTML =
      '<p class="placeholder">Could not load the prepared questions.</p>';
  }
}

function initAsk() {
  if (!ASK_ENDPOINT) return;
  document.getElementById("ask-form").hidden = false;
  document.getElementById("ask-unavailable").hidden = true;
  applyAskNotice();

  document.getElementById("ask-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = document.getElementById("ask-input").value.trim();
    if (!question) return;
    const button = document.getElementById("ask-button");
    button.disabled = true;
    try {
      await answerQuestion(question, SECTIONS.ask, null);
    } finally {
      button.disabled = false;
    }
  });
}

loadFaq();
initAsk();
