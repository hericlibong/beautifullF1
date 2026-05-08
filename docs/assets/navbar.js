/* Beautiful F1 — Top navigation bar
 *
 * Injecte une barre fixe en haut de la page avec :
 *   - le brand cliquable (retour dashboard)
 *   - un menu listant les viz disponibles depuis manifest.json
 *
 * À inclure sur le dashboard ET sur chaque page de viz.
 * Utilise data-manifest pour résoudre le chemin vers manifest.json
 * (relatif à la page courante). Par défaut : "assets/manifest.json".
 */

(async function () {
  const script = document.currentScript;
  const manifestPath = (script && script.dataset.manifest) || "assets/manifest.json";
  const baseHref = (script && script.dataset.base) || "./";

  let manifest;
  try {
    manifest = await fetch(manifestPath).then(r => r.json());
  } catch (e) {
    console.warn("[navbar] manifest introuvable :", e);
    return;
  }

  const nav = document.createElement("nav");
  nav.className = "dash-navbar";
  nav.setAttribute("aria-label", "Navigation principale");

  const items = (manifest.items || []).filter(it => it.available);
  const links = items.map(it => {
    const href = it.id === "dashboard" ? baseHref : (baseHref + it.route);
    return `<a href="${href}" class="dash-navbar-link" data-id="${it.id}">${it.title}</a>`;
  }).join("");

  nav.innerHTML = `
    <a href="${baseHref}" class="dash-navbar-brand">
      <span class="dash-navbar-mark">F1</span>
      <span>Beautiful F1 ${manifest.season || ""}</span>
    </a>
    <div class="dash-navbar-links">${links}</div>
  `;

  document.body.insertBefore(nav, document.body.firstChild);

  // Marquer le lien actif (correspondance par segment de chemin)
  const path = window.location.pathname.replace(/\/+$/, "/");
  nav.querySelectorAll(".dash-navbar-link").forEach(a => {
    const href = a.getAttribute("href");
    const isHome = a.dataset.id === "dashboard";
    const matches = isHome
      ? path.endsWith("/") && !path.includes("/race_chart_builder") && !path.includes("/season_summary_heatmap")
      : path.includes(href.replace(/^\.\//, "").replace(/\/$/, ""));
    if (matches) a.classList.add("active");
  });
})();
