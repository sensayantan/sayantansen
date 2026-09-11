// Step 1 of the login flow: redirect the admin's popup to GitHub's own
// authorize page. GitHub then redirects back to callback.js with a
// one-time code.
//
// The `state` value is GitHub's standard CSRF defense for OAuth: we
// generate a random value here, hand it to GitHub, and store our own
// copy in a short-lived cookie. callback.js checks the two match before
// trusting the response — without this, another site could trick a
// logged-in browser into completing a login it didn't ask for.
export async function onRequest(context) {
  const { request, env } = context;
  const clientId = env.GITHUB_CLIENT_ID;

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
