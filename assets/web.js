// W website — what only the web needs on top of the docs' site.js: remembering
// the reader's language, the screenshot lightbox, and filling the download card
// with the image that is published right now.
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

  // Screenshots: the links open the full image without script; with it they open
  // in the lightbox, paged by arrows, ←/→ and a swipe. The <dialog> brings the
  // tinted backdrop, Esc and the focus trap itself.
  const box = document.querySelector(".lightbox");
  if (box) {
    const shots = [...document.querySelectorAll(".shots .grid a")];
    const img = box.querySelector("img"), cap = box.querySelector("figcaption");
    let i = 0, x0 = null;
    const show = (n) => {
      i = (n + shots.length) % shots.length;
      const s = shots[i].querySelector("img");
      img.src = shots[i].href; img.alt = s.alt; cap.textContent = s.alt;
    };
    shots.forEach((a, n) => a.addEventListener("click", (ev) => { ev.preventDefault(); show(n); box.showModal(); }));
    box.querySelector(".prev").onclick = () => show(i - 1);
    box.querySelector(".next").onclick = () => show(i + 1);
    box.querySelector(".close").onclick = () => box.close();
    box.addEventListener("click", (ev) => { if (ev.target === box) box.close(); });
    box.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") show(i - 1); else if (ev.key === "ArrowRight") show(i + 1);
    });
    img.addEventListener("pointerdown", (ev) => { x0 = ev.clientX; });
    img.addEventListener("pointerup", (ev) => {
      const dx = x0 === null ? 0 : ev.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 40) show(dx < 0 ? i + 1 : i - 1);
    });
    img.addEventListener("dragstart", (ev) => ev.preventDefault());
  }

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
