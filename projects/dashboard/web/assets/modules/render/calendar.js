/* Beautiful F1 — Dashboard : onglet Calendrier + drill-down circuit. */

import { t } from "../i18n.js";
import { formatDateShort } from "../utils.js";
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

export function initCalendar(dashRes, circuitsRes, historyRes, teamColor) {
  const calContainer = document.getElementById("dash-calendar");
  const calProgress = document.getElementById("dash-calendar-progress");
  if (!calContainer || !dashRes.calendar) return;

  const cal = dashRes.calendar;
  const played = cal.filter((c) => c.status === "played").length;
  if (calProgress) calProgress.textContent = `${played} / ${cal.length} GP`;

  const circuits = (circuitsRes && circuitsRes.circuits) || {};
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

  // Drill-down circuit : clic sur une ligne → panneau détaillé déplié dessous
  calContainer.addEventListener("click", (e) => {
    const li = e.target.closest("li.dash-cal-clickable");
    if (!li) return;
    // Ferme tout panneau déjà ouvert
    calContainer.querySelectorAll(".dash-circuit-detail").forEach((n) => n.remove());
    calContainer.querySelectorAll(".dash-cal-active").forEach((n) => n.classList.remove("dash-cal-active"));
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
