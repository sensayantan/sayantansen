// Single Worker entry point. Cloudflare's current deployment model (a
// git-connected Worker with a static "assets" directory) doesn't do
// Pages' old file-based routing under functions/ — instead one script
// handles every request and decides what to do with it.
//
// Only /api/auth and /api/callback need real logic; everything else
// (just public/index.html here) is handed off to the static assets
// binding configured in wrangler.jsonc.
import { handleAuth } from "./auth.js";
import { handleCallback } from "./callback.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/auth") {
      return handleAuth(request, env);
    }
    if (url.pathname === "/api/callback") {
      return handleCallback(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
