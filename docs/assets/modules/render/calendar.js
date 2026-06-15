/* Beautiful F1 — Dashboard : onglet Calendrier + drill-down circuit.
 *
 * Le calendrier (léger, issu de dashboard_2026.json) s'affiche immédiatement.
 * Les données lourdes du circuit (circuits_2026.json ~152 Ko + gp_history.json)
 * sont chargées à la demande au premier affichage de l'onglet → allège le load initial.
 */

import { t } from "../i18n.js";
import { formatDateShort, fetchJson } from "../utils.js";
import { GP_TO_CIRCUIT } from "../constants.js";
import { renderCircuitDetail } from "./circuit.js";
import { wireCircuitHistory } from "./history.js";

// Auto-scroll de la liste calendrier sur le prochain GP (appelé aussi à l'activation de l'onglet).
export function scrollCalendarToNext() {
  const list = document.getElementById("dash-calendar");
  const next = list && list.querySelector(".dash-cal-next");
  if (next) {
    const offset = next.offsetTop - list.offsetTop;
    list.scrollTop = Math.max(0, offset - 60);
  }
}

function renderCalendarList(calContainer, cal, circuits, teamColor) {
  calContainer.innerHTML = cal
    .map((c) => {
      const statusIcon = c.status === "played" ? "✓" : c.status === "next" ? "▶" : "·";
      const winnerHtml = c.winner
        ? `<span class="dash-cal-winner" style="color:${teamColor(c.winner.team)}">${c.winner.shortName}</span>`
        : c.status === "next"
          ? `<span class="dash-cal-next-tag">${t("cal.nextTag")}</span>`
          : "";
      const sprintBadge = c.isSprint
        ? `<span class="dash-cal-sprint" title="${t("cal.sprintWeekend")}">S</span>`
        : "";
      const hasInfo = !!circuits[c.name];
      return `
        <li class="dash-cal-item dash-cal-${c.status} ${hasInfo ? "dash-cal-clickable" : ""}" data-gp="${c.name}">
          <span class="dash-cal-round">${c.round}</span>
          <span class="dash-cal-status">${statusIcon}</span>
          <span class="dash-cal-name">${c.shortName}${sprintBadge}</span>
          <span class="dash-cal-date">${formatDateShort(c.date)}</span>
          ${winnerHtml}
        </li>
      `;
    })
    .join("");
}

export function initCalendar(dashRes, teamColor) {
  const calContainer = document.getElementById("dash-calendar");
  const calProgress = document.getElementById("dash-calendar-progress");
  if (!calContainer || !dashRes.calendar) return;

  const cal = dashRes.calendar;
  const played = cal.filter((c) => c.status === "played").length;
  if (calProgress) calProgress.textContent = `${played} / ${cal.length} GP`;

  // 1) Rendu immédiat de la liste (sans capacité de drill-down, données lourdes pas encore chargées)
  renderCalendarList(calContainer, cal, {}, teamColor);

  // 2) Enrichissement paresseux : au premier affichage de l'onglet, on charge les
  //    données circuit + historique, puis on rend les lignes cliquables.
  let enhanced = false;
  const enhance = async () => {
    if (enhanced) return;
    enhanced = true;
    const [circuitsRes, historyRes] = await Promise.all([
      fetchJson("data/circuits_2026.json"),
      fetchJson("data/gp_history.json"),
    ]);
    const circuits = (circuitsRes && circuitsRes.circuits) || {};
    renderCalendarList(calContainer, cal, circuits, teamColor);
    wireCircuitDrilldown(calContainer, cal, circuits, historyRes, teamColor);
  };

  const calTab = document.querySelector('.dash-tab[data-tab="calendar"]');
  if (calTab) calTab.addEventListener("click", enhance);
  // Si l'onglet calendrier est déjà actif au chargement (restauration d'état), enrichir tout de suite.
  if (calTab && calTab.classList.contains("active")) enhance();
}

function wireCircuitDrilldown(calContainer, cal, circuits, historyRes, teamColor) {
  calContainer.addEventListener("click", (e) => {
    const li = e.target.closest("li.dash-cal-clickable");
    if (!li) return;
    // Ferme tout panneau déjà ouvert
    calContainer.querySelectorAll(".dash-circuit-detail").forEach((n) => n.remove());
    calContainer
      .querySelectorAll(".dash-cal-active")
      .forEach((n) => n.classList.remove("dash-cal-active"));
    const wasOpen = li.dataset.open === "1";
    calContainer.querySelectorAll("li.dash-cal-clickable").forEach((n) => (n.dataset.open = ""));
    if (wasOpen) return;
    li.dataset.open = "1";
    li.classList.add("dash-cal-active");
    const circuit = circuits[li.dataset.gp];
    const calItem = cal.find((x) => x.name === li.dataset.gp);
    if (!circuit) return;
    // Historique du circuit (clé = circuitId Ergast, mappé depuis le nom GP)
    const histKey = GP_TO_CIRCUIT[li.dataset.gp];
    const history = historyRes && histKey ? historyRes[histKey] : null;
    const detail = document.createElement("li");
    detail.className = "dash-circuit-detail";
    detail.innerHTML = renderCircuitDetail(circuit, calItem, teamColor, history);
    li.after(detail);
    if (history) wireCircuitHistory(detail, history, teamColor);
  });
}
