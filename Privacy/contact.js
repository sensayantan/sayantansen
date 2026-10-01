/* Contact form on Privacy/index.html.
 *
 * Posts to the sayantansen-contact Worker (Privacy/worker/), which checks the
 * Cloudflare Turnstile token and emails the message to the owner. Until both
 * values below are set, the form stays hidden and a "being set up" note shows
 * instead, so a half-finished setup never offers a form that cannot send.
 */
(function () {
  "use strict";

  // The Worker's endpoint, and the Turnstile widget's site key. The site key
  // is public by design: it identifies the widget, while the secret that
  // verifies a token lives only in the Worker's dashboard settings.
  var CONTACT_ENDPOINT = "";
  var TURNSTILE_SITE_KEY = "";

  var form = document.getElementById("contact-form");
  var unavailable = document.getElementById("contact-unavailable");
  var status = document.getElementById("contact-status");
  var submit = document.getElementById("contact-submit");
  var holder = document.getElementById("contact-turnstile");
  if (!form || !unavailable || !status || !submit || !holder) return;

  if (!CONTACT_ENDPOINT || !TURNSTILE_SITE_KEY) {
    unavailable.hidden = false;
    return;
  }
  form.hidden = false;

  var widgetId = null;

  window.onContactTurnstileLoad = function () {
    widgetId = window.turnstile.render(holder, {
      sitekey: TURNSTILE_SITE_KEY,
      action: "contact",
    });
  };
  var api = document.createElement("script");
  api.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onContactTurnstileLoad";
  api.async = true;
  api.defer = true;
  document.head.appendChild(api);

  function say(text, kind) {
    status.textContent = text;
    status.className = "contact-status" + (kind ? " is-" + kind : "");
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var name = form.elements.name.value.trim();
    var email = form.elements.email.value.trim();
    var message = form.elements.message.value.trim();
    var token = window.turnstile && widgetId !== null ? window.turnstile.getResponse(widgetId) : "";

    if (!name) return say("Please add your name.", "error");
    if (message.length < 10) return say("Please write a little more.", "error");
    if (!token) return say("Please complete the human check above the button.", "error");

    submit.disabled = true;
    say("Sending…");
    fetch(CONTACT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name, email: email, message: message, turnstileToken: token }),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) throw new Error(data.error || "The message couldn't be sent.");
        });
      })
      .then(function () {
        form.reset();
        say("Thank you — your message is on its way." + (email ? " I'll reply to " + email + "." : ""), "ok");
      })
      .catch(function (error) {
        say(error.message, "error");
      })
      .then(function () {
        submit.disabled = false;
        // A Turnstile token is single-use; get a fresh one for any next send.
        if (window.turnstile && widgetId !== null) window.turnstile.reset(widgetId);
      });
  });
})();
