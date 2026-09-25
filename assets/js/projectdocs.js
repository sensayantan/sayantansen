/* SenProjectDocumentation — renders data/project-docs.json as a backlog.
 *
 * Epics are collapsible groups holding stories; each story shows its
 * narrative, acceptance criteria and assumptions. Grouped by project, so a
 * second independently numbered set can be appended to the source file
 * without either set being renumbered.
 *
 * The rendered strings come from backend/render_project_docs.py, which has
 * already converted Markdown to HTML. Everything that is not deliberate
 * Markdown is set with textContent rather than innerHTML.
 */
(function () {
  "use strict";

  var DATA_URL = "data/project-docs.json";
  var STATUSES = ["Done", "In progress", "Blocked"];

  // Reuses the exact OAuth Worker and popup handshake the admin interface
  // (/admin) already uses — see oauth-proxy/src/{auth,callback}.js. This is a
  // client-side login wall, not a server-side access control: the JSON this
  // page fetches after sign-in is still an ordinary static file on GitHub
  // Pages, reachable directly by anyone who knows its URL. That trade is
  // deliberate and is documented in content/project-docs.yml, story 7.5 —
  // nothing on this page is sensitive enough to justify a Worker that
  // proxies and gates the file server-side.
  var AUTH_URL = "https://sayantansen-oauth.sen-sayantan.workers.dev/api/auth";
  var OWNER_LOGIN = "sensayantan";
  var SESSION_KEY = "senProjectDocsAuth";

  var gate = document.getElementById("doc-gate");
  var app = document.getElementById("doc-app");
  var signinButton = document.getElementById("doc-gate-signin");
  var gateStatus = document.getElementById("doc-gate-status");
  var sessionBox = document.getElementById("doc-session");

  var root = document.getElementById("backlog");
  var status = document.getElementById("backlog-status");
  if (!root || !gate || !app) return;

  var active = null; // null means "no filter"

  function readSession() {
    try {
      var raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function writeSession(value) {
    try {
      if (value) sessionStorage.setItem(SESSION_KEY, JSON.stringify(value));
      else sessionStorage.removeItem(SESSION_KEY);
    } catch (err) { /* private browsing, storage disabled, etc. — session just will not persist */ }
  }

  function renderSessionBox(login) {
    if (!sessionBox) return;
    sessionBox.textContent = "";
    sessionBox.appendChild(el("span", "doc-session-user", "Signed in as @" + login));
    var out = el("button", "doc-session-signout", "Sign out");
    out.type = "button";
    out.addEventListener("click", function () {
      writeSession(null);
      window.location.reload();
    });
    sessionBox.appendChild(out);
  }

  function showGateMessage(text) {
    if (gateStatus) gateStatus.textContent = text || "";
  }

  // Decap's own admin login uses this identical protocol against the same
  // Worker: the popup announces "authorizing:github", then sends
  // "authorization:github:success:<json>" (or ":error:<json>") to this
  // window. A 500ms fallback in the Worker sends the token even if this
  // page never replies to the announcement, so no reply is required here.
  function signIn() {
    showGateMessage("Opening GitHub sign-in…");
    var popup = window.open(AUTH_URL, "senProjectDocsAuth", "width=600,height=700,menubar=no,toolbar=no");
    if (!popup) {
      showGateMessage("Your browser blocked the sign-in pop-up. Please allow pop-ups for this site and try again.");
      return;
    }

    function onMessage(event) {
      if (typeof event.data !== "string") return;
      if (event.data === "authorizing:github") return; // just the announcement
      var m = /^authorization:github:(success|error):(.*)$/.exec(event.data);
      if (!m) return;
      window.removeEventListener("message", onMessage);

      if (m[1] === "error") {
        showGateMessage("GitHub sign-in failed. Please try again.");
        return;
      }
      var payload;
      try { payload = JSON.parse(m[2]); } catch (err) { payload = null; }
      if (!payload || !payload.token) {
        showGateMessage("GitHub sign-in did not return a token. Please try again.");
        return;
      }
      verifyAndEnter(payload.token);
    }
    window.addEventListener("message", onMessage);
  }

  function verifyAndEnter(token) {
    showGateMessage("Checking your GitHub account…");
    fetch("https://api.github.com/user", { headers: { Authorization: "token " + token } })
      .then(function (response) {
        if (!response.ok) throw new Error("GitHub identity check failed (" + response.status + ")");
        return response.json();
      })
      .then(function (user) {
        if (user.login !== OWNER_LOGIN) {
          showGateMessage("Signed in as @" + user.login + ", but this documentation is limited to the site owner.");
          return;
        }
        writeSession({ token: token, login: user.login });
        enter(user.login);
      })
      .catch(function (err) {
        console.error(err);
        showGateMessage("Could not verify your GitHub account. Please try again.");
      });
  }

  function enter(login) {
    gate.hidden = true;
    app.hidden = false;
    renderSessionBox(login);
    loadAndRender();
  }

  var existing = readSession();
  if (existing && existing.login === OWNER_LOGIN) {
    enter(existing.login);
  } else if (signinButton) {
    signinButton.addEventListener("click", signIn);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* Only for fields the renderer produced from Markdown. */
  function rich(tag, className, html) {
    var node = el(tag, className);
    node.innerHTML = html || "";
    return node;
  }

  function statusClass(name) {
    return "chip chip-" + String(name).toLowerCase().replace(/[^a-z]+/g, "-");
  }

  function list(className, items, label) {
    if (!items || !items.length) return null;
    var wrap = el("div", className);
    wrap.appendChild(el("h5", "backlog-sublabel", label));
    var ul = el("ul");
    items.forEach(function (item) { ul.appendChild(rich("li", null, item)); });
    wrap.appendChild(ul);
    return wrap;
  }

  function renderStory(story) {
    var card = el("article", "story");
    card.dataset.status = story.status;

    var head = el("div", "story-head");
    head.appendChild(el("span", "story-key", story.number));
    head.appendChild(el("h4", "story-title", story.title));
    var chip = el("span", statusClass(story.status) + (story.known_status ? "" : " chip-other"), story.status);
    head.appendChild(chip);
    card.appendChild(head);

    if (story.narrative) card.appendChild(rich("p", "story-narrative", story.narrative));

    var ac = list("story-block", story.acceptance_criteria, "Acceptance criteria");
    if (ac) card.appendChild(ac);
    var as = list("story-block story-assumptions", story.assumptions, "Assumptions");
    if (as) card.appendChild(as);
    if (story.notes) {
      var notes = el("div", "story-block story-notes");
      notes.appendChild(el("h5", "backlog-sublabel", "Notes"));
      notes.appendChild(rich("p", null, story.notes));
      card.appendChild(notes);
    }
    return card;
  }

  function renderEpic(epic) {
    // <details> gives collapse behaviour, keyboard support and find-in-page
    // without any state to manage.
    var box = el("details", "epic");
    box.open = true;

    var summary = el("summary", "epic-head");
    summary.appendChild(el("span", "epic-key", epic.key));
    summary.appendChild(el("span", "epic-title", epic.title));
    summary.appendChild(el("span", "epic-progress", epic.done + " of " + epic.total + " done"));
    summary.appendChild(el("span", statusClass(epic.status), epic.status));
    box.appendChild(summary);

    if (epic.summary) box.appendChild(rich("p", "epic-summary", epic.summary));

    var stories = el("div", "epic-stories");
    epic.stories.forEach(function (s) { stories.appendChild(renderStory(s)); });
    box.appendChild(stories);
    return box;
  }

  function applyFilter() {
    var epics = root.querySelectorAll(".epic");
    Array.prototype.forEach.call(epics, function (box) {
      var shown = 0;
      Array.prototype.forEach.call(box.querySelectorAll(".story"), function (card) {
        var match = !active || card.dataset.status === active;
        card.hidden = !match;
        if (match) shown++;
      });
      // Hide an epic entirely when the filter leaves it with nothing, rather
      // than showing an empty group.
      box.hidden = shown === 0;
      if (shown > 0) box.open = true;
    });
  }

  function renderFilters(container) {
    container.textContent = "";
    ["All"].concat(STATUSES).forEach(function (name) {
      var button = el("button", "backlog-filter", name);
      button.type = "button";
      var value = name === "All" ? null : name;
      if (value === active) button.classList.add("is-active");
      button.addEventListener("click", function () {
        active = value;
        renderFilters(container);
        applyFilter();
      });
      container.appendChild(button);
    });
  }

  function appendix(container, data) {
    container.textContent = "";
    [["Definition of done", data.definition_of_done],
     ["Out of scope", data.out_of_scope]].forEach(function (pair) {
      if (!pair[1] || !pair[1].length) return;
      var box = el("section", "backlog-appendix-block");
      box.appendChild(el("h2", null, pair[0]));
      var ul = el("ul");
      pair[1].forEach(function (item) { ul.appendChild(rich("li", null, item)); });
      box.appendChild(ul);
      container.appendChild(box);
    });
  }

  function overview(container, data) {
    container.textContent = "";
    if (data.purpose) {
      container.appendChild(el("h2", "backlog-h2", "Document purpose"));
      container.appendChild(rich("p", null, data.purpose));
    }
    if (data.vision) {
      container.appendChild(el("h2", "backlog-h2", "Product vision"));
      container.appendChild(rich("p", "backlog-vision", data.vision));
    }
    if (data.principles && data.principles.length) {
      container.appendChild(el("h2", "backlog-h2", "Core principles"));
      var ol = el("ol", "backlog-principles");
      data.principles.forEach(function (p) { ol.appendChild(rich("li", null, p)); });
      container.appendChild(ol);
    }
  }

  function renderBacklogTable(container, items) {
    container.textContent = "";
    if (!items || !items.length) return;

    var section = el("section", "backlog-table-block");
    section.id = "backlog-table";
    section.appendChild(el("h2", "backlog-h2", "Backlog"));
    section.appendChild(el(
      "p", "backlog-table-intro",
      "Identified work that has not been built yet, most recently identified first."
    ));

    var table = el("table", "backlog-table");
    var thead = el("thead");
    var headRow = el("tr");
    ["Epic name", "Backlog description", "Type", "Date of backlog"].forEach(function (label) {
      headRow.appendChild(el("th", null, label));
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = el("tbody");
    items.forEach(function (item) {
      var row = el("tr");
      row.appendChild(el("td", "backlog-table-epic", item.epic));

      var descCell = el("td", "backlog-table-desc");
      descCell.appendChild(el("p", "backlog-table-title", item.title));
      if (item.description) descCell.appendChild(rich("p", "backlog-table-body", item.description));
      row.appendChild(descCell);

      var typeCell = el("td");
      typeCell.appendChild(el("span", typeClass(item.type) + (item.known_type ? "" : " chip-other"), item.type));
      row.appendChild(typeCell);

      row.appendChild(el("td", "backlog-table-date", item.date || "—"));
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    section.appendChild(table);
    container.appendChild(section);
  }

  function typeClass(name) {
    return "chip chip-type-" + String(name).toLowerCase().replace(/[^a-z]+/g, "-");
  }

  function loadAndRender() {
    fetch(DATA_URL, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("project-docs.json unavailable (" + response.status + ")");
        return response.json();
      })
      .then(function (data) {
        if (data.title) {
          document.title = data.title;
          var heading = document.getElementById("backlog-title");
          if (heading) heading.textContent = data.title;
        }

        overview(document.getElementById("backlog-overview"), data);

        var counts = document.getElementById("backlog-counts");
        if (counts && data.totals) {
          counts.textContent = data.totals.epics + " epics · " + data.totals.stories +
            " stories done · " + data.totals.backlog + " in backlog";
        }
        renderFilters(document.getElementById("backlog-filters"));

        root.textContent = "";
        (data.projects || []).forEach(function (project) {
          var section = el("section", "backlog-project");
          // Only label the project when there is more than one, so a single
          // set does not carry a redundant heading.
          if ((data.projects || []).length > 1) {
            section.appendChild(el("h2", "backlog-project-name", project.name));
          }
          project.epics.forEach(function (e) { section.appendChild(renderEpic(e)); });
          root.appendChild(section);
        });

        renderBacklogTable(document.getElementById("backlog-table-section"), data.backlog);
        appendix(document.getElementById("backlog-appendix"), data);
        applyFilter();
      })
      .catch(function (error) {
        console.error(error);
        if (status) status.textContent = "The backlog could not be loaded.";
      });
  }
})();
