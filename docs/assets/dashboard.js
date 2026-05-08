/* Beautiful F1 — Dashboard 2026
 * Charge data/dashboard_2026.json + assets/teams.json et peuple la page.
 */

(async function () {
  const [dashRes, teamsRes, manifestRes] = await Promise.all([
    fetch("data/dashboard_2026.json").then(r => r.json()),
    fetch("assets/teams.json").then(r => r.json()),
    fetch("assets/manifest.json").then(r => r.json()),
  ]);

  const teams = teamsRes.teams || {};
  const teamColor = name => (teams[name] && teams[name].color) || teamsRes.fallbackColor;

  // ---------- Header ----------
  const lastGpDate = formatDate(dashRes.lastGp.date);
  document.getElementById("dash-subtitle").textContent =
    `Dernier GP joué : ${dashRes.lastGp.shortName} (${lastGpDate}) • ${dashRes.kpis.raceCount} / ${dashRes.kpis.totalRaces} GP`;

  // ---------- KPI ----------
  const kpiContainer = document.getElementById("dash-kpis");
  const k = dashRes.kpis;
  const kpis = [
    {
      label: "Leader actuel",
      value: shortName(k.leader.name),
      sub: `${k.leader.points} pts • ${k.leader.team}`,
      color: teamColor(k.leader.team),
    },
    {
      label: "Écart leader / 2e",
      value: `+${k.leaderGap}`,
      sub: `vs ${shortName(k.second.name)} (${k.second.points} pts)`,
    },
    {
      label: "Dernier vainqueur",
      value: shortName(k.lastWinner.name),
      sub: `${k.lastWinner.gp} • ${k.lastWinner.team}`,
      color: teamColor(k.lastWinner.team),
    },
    {
      label: "Prochain GP",
      value: dashRes.nextGp.shortName,
      sub: `${formatDate(dashRes.nextGp.date)}${dashRes.nextGp.isSprint ? " • Sprint" : ""}`,
    },
  ];

  kpiContainer.innerHTML = kpis.map(kpi => `
    <div class="dash-kpi">
      <div class="dash-kpi-label">${kpi.label}</div>
      <div class="dash-kpi-value" ${kpi.color ? `style="color:${kpi.color}"` : ""}>${kpi.value}</div>
      <div class="dash-kpi-sub">${kpi.sub}</div>
    </div>
  `).join("");

  // ---------- Visualisations (depuis manifest) ----------
  const vizContainer = document.getElementById("dash-viz");
  if (vizContainer && manifestRes.items) {
    const vizItems = manifestRes.items.filter(it => it.category === "viz");
    vizContainer.innerHTML = vizItems.map(it => {
      const disabled = !it.available;
      const linkLabel = disabled ? "Bientôt" : "Ouvrir →";
      const tag = disabled ? "div" : "a";
      const hrefAttr = disabled ? "" : `href="${it.route}"`;
      const ariaAttr = disabled ? `aria-disabled="true" style="opacity:0.55;"` : "";
      return `
        <${tag} class="dash-card" ${hrefAttr} ${ariaAttr}>
          <div class="dash-card-header">
            <h3 class="dash-card-title">${it.title}</h3>
            <span class="dash-card-link">${linkLabel}</span>
          </div>
          <p class="dash-kpi-sub">${it.description}</p>
        </${tag}>
      `;
    }).join("");
  }
})().catch(err => {
  console.error("Erreur de chargement du dashboard :", err);
  const sub = document.getElementById("dash-subtitle");
  if (sub) sub.textContent = "Erreur de chargement des données.";
});

function shortName(full) {
  const parts = (full || "").trim().split(/\s+/);
  if (parts.length < 2) return full;
  return parts[0][0] + ". " + parts.slice(1).join(" ");
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}
