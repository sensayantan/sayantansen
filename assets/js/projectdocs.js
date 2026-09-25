/* SenProjectDocumentation — renders data/project-docs.json as a backlog, and
 * lets a signed-in owner add, edit and delete Backlog table rows in place.
 *
 * Epics and stories are read-only here and come from data/project-docs.json,
 * which backend/render_project_docs.py already converted from Markdown to
 * HTML — those are edited through the admin's Project Documentation
 * collection instead of here, because their nested acceptance-criteria and
 * assumption lists are much easier to get wrong with hand-rolled text
 * surgery than the flat, five-field Backlog rows are.
 *
 * The Backlog table is different: once signed in, it is read from and
 * written straight back to content/project-docs.yml on GitHub, using the
 * exact same GitHub Contents API Decap's own admin uses, and the exact same
 * OAuth token this page's own sign-in already obtained. Saving edits only
 * the `backlog:` block of that file — every byte before and after it,
 * including the schema comments at the top of the file and every epic and
 * story, is left untouched.
 */
(function () {
  "use strict";

  var DATA_URL = "data/project-docs.json";
  var STATUSES = ["Done", "In progress", "Blocked"];
  var BACKLOG_TYPES = ["Technical Debt", "Feature Enhancement", "Feature Development"];

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

  // The Backlog editor talks to this repo directly over the GitHub REST API,
  // using the same repo-scoped token Decap's own login already carries —
  // this adds no new capability the token did not already have.
  var REPO_OWNER = "sensayantan";
  var REPO_NAME = "sayantansen";
  var CONTENT_PATH = "content/project-docs.yml";
  var CONTENT_BRANCH = "main";
  var CONTENT_API = "https://api.github.com/repos/" + REPO_OWNER + "/" + REPO_NAME +
    "/contents/" + CONTENT_PATH;

  var gate = document.getElementById("doc-gate");
  var app = document.getElementById("doc-app");
  var signinButton = document.getElementById("doc-gate-signin");
  var gateStatus = document.getElementById("doc-gate-status");
  var sessionBox = document.getElementById("doc-session");

  var root = document.getElementById("backlog");
  var status = document.getElementById("backlog-status");
  if (!root || !gate || !app) return;

  var active = null; // null means "no filter"
  var knownEpicTitles = []; // filled from data.projects once loaded, used by the Add/Edit form

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

  function typeClass(name) {
    return "chip chip-type-" + String(name).toLowerCase().replace(/[^a-z]+/g, "-");
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
        // The toolbar sits above a long, seven-epic page; without this a
        // click had no visible effect unless the reader happened to already
        // be scrolled down to the epics themselves.
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      container.appendChild(button);
    });

    var jump = el("button", "backlog-filter backlog-filter-jump", "Backlog ↓");
    jump.type = "button";
    jump.addEventListener("click", function () {
      var table = document.getElementById("backlog-table-section");
      if (table) table.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    container.appendChild(jump);
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

  // ---------------------------------------------------------------------
  // Backlog table: rendering (read-only rows, plus edit controls when the
  // page can write back to GitHub) and the GitHub read/write plumbing.
  // ---------------------------------------------------------------------

  function renderBacklogTable(container, items, opts) {
    opts = opts || {};
    container.textContent = "";
    items = (items || []).slice().sort(function (a, b) {
      var da = a.date || "", db = b.date || "";
      return da < db ? 1 : da > db ? -1 : 0;
    });

    var section = el("section", "backlog-table-block");
    section.id = "backlog-table";
    section.appendChild(el("h2", "backlog-h2", "Backlog"));
    section.appendChild(el(
      "p", "backlog-table-intro",
      "Identified work that has not been built yet, most recently identified first."
    ));

    if (opts.note) section.appendChild(el("p", "backlog-table-note", opts.note));

    if (opts.editable) {
      var add = el("button", "backlog-add-button", "+ Add backlog item");
      add.type = "button";
      add.addEventListener("click", function () { openBacklogEditor(null); });
      section.appendChild(add);
    }

    if (items && items.length) {
      var table = el("table", "backlog-table");
      var thead = el("thead");
      var headRow = el("tr");
      ["Epic name", "Backlog description", "Type", "Date of backlog"].forEach(function (label) {
        headRow.appendChild(el("th", null, label));
      });
      if (opts.editable) headRow.appendChild(el("th", null, " "));
      thead.appendChild(headRow);
      table.appendChild(thead);

      var tbody = el("tbody");
      items.forEach(function (item) {
        var row = el("tr");
        row.appendChild(el("td", "backlog-table-epic", item.epic));

        var descCell = el("td", "backlog-table-desc");
        descCell.appendChild(el("p", "backlog-table-title", item.title));
        // opts.editable rows come straight from YAML (plain text); rows from
        // the static JSON fallback already have Markdown rendered to HTML.
        if (item.description) {
          descCell.appendChild(
            opts.editable
              ? el("p", "backlog-table-body", item.description)
              : rich("p", "backlog-table-body", item.description)
          );
        }
        row.appendChild(descCell);

        var typeCell = el("td");
        typeCell.appendChild(el("span", typeClass(item.type) + (item.known_type === false ? " chip-other" : ""), item.type));
        row.appendChild(typeCell);

        row.appendChild(el("td", "backlog-table-date", item.date || "—"));

        if (opts.editable) {
          var actionsCell = el("td", "backlog-table-actions");
          var editBtn = el("button", "backlog-row-action", "Edit");
          editBtn.type = "button";
          editBtn.addEventListener("click", function () { openBacklogEditor(item); });
          var delBtn = el("button", "backlog-row-action backlog-row-danger", "Delete");
          delBtn.type = "button";
          delBtn.addEventListener("click", function () { confirmDeleteBacklogItem(item); });
          actionsCell.appendChild(editBtn);
          actionsCell.appendChild(delBtn);
          row.appendChild(actionsCell);
        }

        tbody.appendChild(row);
      });
      table.appendChild(tbody);
      section.appendChild(table);
    } else if (!opts.editable) {
      return; // nothing to show and nothing to add — match the old behaviour
    }

    container.appendChild(section);
  }

  function utf8ToBase64(str) {
    var bytes = new TextEncoder().encode(str);
    var binary = "";
    var chunk = 0x8000;
    for (var i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  function base64ToUtf8(b64) {
    var binary = atob(String(b64).replace(/\n/g, ""));
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder("utf-8").decode(bytes);
  }

  function githubHeaders(token) {
    return { Authorization: "token " + token, Accept: "application/vnd.github+json" };
  }

  function getContentFile(token) {
    return fetch(CONTENT_API + "?ref=" + CONTENT_BRANCH, { headers: githubHeaders(token), cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("Could not read " + CONTENT_PATH + " (" + r.status + ")");
        return r.json();
      })
      .then(function (json) {
        return { text: base64ToUtf8(json.content), sha: json.sha };
      });
  }

  function putContentFile(token, text, sha, message) {
    return fetch(CONTENT_API, {
      method: "PUT",
      headers: Object.assign({ "Content-Type": "application/json" }, githubHeaders(token)),
      body: JSON.stringify({
        message: message,
        content: utf8ToBase64(text),
        sha: sha,
        branch: CONTENT_BRANCH,
      }),
    }).then(function (r) {
      if (!r.ok) {
        return r.json().catch(function () { return {}; }).then(function (body) {
          var err = new Error((body && body.message) || ("Could not save (" + r.status + ")"));
          err.status = r.status;
          throw err;
        });
      }
      return r.json();
    });
  }

  function dateToIso(value) {
    if (value && typeof value === "object" && typeof value.toISOString === "function") {
      return value.toISOString().slice(0, 10);
    }
    return value ? String(value) : "";
  }

  // window.jsyaml parses any valid YAML the admin's own Decap form might
  // have written, even if its own serialization style differs from ours —
  // only the WRITE side below has to match a fixed shape, not this read side.
  function parseBacklogFromYamlText(text) {
    var parsed;
    try {
      parsed = window.jsyaml.load(text);
    } catch (err) {
      throw new Error("The stored file is not valid YAML: " + err.message);
    }
    var items = (parsed && parsed.backlog) || [];
    return items.map(function (item) {
      return {
        epic: String(item.epic || ""),
        title: String(item.title || ""),
        description: String(item.description || ""),
        type: String(item.type || "Feature Development"),
        date: dateToIso(item.date),
      };
    });
  }

  function yamlQuote(str) {
    // A double-quoted YAML scalar. JSON's escaping (backslash, double-quote,
    // control characters) is a valid subset of YAML double-quoted escaping,
    // so JSON.stringify always produces a safe, single-line YAML scalar here
    // — verified against both js-yaml and PyYAML, including a title and
    // description containing embedded quotes, a backslash and a newline.
    return JSON.stringify(String(str == null ? "" : str));
  }

  function serializeBacklogYaml(items) {
    var sorted = items.slice().sort(function (a, b) {
      return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
    });
    var lines = ["backlog:"];
    sorted.forEach(function (item) {
      lines.push("  - epic: " + yamlQuote(item.epic));
      lines.push("    title: " + yamlQuote(item.title));
      lines.push("    description: " + yamlQuote(item.description || ""));
      lines.push("    type: " + item.type);
      lines.push("    date: " + item.date);
    });
    return lines.join("\n") + "\n";
  }

  // Rewrites only the `backlog:` block. Everything before it (the schema
  // comments, `document:`, every epic and story) and everything after it
  // (`definition_of_done:`, `out_of_scope:`) is passed through untouched —
  // verified byte-for-byte against the real file before this shipped.
  function replaceBacklogBlock(rawText, items) {
    var newBlock = serializeBacklogYaml(items);
    var startMatch = /^backlog:[ \t]*$/m.exec(rawText);
    if (!startMatch) {
      var anchor = /^definition_of_done:[ \t]*$/m.exec(rawText) || /^out_of_scope:[ \t]*$/m.exec(rawText);
      if (anchor) return rawText.slice(0, anchor.index) + newBlock + "\n" + rawText.slice(anchor.index);
      return rawText.replace(/\n?$/, "\n\n" + newBlock);
    }
    var afterStart = startMatch.index + startMatch[0].length;
    var nextKey = /\n([A-Za-z_][A-Za-z0-9_]*):[ \t]*\n/g;
    nextKey.lastIndex = afterStart;
    var m = nextKey.exec(rawText);
    var endIndex = m ? m.index + 1 : rawText.length;
    return rawText.slice(0, startMatch.index) + newBlock + "\n" + rawText.slice(endIndex);
  }

  function itemsEqual(a, b) {
    return a.epic === b.epic && a.title === b.title && a.description === b.description &&
      a.type === b.type && a.date === b.date;
  }

  // Re-fetches the file fresh immediately before every save, and applies the
  // intended change against THAT copy rather than a possibly-stale one held
  // since the page loaded — narrowing, though not eliminating, the window
  // for a lost concurrent edit made through the admin in another tab.
  function withFreshBacklog(token, mutate) {
    return getContentFile(token).then(function (file) {
      var items = parseBacklogFromYamlText(file.text);
      var result = mutate(items);
      if (result === null) return null; // mutate() signals "nothing to do"
      var newText = replaceBacklogBlock(file.text, result.items);
      return putContentFile(token, newText, file.sha, result.message).then(function () {
        return result.items;
      });
    });
  }

  function saveBacklogItem(existingItem, values) {
    var session = readSession();
    if (!session) return Promise.reject(new Error("Not signed in."));
    return withFreshBacklog(session.token, function (fresh) {
      if (existingItem) {
        var index = -1;
        for (var i = 0; i < fresh.length; i++) {
          if (itemsEqual(fresh[i], existingItem)) { index = i; break; }
        }
        if (index === -1) {
          throw new Error("This item changed since the page loaded. Reloading the current backlog — please try your edit again.");
        }
        var next = fresh.slice();
        next[index] = values;
        return { items: next, message: "Update backlog item: " + values.title };
      }
      return { items: fresh.concat([values]), message: "Add backlog item: " + values.title };
    });
  }

  function deleteBacklogItemRemote(item) {
    var session = readSession();
    if (!session) return Promise.reject(new Error("Not signed in."));
    return withFreshBacklog(session.token, function (fresh) {
      var next = fresh.filter(function (x) { return !itemsEqual(x, item); });
      if (next.length === fresh.length) {
        // Already gone — nothing to delete, but still worth re-rendering
        // against the fresh list in case something else changed too.
        return { items: fresh, message: "" };
      }
      return { items: next, message: "Delete backlog item: " + item.title };
    });
  }

  function confirmDeleteBacklogItem(item) {
    if (!window.confirm('Delete "' + item.title + '" from the backlog?')) return;
    deleteBacklogItemRemote(item)
      .then(function (items) {
        renderBacklogTable(document.getElementById("backlog-table-section"), items, { editable: true });
      })
      .catch(function (err) {
        console.error(err);
        window.alert("Could not delete that item: " + err.message);
      });
  }

  var editorOverlay = null;

  function closeBacklogEditor() {
    if (editorOverlay && editorOverlay.parentNode) editorOverlay.parentNode.removeChild(editorOverlay);
    editorOverlay = null;
  }

  function field(labelText, inputEl) {
    var wrap = el("label", "backlog-editor-field");
    wrap.appendChild(el("span", "backlog-editor-label", labelText));
    wrap.appendChild(inputEl);
    return wrap;
  }

  function openBacklogEditor(existingItem) {
    closeBacklogEditor();

    var isEdit = !!existingItem;
    var today = new Date().toISOString().slice(0, 10);

    var epicSelect = document.createElement("select");
    var epicOptions = knownEpicTitles.slice();
    if (isEdit && epicOptions.indexOf(existingItem.epic) === -1) epicOptions.unshift(existingItem.epic);
    epicOptions.forEach(function (title) {
      var opt = document.createElement("option");
      opt.value = title; opt.textContent = title;
      epicSelect.appendChild(opt);
    });
    if (isEdit) epicSelect.value = existingItem.epic;

    var titleInput = document.createElement("input");
    titleInput.type = "text"; titleInput.required = true; titleInput.maxLength = 200;
    titleInput.value = isEdit ? existingItem.title : "";

    var descInput = document.createElement("textarea");
    descInput.rows = 4;
    descInput.value = isEdit ? existingItem.description : "";

    var typeSelect = document.createElement("select");
    BACKLOG_TYPES.forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t; opt.textContent = t;
      typeSelect.appendChild(opt);
    });
    typeSelect.value = isEdit ? existingItem.type : "Feature Development";

    var dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.value = isEdit ? existingItem.date : today;

    var form = el("form", "backlog-editor-form");
    form.appendChild(field("Epic", epicSelect));
    form.appendChild(field("Title", titleInput));
    form.appendChild(field("Backlog description", descInput));
    form.appendChild(field("Type", typeSelect));
    form.appendChild(field("Date of backlog", dateInput));

    var editorStatus = el("p", "backlog-editor-status");

    var saveBtn = el("button", "backlog-editor-save", isEdit ? "Save changes" : "Add to backlog");
    saveBtn.type = "submit";
    var cancelBtn = el("button", "backlog-editor-cancel", "Cancel");
    cancelBtn.type = "button";
    cancelBtn.addEventListener("click", closeBacklogEditor);

    var actions = el("div", "backlog-editor-actions");
    actions.appendChild(saveBtn);
    actions.appendChild(cancelBtn);
    form.appendChild(actions);
    form.appendChild(editorStatus);

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var values = {
        epic: epicSelect.value,
        title: titleInput.value.trim(),
        description: descInput.value.trim(),
        type: typeSelect.value,
        date: dateInput.value,
      };
      if (!values.title || !values.epic || !values.date) {
        editorStatus.textContent = "Epic, title and date are all required.";
        return;
      }
      saveBtn.disabled = true;
      editorStatus.textContent = "Saving to GitHub…";
      saveBacklogItem(isEdit ? existingItem : null, values)
        .then(function (items) {
          renderBacklogTable(document.getElementById("backlog-table-section"), items, { editable: true });
          closeBacklogEditor();
        })
        .catch(function (err) {
          console.error(err);
          saveBtn.disabled = false;
          editorStatus.textContent = err.message || "Could not save. Please try again.";
        });
    });

    var panel = el("div", "backlog-editor-panel");
    panel.appendChild(el("h3", null, isEdit ? "Edit backlog item" : "Add backlog item"));
    panel.appendChild(form);

    editorOverlay = el("div", "backlog-editor-overlay");
    editorOverlay.appendChild(panel);
    editorOverlay.addEventListener("click", function (event) {
      if (event.target === editorOverlay) closeBacklogEditor();
    });
    document.body.appendChild(editorOverlay);
    titleInput.focus();
  }

  // Tried once per page load, right after sign-in. A failure here (network,
  // an expired token, GitHub rate limiting) falls back to the same read-only
  // table the page has always shown, built from data/project-docs.json —
  // editing is simply unavailable until the next successful load.
  function refreshEditableBacklog(fallbackItems) {
    var container = document.getElementById("backlog-table-section");
    var session = readSession();
    if (!session || typeof window.jsyaml === "undefined") {
      renderBacklogTable(container, fallbackItems, { editable: false });
      return;
    }
    getContentFile(session.token)
      .then(function (file) {
        var items = parseBacklogFromYamlText(file.text);
        renderBacklogTable(container, items, { editable: true });
      })
      .catch(function (err) {
        console.error(err);
        renderBacklogTable(container, fallbackItems, {
          editable: false,
          note: "Editing is unavailable right now (" + err.message + "). Showing the last published backlog instead.",
        });
      });
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
        knownEpicTitles = [];
        (data.projects || []).forEach(function (project) {
          var section = el("section", "backlog-project");
          // Only label the project when there is more than one, so a single
          // set does not carry a redundant heading.
          if ((data.projects || []).length > 1) {
            section.appendChild(el("h2", "backlog-project-name", project.name));
          }
          project.epics.forEach(function (e) {
            section.appendChild(renderEpic(e));
            knownEpicTitles.push(e.title);
          });
          root.appendChild(section);
        });

        refreshEditableBacklog(data.backlog);
        appendix(document.getElementById("backlog-appendix"), data);
        applyFilter();
      })
      .catch(function (error) {
        console.error(error);
        if (status) status.textContent = "The backlog could not be loaded.";
      });
  }
})();
