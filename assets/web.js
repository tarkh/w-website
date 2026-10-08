// W website — what only the web needs on top of the docs' site.js: remembering
// the reader's language, and filling the download card with the image that is
// published right now.
//
// The image is rebuilt every night under a dated name, so a link baked into the
// page at build time would go stale by morning. The card asks GitHub instead —
// the `edge` release's one .iso asset, its size and its SHA-256 — and until (or
// unless) that answer comes, its button points at the release page, which is
// always right.
(function () {
  "use strict";

  document.addEventListener("click", (ev) => {
    const a = ev.target.closest && ev.target.closest("a[hreflang]");
    if (a) try { localStorage.setItem("w-lang", a.hreflang); } catch (e) { /* private mode */ }
  });

  const card = document.querySelector(".iso");
  if (!card) return;
  const set = (k, v) => { const el = card.querySelector(`[data-k="${k}"]`); if (el) el.textContent = v; };
  fetch(`https://api.github.com/repos/${card.dataset.repo}/releases/tags/${card.dataset.tag}`,
        { headers: { Accept: "application/vnd.github+json" } })
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((rel) => {
      const iso = (rel.assets || []).find((a) => /\.iso$/.test(a.name));
      if (!iso) return;
      const m = iso.name.match(/^w-(.+)-(\d{4})\.(\d{2})\.(\d{2})-x86_64\.iso$/);
      const sha = (iso.digest || "").replace(/^sha256:/, "") ||
        ((rel.body || "").match(/\b[0-9a-f]{64}\b/) || [""])[0];
      set("name", iso.name);
      set("release", m ? m[1] : "");
      set("built", m ? `${m[2]}-${m[3]}-${m[4]}` : iso.updated_at.slice(0, 10));
      set("size", `${Math.round(iso.size / 1e6).toLocaleString(document.documentElement.lang)} MB`);
      set("sha", sha ? `SHA-256  ${sha}` : "");
      card.querySelector(".iso-get").href = iso.browser_download_url;
      card.classList.add("ready");
    })
    .catch(() => {});
})();
