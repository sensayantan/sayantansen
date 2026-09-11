function renderPhotoPanel(photos) {
  if (!photos || photos.length === 0) return "";
  return photos
    .map((p) => {
      const badge = p.ai_generated
        ? '<span class="photo-badge">AI Generated</span>'
        : "";
      const caption = p.caption
        ? `<p class="photo-caption">${p.caption}</p>`
        : "";
      return `
        <figure class="photo-panel-item">
          <img src="${p.image}" alt="${p.caption || ""}" loading="lazy">
          ${badge}
          ${caption}
        </figure>`;
    })
    .join("");
}

async function loadAbout() {
  try {
    const response = await fetch("data/about.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load about.json (${response.status})`);
    const data = await response.json();

    document.getElementById("about-intro").innerHTML = data.about_intro_html || "";
    document.getElementById("profile-photos").innerHTML = renderPhotoPanel(data.profile_photos);

    document.getElementById("professional-journey").innerHTML =
      data.professional_journey_html || "";

    document.getElementById("personal-journey").innerHTML =
      data.personal_journey_html ||
      '<p class="placeholder">This section is still being written.</p>';

    document.getElementById("family-intro").innerHTML =
      data.family_intro_html || '<p class="placeholder">This section is still being written.</p>';
    document.getElementById("family-photos").innerHTML = renderPhotoPanel(data.family_photos);
  } catch (err) {
    console.error(err);
  }
}

loadAbout();
