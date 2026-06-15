/* Beautiful F1 — Dashboard : drill-down pilote (en-tête + sparkline + table GP). */

import { t } from "../i18n.js";

export function renderDriverDetail(driver, teamColor) {
  const color = teamColor(driver.team);
  const progress = driver.progress || [];
  // Mini sparkline SVG (cumul de points)
  const W = 240,
    H = 60,
    PAD = 4;
  let sparkSvg = "";
  if (progress.length >= 2) {
    const ys = progress.map((p) => p.cumulative);
    const yMax = Math.max(...ys, 1);
    const xStep = (W - 2 * PAD) / (progress.length - 1);
    const pts = progress.map((p, i) => {
      const x = PAD + i * xStep;
      const y = H - PAD - (p.cumulative / yMax) * (H - 2 * PAD);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    sparkSvg = `
      <svg class="dash-driver-spark" viewBox="0 0 ${W} ${H}" aria-hidden="true">
        <polyline fill="none" stroke="${color}" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"
                  points="${pts.join(" ")}"/>
        <circle cx="${pts[pts.length - 1].split(",")[0]}"
                cy="${pts[pts.length - 1].split(",")[1]}"
                r="3" fill="${color}"/>
      </svg>
    `;
  }
  // Tableau GP par GP (gain + cumul)
  const gpRows = progress
    .map(
      (p, i) => `
    <tr>
      <td class="t-rank muted">${i + 1}</td>
      <td>${p.shortName}</td>
      <td class="t-num ${p.gain > 0 ? "positive" : "muted"}">${p.gain > 0 ? "+" + p.gain : p.gain === 0 ? "0" : p.gain}</td>
      <td class="t-num"><strong>${p.cumulative}</strong></td>
    </tr>
  `,
    )
    .join("");
  const photo = driver.image
    ? `<img class="dash-driver-photo" src="${driver.image}" alt="" loading="lazy" onerror="this.style.display='none'"/>`
    : "";
  return `
    <div class="dash-driver-detail">
      <div class="dash-driver-head" style="border-left:3px solid ${color}">
        ${photo}
        <div class="dash-driver-id">
          <div class="dash-driver-name">${driver.name}</div>
          <div class="dash-driver-team" style="color:${color}">${driver.team}</div>
        </div>
        <div class="dash-driver-mini">
          <div><span class="dash-mini-label">${t("driver.rank")}</span><span class="dash-mini-val">${driver.rank}</span></div>
          <div><span class="dash-mini-label">${t("driver.points")}</span><span class="dash-mini-val">${driver.points}</span></div>
          <div><span class="dash-mini-label">${t("driver.deltaLast")}</span><span class="dash-mini-val ${driver.deltaLastGp > 0 ? "positive" : "muted"}">${driver.deltaLastGp > 0 ? "+" + driver.deltaLastGp : driver.deltaLastGp}</span></div>
          <div><span class="dash-mini-label">${t("driver.leaderGap")}</span><span class="dash-mini-val muted">${driver.leaderGap === 0 ? "—" : driver.leaderGap}</span></div>
        </div>
        ${sparkSvg}
      </div>
      <table class="dash-table dash-driver-progress">
        <thead>
          <tr>
            <th class="t-rank">#</th>
            <th>${t("driver.gp")}</th>
            <th class="t-num">${t("driver.gain")}</th>
            <th class="t-num">${t("driver.cumulative")}</th>
          </tr>
        </thead>
        <tbody>${gpRows}</tbody>
      </table>
    </div>
  `;
}
