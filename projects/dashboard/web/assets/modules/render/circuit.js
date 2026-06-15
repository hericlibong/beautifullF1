/* Beautiful F1 — Dashboard : drill-down circuit (tracé + specs + vainqueurs). */

import { t } from "../i18n.js";
import { renderHistoryScatter, renderHistoryBars } from "./history.js";

export function renderCircuitDetail(circuit, calItem, teamColor, history) {
  // Tracé SVG
  let trackSvg = "";
  if (circuit.trackPath && circuit.trackPath.length > 1) {
    // Les coords sont normalisées 0..1000 ; on inverse Y (SVG a l'origine en haut)
    const pts = circuit.trackPath.map(([x, y]) => `${x},${1000 - y}`).join(" ");
    trackSvg = `
      <svg viewBox="-40 -40 1080 1080" class="dash-circuit-track" aria-label="${t("circuit.trackAria")}">
        <polyline points="${pts}" fill="none" stroke="#e8eaf0" stroke-width="14"
                  stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
      </svg>
    `;
  } else {
    trackSvg = `<div class="dash-circuit-notrack">${t("circuit.trackUnavailable")}</div>`;
  }

  // Caractéristiques
  const specs = [];
  if (circuit.lengthKm) specs.push([t("circuit.length"), `${circuit.lengthKm.toFixed(3)} km`]);
  if (circuit.laps) specs.push([t("circuit.laps"), circuit.laps]);
  if (circuit.corners) specs.push([t("circuit.corners"), circuit.corners]);
  if (circuit.isSprint) specs.push([t("circuit.format"), t("circuit.sprint")]);

  const specsHtml = specs
    .map(
      ([k, v]) =>
        `<div class="dash-circuit-spec"><span class="dash-circuit-spec-k">${k}</span><span class="dash-circuit-spec-v">${v}</span></div>`,
    )
    .join("");

  // Record du tour (saison source du tracé)
  const recordHtml = circuit.lapRecord
    ? `<div class="dash-circuit-record">${t("circuit.fastestLap", { year: circuit.lapRecord.year, driver: circuit.lapRecord.driver, time: circuit.lapRecord.time })}</div>`
    : "";

  // Vainqueur de la saison en cours (si GP joué) — vient du calendrier dashboard
  const winner2026 =
    calItem && calItem.winner
      ? `<div class="dash-circuit-winner-2026">${t("circuit.winner", { season: 2026, color: teamColor(calItem.winner.team), name: calItem.winner.shortName, team: calItem.winner.team })}</div>`
      : "";

  // Vainqueurs historiques
  const pastHtml = (circuit.pastWinners || [])
    .map(
      (w) => `
    <div class="dash-circuit-past-row">
      <span class="dash-circuit-past-year">${w.year}</span>
      <span class="dash-circuit-past-driver" style="color:${teamColor(w.team)}">${w.driver}</span>
      <span class="dash-circuit-past-team">${w.team}</span>
    </div>
  `,
    )
    .join("");

  // Zone "Histoire" : scatter chronologie (rendu initial en mode "driver")
  const historyHtml = history
    ? `
    <div class="dash-history" data-circuit="${history.circuitId}">
      <div class="dash-history-head">
        <div>
          <div class="dash-history-title">${t("history.title")}</div>
          <div class="dash-history-sub">${t("history.subtitle", { from: history.yearFrom, to: history.yearTo, n: history.editions.length })}</div>
        </div>
        <label class="dash-history-ymode">
          <span>${t("history.yLabel")}</span>
          <select class="dash-history-yselect dash-duel-select">
            <option value="driver">${t("history.yDriver")}</option>
            <option value="team">${t("history.yTeam")}</option>
          </select>
        </label>
      </div>
      <div class="dash-history-plot">
        ${renderHistoryScatter(history, "driver", teamColor)}
        <div class="dash-history-tip" hidden></div>
      </div>
      ${renderHistoryBars(history, teamColor)}
    </div>
  `
    : "";

  return `
    <div class="dash-circuit-detail-inner">
      <div class="dash-circuit-left">
        ${trackSvg}
      </div>
      <div class="dash-circuit-right">
        <div class="dash-circuit-specs">${specsHtml}</div>
        ${recordHtml}
        ${winner2026}
        ${
          pastHtml
            ? `
          <div class="dash-circuit-past">
            <div class="dash-circuit-past-title">${t("circuit.recentWinners")}</div>
            ${pastHtml}
          </div>`
            : ""
        }
      </div>
    </div>
    ${historyHtml}
  `;
}
