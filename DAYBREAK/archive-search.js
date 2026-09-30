/* Daybreak archive search.
 *
 * Keyword search over every story in every past edition. Reads
 * DAYBREAK/data/daybreak-stories.json, which DAYBREAK/patch_daybreak.py
 * rebuilds each time an edition lands, and filters it in the browser —
 * no server, no index service. The file is only fetched once the reader
 * starts typing, so the calendar does not pay for it.
 *
 * Matching is plain keywords, not meaning: every word typed must start a
 * word in the story's headline, summary, category or section, ignoring case
 * and accents — "fed" finds "Fed" and "federal", not "confederation". Results are newest first and link to the story's section in its
 * edition. Each result is dated, because this is past reporting.
 */
(function () {
  "use strict";

  var STORIES_URL = "data/daybreak-stories.json";
  var MAX_RESULTS = 40;

  var input = document.getElementById("archive-q");
  var status = document.getElementById("archive-search-status");
  var list = document.getElementById("archive-results");
  if (!input || !status || !list) return;

  // Same rule as the calendar: inside the pop-up, keep the chrome off.
  var bare = document.documentElement.classList.contains("is-bare");
  var WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var stories = null;   // loaded on first use
  var loading = null;   // the in-flight fetch, so typing fast fetches once
  var timer = null;

  /* Lower-case and strip accents, so "Inacio" finds "Inácio". */
  function fold(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function isWordChar(c) {
    return /[a-z0-9]/.test(c || "");
  }

  /* Folded text as space-separated words, with a leading space, so that
   * " term" is found exactly where a word starts with the term. */
  function words(text) {
    return " " + fold(text).replace(/[^a-z0-9]+/g, " ");
  }

  function esc(text) {
    return text.replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* "2026-09-10" -> "Thu 10 Sep 2026", read as a local date (see archive.js). */
  function label(iso) {
    var p = iso.split("-");
    var d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    return WEEKDAYS[d.getDay()] + " " + d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear();
  }

  /* Wraps each term in <mark>. Works on the folded copy to find positions,
   * so accents and case never stop a highlight, then slices the original. */
  function highlight(text, terms) {
    var folded = fold(text);
    var marks = [];
    terms.forEach(function (term) {
      var at = folded.indexOf(term);
      while (at !== -1) {
        if (!isWordChar(folded[at - 1])) marks.push([at, at + term.length]);
        at = folded.indexOf(term, at + term.length);
      }
    });
    if (!marks.length || folded.length !== text.length) return esc(text);
    marks.sort(function (a, b) { return a[0] - b[0]; });
    var out = "", pos = 0;
    marks.forEach(function (m) {
      if (m[0] < pos) return; // overlapping match
      out += esc(text.slice(pos, m[0])) + "<mark>" + esc(text.slice(m[0], m[1])) + "</mark>";
      pos = m[1];
    });
    return out + esc(text.slice(pos));
  }

  function load() {
    if (!loading) {
      loading = fetch(STORIES_URL, { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) throw new Error("Story index unavailable (" + response.status + ")");
          return response.json();
        })
        .then(function (data) {
          stories = (data.stories || []).map(function (s) {
            s.haystack = words([s.headline, s.summary, s.category, s.section].join(" "));
            return s;
          });
        });
    }
    return loading;
  }

  function render(query) {
    var terms = fold(query).split(/[^a-z0-9]+/).filter(function (t) { return t.length >= 2; });
    list.textContent = "";
    if (!terms.length) {
      status.textContent = "";
      return;
    }
    var hits = stories.filter(function (s) {
      return terms.every(function (t) { return s.haystack.indexOf(" " + t) !== -1; });
    });
    if (!hits.length) {
      status.textContent = "No past stories mention " + query.trim() + ".";
      return;
    }
    var editions = {};
    hits.forEach(function (s) { editions[s.date] = true; });
    var editionCount = Object.keys(editions).length;
    status.textContent = hits.length + (hits.length === 1 ? " story" : " stories") +
      " in " + editionCount + (editionCount === 1 ? " edition" : " editions") +
      (hits.length > MAX_RESULTS ? ", showing the newest " + MAX_RESULTS : "") + ".";

    hits.slice(0, MAX_RESULTS).forEach(function (s) {
      var li = document.createElement("li");
      li.className = "archive-result";
      var href = s.file + (bare ? "?chrome=off" : "") + "#" + s.anchor;
      li.innerHTML =
        '<p class="archive-result-meta"><time datetime="' + esc(s.date) + '">' + esc(label(s.date)) +
        "</time> · " + esc(s.section) + "</p>" +
        '<a class="archive-result-headline" href="' + esc(href) + '">' + highlight(s.headline, terms) + "</a>" +
        '<p class="archive-result-summary">' + highlight(s.summary, terms) + "</p>";
      list.appendChild(li);
    });
  }

  function onInput() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var query = input.value;
      if (stories) {
        render(query);
        return;
      }
      if (query.trim()) status.textContent = "Loading past stories…";
      load()
        .then(function () { render(input.value); })
        .catch(function (error) {
          console.error(error);
          loading = null; // let the next keystroke retry
          status.textContent = "Past stories could not be loaded. Try again shortly.";
        });
    }, 150);
  }

  input.addEventListener("input", onInput);
  input.addEventListener("focus", function () { load().catch(function () { loading = null; }); }, { once: true });
  input.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      input.value = "";
      render("");
    }
  });
})();
