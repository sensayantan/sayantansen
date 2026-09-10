function renderTile(post) {
  const image = post.image
    ? `<img class="blog-tile-image" src="${post.image}" alt="" loading="lazy">`
    : "";
  return `
    <a class="blog-tile" href="${post.url}">
      ${image}
      <div class="blog-tile-body">
        <p class="blog-tile-date">${post.date_display}</p>
        <h3 class="blog-tile-title">${post.title}</h3>
        <p class="blog-tile-excerpt">${post.excerpt}</p>
      </div>
    </a>`;
}

async function loadBlogs() {
  const container = document.getElementById("blog-grid");
  const emptyState = document.getElementById("blog-empty-state");
  try {
    const response = await fetch("data/blogs.json");
    if (!response.ok) throw new Error(`Failed to load blogs.json (${response.status})`);
    const data = await response.json();

    if (!data.posts || data.posts.length === 0) {
      emptyState.hidden = false;
      return;
    }

    container.innerHTML = data.posts.map(renderTile).join("");
  } catch (err) {
    emptyState.hidden = false;
    emptyState.textContent = "Couldn't load posts. Try refreshing the page.";
    console.error(err);
  }
}

loadBlogs();
