// Step 1 of the login flow: redirect the admin's popup to GitHub's own
// authorize page. GitHub then redirects back to callback.js with a
// one-time code.
//
// The `state` value is GitHub's standard CSRF defense for OAuth: we
// generate a random value here, hand it to GitHub, and store our own
// copy in a short-lived cookie. callback.js checks the two match before
// trusting the response — without this, another site could trick a
// logged-in browser into completing a login it didn't ask for.
export function handleAuth(request, env) {
  const clientId = env.GITHUB_CLIENT_ID;

  // Without this guard a missing client ID still redirects to GitHub, with
  // client_id=undefined in the query string, and GitHub answers with its own
  // 404. That 404 looks like the admin page is missing rather than like a
  // configuration problem, which is exactly the wrong place to go looking.
  if (!clientId) {
    return new Response(
      "GITHUB_CLIENT_ID is not set on this Worker.\n\n" +
        "It should come from the vars block in oauth-proxy/wrangler.jsonc. " +
        "If it is missing there, add it and redeploy — a value set only in " +
        "the Cloudflare dashboard is wiped by the next wrangler deploy.",
      { status: 500, headers: { "Content-Type": "text/plain" } }
    );
  }

  const url = new URL(request.url);
  const state = crypto.randomUUID();

  const authorizeUrl = new URL("https://github.com/login/oauth/authorize");
  authorizeUrl.searchParams.set("client_id", clientId);
  authorizeUrl.searchParams.set("redirect_uri", `${url.origin}/api/callback`);
  authorizeUrl.searchParams.set("scope", "repo,user");
  authorizeUrl.searchParams.set("state", state);

  return new Response(null, {
    status: 302,
    headers: {
      Location: authorizeUrl.href,
      // HttpOnly: never readable by page JS (nothing to steal via XSS).
      // SameSite=Lax: still sent on this top-level GitHub->our-site redirect.
      // Max-Age is short — this cookie only needs to survive one login round trip.
      "Set-Cookie": `oauth_state=${state}; HttpOnly; Secure; SameSite=Lax; Max-Age=600; Path=/`,
    },
  });
}
