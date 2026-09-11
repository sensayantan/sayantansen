// Step 2: GitHub redirects here with a one-time `code` after the user
// approves the login. This runs inside the popup Decap opened, so the
// only way to hand the result back to the main /admin window is
// window.postMessage — there's no shared server-side session between
// this popup and that window.
//
// Decap's handshake (undocumented but stable — verified against a
// reference implementation): the popup announces itself with
// "authorizing:github", waits for the opener to reply, then sends
// "authorization:github:success:<json>" (or ":error:<json>").

function resultPage(status, payload) {
  const html = `<!DOCTYPE html><html><body><script>
    (function() {
      function receiveMessage(message) {
        window.opener.postMessage(
          'authorization:github:${status}:${JSON.stringify(payload)}',
          message.origin
        );
        window.removeEventListener("message", receiveMessage, false);
      }
      window.addEventListener("message", receiveMessage, false);
      window.opener.postMessage("authorizing:github", "*");
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

  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const returnedState = url.searchParams.get("state");
  const expectedState = getCookie(request, "oauth_state");

  if (!returnedState || !expectedState || returnedState !== expectedState) {
    return resultPage("error", { message: "OAuth state mismatch — please try logging in again." });
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
      return resultPage("error", result);
    }

    return resultPage("success", { token: result.access_token, provider: "github" });
  } catch (error) {
    return resultPage("error", { message: error.message });
  }
}
