let faqData = [];

function scoreLabel(score) {
  if (score >= 0.35) return "strong match";
  if (score >= 0.15) return "weak match";
  return "very weak match";
}

function renderResults(entry) {
  if (!entry.results.length) {
    return '<p class="placeholder">Nothing in the corpus shared enough vocabulary with this question to score above zero.</p>';
  }

  return entry.results
    .map((r, i) => `
      <article class="result-card">
        <div class="result-rank">#${i + 1}</div>
        <div class="result-body">
          <div class="result-meta">
            <span class="result-score">${r.score.toFixed(3)}</span>
            <span class="result-score-label">${scoreLabel(r.score)}</span>
            <span class="result-category">${r.category.replace(/_/g, " ")}</span>
          </div>
          <h3 class="result-title">${r.title}</h3>
          <p class="result-text">${r.text}</p>
          <p class="result-source">${r.source_note}</p>
        </div>
      </article>`)
    .join("");
}

async function loadFaq() {
  try {
    const response = await fetch("data/autism-faq.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load autism-faq.json (${response.status})`);
    const data = await response.json();
    faqData = data.questions || [];

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
