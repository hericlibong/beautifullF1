/* Beautiful F1 — Dashboard : classements pilotes/constructeurs + drill-down pilote. */

import { t } from "../i18n.js";
import { renderDriverDetail } from "./driver.js";

const fmtDelta = (n) => (n > 0 ? `+${n}` : n === 0 ? "0" : `${n}`);
const trophy = (rank) => (rank === 1 ? "🏆" : rank);

// Construit les deux tableaux de classement et câble le drill-down pilote.
export function initStandings(dashRes, teamColor) {
  initDriversTable(dashRes, teamColor);
  initConstructorsTable(dashRes, teamColor);
}

function initDriversTable(dashRes, teamColor) {
  const driversTable = document.getElementById("standings-drivers");
  if (!driversTable || !dashRes.standings || !dashRes.standings.drivers) return;

  const allDrivers = dashRes.standings.drivers;
  const TOP_N = 10;
  const renderDriverRows = (list) =>
    list
      .map(
        (d) => `
      <tr class="t-clickable" data-driver="${d.name}">
        <td class="t-rank ${d.rank === 1 ? "leader" : ""}">${trophy(d.rank)}</td>
        <td class="t-name">
          <span class="t-swatch" style="background:${teamColor(d.team)}"></span>
          ${d.shortName}
        </td>
        <td class="t-team">${d.team}</td>
        <td class="t-num"><strong>${d.points}</strong></td>
        <td class="t-num ${d.deltaLastGp > 0 ? "positive" : "muted"}">${fmtDelta(d.deltaLastGp)}</td>
        <td class="t-num t-gap muted">${d.leaderGap === 0 ? "—" : d.leaderGap}</td>
      </tr>
    `,
      )
      .join("");

  const renderTable = (expanded) => {
    const visible = expanded ? allDrivers : allDrivers.slice(0, TOP_N);
    driversTable.innerHTML = `
        <thead>
          <tr>
            <th class="t-rank">${t("col.rank")}</th>
            <th class="t-name">${t("col.driver")}</th>
            <th class="t-team">${t("col.team")}</th>
            <th class="t-num">${t("col.points")}</th>
            <th class="t-num">${t("col.delta")}</th>
            <th class="t-num t-gap">${t("col.gap")}</th>
          </tr>
        </thead>
        <tbody>${renderDriverRows(visible)}</tbody>
      `;
    // Le bouton "Voir les N" vit DANS le pane Pilotes, juste après le tableau
    const pane = driversTable.closest(".dash-tab-pane");
    let toggle = pane.querySelector(".dash-table-toggle");
    if (allDrivers.length > TOP_N) {
      if (!toggle) {
        toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "dash-table-toggle";
        pane.appendChild(toggle);
        toggle.addEventListener("click", () => renderTable(!toggle.dataset.expanded));
      }
      toggle.dataset.expanded = expanded ? "1" : "";
      toggle.textContent = expanded
        ? t("table.showTop", { n: TOP_N })
        : t("table.showAll", { n: allDrivers.length });
    }
  };
  renderTable(false);

  // Drill-down : clic sur une ligne → panneau détaillé sous la ligne
  driversTable.addEventListener("click", (e) => {
    const tr = e.target.closest("tr.t-clickable");
    if (!tr) return;
    // Ferme tout autre panneau ouvert
    driversTable.querySelectorAll("tr.t-detail").forEach((n) => n.remove());
    driversTable.querySelectorAll("tr.t-active").forEach((n) => n.classList.remove("t-active"));
    const wasOpen = tr.dataset.expanded === "1";
    // Reset all expanded markers
    driversTable.querySelectorAll("tr.t-clickable").forEach((n) => (n.dataset.expanded = ""));
    if (wasOpen) return;
    tr.dataset.expanded = "1";
    tr.classList.add("t-active");
    const driver = allDrivers.find((d) => d.name === tr.dataset.driver);
    if (!driver) return;
    const detail = document.createElement("tr");
    detail.className = "t-detail";
    detail.innerHTML = `<td colspan="6">${renderDriverDetail(driver, teamColor)}</td>`;
    tr.after(detail);
  });
}

function initConstructorsTable(dashRes, teamColor) {
  const teamsTable = document.getElementById("standings-constructors");
  if (!teamsTable || !dashRes.standings || !dashRes.standings.constructors) return;

  teamsTable.innerHTML = `
      <thead>
        <tr>
          <th class="t-rank">${t("col.rank")}</th>
          <th class="t-name">${t("col.team")}</th>
          <th class="t-num">${t("col.points")}</th>
          <th class="t-num">${t("col.delta")}</th>
          <th class="t-num t-gap">${t("col.gap")}</th>
        </tr>
      </thead>
      <tbody>
        ${dashRes.standings.constructors
          .map(
            (c) => `
          <tr>
            <td class="t-rank ${c.rank === 1 ? "leader" : ""}">${trophy(c.rank)}</td>
            <td class="t-name">
              <span class="t-swatch" style="background:${teamColor(c.team)}"></span>
              ${c.team}
            </td>
            <td class="t-num"><strong>${c.points}</strong></td>
            <td class="t-num ${c.deltaLastGp > 0 ? "positive" : "muted"}">${fmtDelta(c.deltaLastGp)}</td>
            <td class="t-num t-gap muted">${c.leaderGap === 0 ? "—" : c.leaderGap}</td>
          </tr>
        `,
          )
          .join("")}
      </tbody>
    `;
}
