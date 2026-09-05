const DATE_FORMAT = { day: "2-digit", month: "short", year: "numeric" };

function todayLabel() {
  const now = new Date();
  const datePart = now
    .toLocaleDateString("en-GB", DATE_FORMAT)
    .replace(/ /g, "-");
  const weekday = now.toLocaleDateString("en-US", { weekday: "long" });
  return { datePart, weekday };
}

function renderEdition() {
  const { datePart, weekday } = todayLabel();
  document.getElementById("db-edition").textContent = `${datePart.toUpperCase()} · ${weekday.toUpperCase()} EDITION`;
  document.getElementById("db-hero-title").textContent =
    `Today's Curated News for Sayantan Sen — ${datePart}`;
}

function renderCategories(sections) {
  const nav = document.getElementById("db-categories");
  nav.innerHTML = sections
    .map((section) => `<a href="#${section.id}">${section.label}</a>`)
    .join("");
}

function renderStats(stats) {
  const el = document.getElementById("db-stats");
  el.innerHTML = stats
    .map(
      (stat) => `
      <div class="db-stat">
        <div class="db-stat-label">${stat.label}</div>
        <div class="db-stat-value">${stat.value}</div>
        <div class="db-stat-note">${stat.note}</div>
      </div>`
    )
    .join("");
}

function renderStory(story, index) {
  const number = String(index + 1).padStart(2, "0");
  const sources = story.sources
    .map(
      (source) =>
        `<a class="db-source" href="${source.url}" target="_blank" rel="noopener">${source.label} ↗</a>`
    )
    .join("");
  return `
    <div class="db-story">
      <span class="db-story-num">${number}</span>
      <div>
        <p class="db-story-category">${story.category}</p>
        <h3 class="db-story-headline">${story.headline}</h3>
        <p class="db-story-summary">${story.summary}</p>
        <div class="db-sources">${sources}</div>
      </div>
    </div>`;
}

function renderSection(section) {
  const body = section.stories.length
    ? `<div class="db-story-grid">${section.stories.map(renderStory).join("")}</div>`
    : `<p class="placeholder">Nothing meaningful to report in this window.</p>`;
  return `
    <section id="${section.id}" class="db-section">
      <p class="db-section-kicker">${section.kicker}</p>
      <h2 class="db-section-title">${section.label}</h2>
      ${body}
    </section>`;
}

async function loadNews() {
  try {
    const response = await fetch("data/news.json");
    if (!response.ok) throw new Error(`Failed to load news.json (${response.status})`);
    const data = await response.json();

    renderEdition();
    renderCategories(data.sections);
    renderStats(data.stats);

    const container = document.getElementById("db-sections");
    container.innerHTML = data.sections.map(renderSection).join("");
  } catch (err) {
    document.getElementById("db-loading").textContent =
      "Couldn't load today's news. Try refreshing the page.";
    console.error(err);
  }
}

loadNews();
