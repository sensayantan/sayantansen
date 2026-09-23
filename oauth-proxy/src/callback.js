// Step 2: GitHub redirects here with a one-time `code` after the user
// approves the login. This runs inside the popup Decap opened, so the
// only way to hand the result back to the main /admin window is
// window.postMessage — there's no shared server-side session between
// this popup and that window.
//
// Decap's handshake: the popup announces itself with "authorizing:github",
// the opener replies, and the popup then sends
// "authorization:github:success:<json>" (or ":error:<json>").
//
// Waiting for that reply is what used to hang the login. The browser refused
// the opener's reply with
//
//   Unable to post message to <worker origin>. Recipient has origin
//   <site origin>.
//
// and since the old code only sent the token from inside the reply handler,
// the popup sat blank forever with a perfectly good token in hand.
//
// So the reply is now an optimisation, not a requirement. Decap registers its
// token listener *before* sending that reply, so a token that arrives without
// it is still received. A short timer sends one either way, and `sent` keeps
// the two paths from firing twice.
//
// The token is posted to an explicit site origin rather than "*", so only the
// admin page can read it — a "*" here would hand a GitHub token to whatever
// happened to open the popup.

const DEFAULT_SITE_ORIGIN = "https://sensayantan.github.io";

// The payload is interpolated into a <script> block, so it has to be safe as
// both JS and HTML. JSON.stringify handles quoting; escaping "<" additionally
// stops a "</script>" inside any value from closing the block early.
function embed(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

function resultPage(status, payload, siteOrigin) {
  const message = `authorization:github:${status}:${JSON.stringify(payload)}`;
  const html = `<!DOCTYPE html><html><body><script>
    (function () {
      var message = ${embed(message)};
      var siteOrigin = ${embed(siteOrigin)};
      var sent = false;

      function send(targetOrigin) {
        if (sent || !window.opener) return;
        sent = true;
        window.removeEventListener("message", onReply, false);
        window.opener.postMessage(message, targetOrigin);
      }

      function onReply(event) {
        if (event.origin === siteOrigin) send(event.origin);
      }

      window.addEventListener("message", onReply, false);
      window.opener.postMessage("authorizing:github", siteOrigin);
      setTimeout(function () { send(siteOrigin); }, 500);
    })();
  </script></body></html>`;
  return new Response(html, {
    status: status === "success" ? 200 : 401,
    headers: { "content-type": "text/html;charset=UTF-8" },
  });
}

function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? match[1] : null;
}

export async function handleCallback(request, env) {
  const clientId = env.GITHUB_CLIENT_ID;
  const clientSecret = env.GITHUB_CLIENT_SECRET;
  const siteOrigin = env.SITE_ORIGIN || DEFAULT_SITE_ORIGIN;

  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const returnedState = url.searchParams.get("state");
  const expectedState = getCookie(request, "oauth_state");

  if (!returnedState || !expectedState || returnedState !== expectedState) {
    return resultPage("error", { message: "OAuth state mismatch — please try logging in again." }, siteOrigin);
  }

  try {
    const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, code }),
    });
    const result = await tokenResponse.json();

    if (result.error || !result.access_token) {
      return resultPage("error", result, siteOrigin);
    }

    return resultPage("success", { token: result.access_token, provider: "github" }, siteOrigin);
  } catch (error) {
    return resultPage("error", { message: error.message }, siteOrigin);
  }
}
