// Comments on blog posts, via giscus.
//
// giscus stores each post's comments as a GitHub Discussion in this
// repository. That means no server, no database and no cost: moderation is
// the repo's Discussions tab, and nothing about a reader is tracked beyond
// what GitHub already knows. The trade-off is that commenting requires a
// GitHub account, which is a real barrier for readers who are not
// developers.
//
// CATEGORY_ID is the one value that cannot be looked up ahead of time — it
// only exists once Discussions is enabled on the repo. Until it is filled
// in, the comments section stays hidden rather than rendering an empty box
// on every post. See the "Blog comments" section of the root README.
const GISCUS = {
  repo: "sensayantan/sayantansen",
  // The repository's GraphQL node id, from the GitHub API.
  repoId: "R_kgDOUJ9k1Q",
  // Announcements is deliberate: only maintainers can open a discussion
  // there, so every comment arrives as a reply to a thread giscus created
  // for that post, rather than as a new top-level discussion anyone can
  // start.
  category: "Announcements",
  categoryId: "",
};

function mountComments() {
  const mount = document.getElementById("comments");
  if (!mount) return;

  if (!GISCUS.categoryId) {
    mount.hidden = true;
    return;
  }

  const script = document.createElement("script");
  script.src = "https://giscus.app/client.js";
  script.async = true;
  script.crossOrigin = "anonymous";

  Object.entries({
    repo: GISCUS.repo,
    repoId: GISCUS.repoId,
    category: GISCUS.category,
    categoryId: GISCUS.categoryId,
    // One thread per post URL. The alternative, matching on title, breaks
    // every existing thread the first time a post is retitled.
    mapping: "pathname",
    strict: "1",
    reactionsEnabled: "1",
    emitMetadata: "0",
    inputPosition: "top",
    theme: "light",
    lang: "en",
    loading: "lazy",
  }).forEach(([key, value]) => {
    // data-repo-id rather than data-repoId — giscus reads kebab-case.
    const attr = key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
    script.setAttribute(`data-${attr}`, value);
  });

  mount.appendChild(script);
}

mountComments();
