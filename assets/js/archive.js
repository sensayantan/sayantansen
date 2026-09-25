/* Daybreak archive calendar.
 *
 * Reads data/daybreak-index.json, which backend/patch_daybreak.py writes
 * from the files actually present in DAYBREAK/. The index drives which
 * days are selectable rather than a weekday rule: Daybreak skips Sundays,
 * but it has also missed ordinary weekdays, and offering those would link
 * to a file that does not exist.
 */
(function () {
  "use strict";

  var INDEX_URL = "data/daybreak-index.json";
  var MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  var root = document.getElementById("archive-calendar");
  var status = document.getElementById("archive-status");
  if (!root) return;

  /* In the pop-up the chrome is off. Carry that through to the edition a day
   * links to, otherwise the pop-up opens the archive bare and then hands back
   * a full edition complete with site header and footer. */
  var bare = document.documentElement.classList.contains("is-bare");

  /* "2026-09-10" -> a local Date at midnight.
   *
   * new Date("2026-09-10") parses as UTC midnight, which in any negative
   * offset (this site's author is on Pacific time) renders as the 9th.
   * Splitting the parts keeps the calendar on the date it says. */
  function parseDate(iso) {
    var p = iso.split("-");
    return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
  }

  function isoOf(year, month, day) {
    return year + "-" + String(month + 1).padStart(2, "0") + "-" + String(day).padStart(2, "0");
  }

  function fail(message) {
    if (status) status.textContent = message;
  }

  fetch(INDEX_URL, { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("Archive index unavailable (" + response.status + ")");
      return response.json();
    })
    .then(function (index) {
      var editions = Array.isArray(index.editions) ? index.editions : [];
      if (!editions.length) {
        fail("No editions have been archived yet.");
        return;
      }

      // date -> filename, so a day cell can link straight to its edition.
      var byDate = {};
      editions.forEach(function (e) {
        if (e && typeof e.date === "string" && typeof e.file === "string") byDate[e.date] = e.file;
      });

      var first = parseDate(index.first || editions[0].date);
      var last = parseDate(index.last || editions[editions.length - 1].date);
      // The calendar opens on the most recent edition's month and cannot be
      // paged outside the range that has editions.
      var view = new Date(last.getFullYear(), last.getMonth(), 1);
      var firstMonth = new Date(first.getFullYear(), first.getMonth(), 1);
      var lastMonth = new Date(last.getFullYear(), last.getMonth(), 1);

      function render() {
        root.textContent = "";

        var head = document.createElement("div");
        head.className = "archive-head";

        var prev = document.createElement("button");
        prev.type = "button";
        prev.className = "archive-nav";
        prev.setAttribute("aria-label", "Previous month");
        prev.textContent = "←";
        prev.disabled = view <= firstMonth;
        prev.addEventListener("click", function () {
          view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
          render();
        });

        var label = document.createElement("h2");
        label.className = "archive-month";
        label.textContent = MONTHS[view.getMonth()] + " " + view.getFullYear();

        var next = document.createElement("button");
        next.type = "button";
        next.className = "archive-nav";
        next.setAttribute("aria-label", "Next month");
        next.textContent = "→";
        next.disabled = view >= lastMonth;
        next.addEventListener("click", function () {
          view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
          render();
        });

        head.appendChild(prev);
        head.appendChild(label);
        head.appendChild(next);
        root.appendChild(head);

        var grid = document.createElement("div");
        grid.className = "archive-grid";

        DAYS.forEach(function (name) {
          var cell = document.createElement("span");
          cell.className = "archive-dayname";
          cell.textContent = name;
          grid.appendChild(cell);
        });

        var year = view.getFullYear();
        var month = view.getMonth();
        var lead = new Date(year, month, 1).getDay();
        var length = new Date(year, month + 1, 0).getDate();

        for (var b = 0; b < lead; b++) {
          var blank = document.createElement("span");
          blank.className = "archive-day is-blank";
          grid.appendChild(blank);
        }

        for (var d = 1; d <= length; d++) {
          var iso = isoOf(year, month, d);
          var file = byDate[iso];
          var cell;
          if (file) {
            cell = document.createElement("a");
            cell.href = "DAYBREAK/" + file + (bare ? "?chrome=off" : "");
            cell.className = "archive-day is-available";
            cell.setAttribute("aria-label", "Daybreak for " + iso);
          } else {
            cell = document.createElement("span");
            cell.className = "archive-day is-empty";
            cell.setAttribute("aria-disabled", "true");
          }
          cell.textContent = String(d);
          grid.appendChild(cell);
        }

        root.appendChild(grid);

        var count = document.createElement("p");
        count.className = "archive-count";
        count.textContent = editions.length + " edition" + (editions.length === 1 ? "" : "s") +
          " from " + index.first + " to " + index.last + ".";
        root.appendChild(count);
      }

      render();
    })
    .catch(function (error) {
      console.error(error);
      fail("The archive index could not be loaded.");
    });
})();
