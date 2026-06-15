/* Beautiful F1 — Dashboard 2026 (orchestrateur).
 *
 * Charge tous les JSON (Promise.all), peuple l'en-tête + les KPI, puis délègue
 * chaque widget à son module de rendu (assets/modules/render/*).
 * Module ES6 : aucun bundler, chargé via <script type="module"> dans index.html.
 */

import { setI18n, t, LANG, applyStaticI18n, setupLangSwitcher } from "./modules/i18n.js";
import { shortName, formatDate, formatCountdown, fetchJson } from "./modules/utils.js";
import { initStandings } from "./modules/render/standings.js";
import { initDuel } from "./modules/render/duel.js";
import { initTeammates } from "./modules/render/teammates.js";
import { initCalendar, scrollCalendarToNext } from "./modules/render/calendar.js";
import { initEmbed } from "./modules/render/embed.js";

(async function () {
  // Chargement initial : uniquement le strict nécessaire à la première vue (onglet Pilotes).
  // Les données lourdes (circuits, historique, qualifs) sont chargées à la demande par
  // leurs modules respectifs au premier affichage de l'onglet concerné.
  const [dashRes, teamsRes, manifestRes, i18nRes] = await Promise.all([
    fetchJson("data/dashboard_2026.json", { required: true }),
    fetchJson("assets/teams.json", { required: true }),
    fetchJson("assets/manifest.json", { required: true }),
    fetchJson("assets/i18n.json", { fallback: {} }),
  ]);

  setI18n(i18nRes);
  document.documentElement.lang = LANG;
  applyStaticI18n();
  setupLangSwitcher();

  const teams = teamsRes.teams || {};
  const teamColor = (name) => (teams[name] && teams[name].color) || teamsRes.fallbackColor;

  // ---------- Header ----------
  const lastGpDate = formatDate(dashRes.lastGp.date);
  document.getElementById("dash-subtitle").textContent = t("header.lastRace", {
    gp: dashRes.lastGp.shortName,
    date: lastGpDate,
    n: dashRes.kpis.raceCount,
    total: dashRes.kpis.totalRaces,
  });

  // ---------- KPI ----------
  const kpiContainer = document.getElementById("dash-kpis");
  const k = dashRes.kpis;
  const kpis = [
    {
      label: t("kpi.leader"),
      value: shortName(k.leader.name),
      sub: t("kpi.points", { n: k.leader.points, team: k.leader.team }),
      color: teamColor(k.leader.team),
    },
    {
      label: t("kpi.gap"),
      value: `+${k.leaderGap}`,
      sub: t("kpi.gapSub", { name: shortName(k.second.name), pts: k.second.points }),
    },
    {
      label: t("kpi.lastWinner"),
      value: shortName(k.lastWinner.name),
      sub: `${k.lastWinner.gp} • ${k.lastWinner.team}`,
      color: teamColor(k.lastWinner.team),
    },
    {
      label: t("kpi.nextRace"),
      countdown: dashRes.nextGp ? dashRes.nextGp.date : null,
      gpName: dashRes.nextGp ? dashRes.nextGp.shortName : "—",
      sub: dashRes.nextGp
        ? `${dashRes.nextGp.shortName} • ${formatDate(dashRes.nextGp.date)}${dashRes.nextGp.isSprint ? " • Sprint" : ""}`
        : t("kpi.seasonEnded"),
    },
  ];

  kpiContainer.innerHTML = kpis
    .map(
      (kpi, i) => `
    <div class="dash-kpi ${kpi.countdown ? "dash-kpi--countdown" : ""}" data-kpi-idx="${i}">
      <div class="dash-kpi-label">${kpi.label}</div>
      <div class="dash-kpi-value" ${kpi.color ? `style="color:${kpi.color}"` : ""}>${kpi.value || ""}</div>
      <div class="dash-kpi-sub">${kpi.sub}</div>
    </div>
  `,
    )
    .join("");

  // Initialise + tick le countdown
  if (dashRes.nextGp && dashRes.nextGp.date) {
    const targetDate = dashRes.nextGp.date + "T14:00:00"; // ~ heure typique de course (locale)
    const tile = kpiContainer.querySelector(".dash-kpi--countdown .dash-kpi-value");
    const tick = () => {
      if (!tile) return;
      const diff = new Date(targetDate).getTime() - Date.now();
      tile.textContent = formatCountdown(diff);
    };
    tick();
    setInterval(tick, 60_000);
  }

  // ---------- Widgets (délégués aux modules) ----------
  initStandings(dashRes, teamColor);
  initDuel(dashRes, teamColor);
  initTeammates(dashRes, teamColor);
  initCalendar(dashRes, teamColor);
  initEmbed(manifestRes);

  // ---------- Onglets Pilotes / Constructeurs / Calendrier / Duel / Coéquipiers ----------
  document.querySelectorAll(".dash-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      document.querySelectorAll(".dash-tab").forEach((b) => {
        const isActive = b.dataset.tab === target;
        b.classList.toggle("active", isActive);
        b.setAttribute("aria-selected", isActive ? "true" : "false");
      });
      document.querySelectorAll(".dash-tab-pane").forEach((p) => {
        p.classList.toggle("active", p.id === `standings-pane-${target}`);
      });
      if (target === "calendar") {
        // L'auto-scroll ne fonctionne que quand le pane est visible
        requestAnimationFrame(scrollCalendarToNext);
      }
    });
  });

  // ---------- Restaurer l'état (onglet ou viz embed) après un changement de langue ----------
  const savedEmbed = sessionStorage.getItem("bf1-active-embed");
  const savedTab = sessionStorage.getItem("bf1-active-tab");
  if (savedEmbed) {
    sessionStorage.removeItem("bf1-active-embed");
    setTimeout(() => {
      const sc = document.querySelector(
        `.dash-shortcut[data-viz-id="${savedEmbed}"]:not(.is-disabled)`,
      );
      if (sc) sc.click();
    }, 0);
  } else if (savedTab) {
    sessionStorage.removeItem("bf1-active-tab");
    setTimeout(() => {
      const tabBtn = document.querySelector(`.dash-tab[data-tab="${savedTab}"]`);
      if (tabBtn) tabBtn.click();
    }, 0);
  }
})().catch((err) => {
  console.error("Erreur de chargement du dashboard :", err);
  const sub = document.getElementById("dash-subtitle");
  if (sub) sub.textContent = t("header.loadError");
});
