/* Beautiful F1 — Dashboard : onglet Duel (head-to-head pilotes). */

import { t } from "../i18n.js";

export function renderDuelPanel(a, b, teamColor) {
  const cA = teamColor(a.team),
    cB = teamColor(b.team);
  const progA = a.progress || [];
  const progB = b.progress || [];
  const n = Math.min(progA.length, progB.length);

  // Métriques calculées
  const totalA = a.points,
    totalB = b.points;
  const gap = totalA - totalB;
  const bestA = progA.length ? Math.max(...progA.map((p) => p.gain)) : 0;
  const bestB = progB.length ? Math.max(...progB.map((p) => p.gain)) : 0;

  // Duel direct par GP
  let winsA = 0,
    winsB = 0;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const ga = progA[i].gain,
      gb = progB[i].gain;
    let winner = "tie";
    if (ga > gb) {
      winsA++;
      winner = "a";
    } else if (gb > ga) {
      winsB++;
      winner = "b";
    }
    rows.push({ gp: progA[i].shortName, ga, gb, winner, diff: ga - gb });
  }

  // Helper : barre comparative pour une métrique
  // valA et valB peuvent être 0 simultanément (ex. wins).
  function metricBar(label, valA, valB, fmt, note) {
    fmt = fmt || ((v) => v);
    const total = valA + valB;
    const pctA = total > 0 ? (valA / total) * 100 : 50;
    const pctB = 100 - pctA;
    const flexA = Math.max(0.01, valA);
    const flexB = Math.max(0.01, valB);
    return `
      <div class="dash-duel-metric">
        <div class="dash-duel-metric-label">${label}</div>
        <div class="dash-duel-metric-bar">
          <div class="dash-duel-metric-side dash-duel-metric-side--a"
               style="flex:${flexA};background:${cA}">
            <span class="dash-duel-metric-value">${fmt(valA)}</span>
          </div>
          <div class="dash-duel-metric-side dash-duel-metric-side--b"
               style="flex:${flexB};background:${cB}">
            <span class="dash-duel-metric-value">${fmt(valB)}</span>
          </div>
        </div>
        ${
          total > 0
            ? `
        <div class="dash-duel-metric-pct">
          <span>${pctA.toFixed(0)}%</span>
          <span>${pctB.toFixed(0)}%</span>
        </div>`
            : ""
        }
        ${note ? `<div class="dash-duel-metric-note">${note}</div>` : ""}
      </div>
    `;
  }

  const photoA = a.image
    ? `<img class="dash-duel-photo" src="${a.image}" alt="" loading="lazy" onerror="this.style.display='none'"/>`
    : "";
  const photoB = b.image
    ? `<img class="dash-duel-photo" src="${b.image}" alt="" loading="lazy" onerror="this.style.display='none'"/>`
    : "";

  // Évolution de l'écart cumulé : line chart amélioré (axes + labels)
  const W = 480,
    H = 160,
    PAD_L = 28,
    PAD_R = 12,
    PAD_T = 12,
    PAD_B = 22;
  const cumDiff = [];
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += progA[i].gain - progB[i].gain;
    cumDiff.push(acc);
  }
  const maxAbs = Math.max(1, ...cumDiff.map((v) => Math.abs(v)));
  const xStep = (W - PAD_L - PAD_R) / Math.max(1, n - 1);
  const yMid = (H - PAD_T - PAD_B) / 2 + PAD_T;
  const ySpan = (H - PAD_T - PAD_B) / 2;
  const yScale = (v) => yMid - (v / maxAbs) * ySpan;
  const pts = cumDiff.map((v, i) => `${(PAD_L + i * xStep).toFixed(1)},${yScale(v).toFixed(1)}`);
  const lineColor = acc >= 0 ? cA : cB;

  return `
    <div class="dash-duel-headers">
      <div class="dash-duel-head" style="border-left-color:${cA}">
        <div class="dash-duel-photo-wrap" style="border-color:${cA}">${photoA}</div>
        <div class="dash-duel-id">
          <div class="dash-duel-name">${a.shortName}</div>
          <div class="dash-duel-team" style="color:${cA}">${a.team}</div>
          <div class="dash-duel-meta">${t("duel.metaRank", { rank: a.rank, pts: totalA })}</div>
        </div>
      </div>
      <div class="dash-duel-vs-big" title="${t("duel.pointsGap")}">
        ${gap === 0 ? "=" : gap > 0 ? `+${gap}` : `${gap}`}
      </div>
      <div class="dash-duel-head dash-duel-head--right" style="border-right-color:${cB}">
        <div class="dash-duel-id" style="text-align:right">
          <div class="dash-duel-name">${b.shortName}</div>
          <div class="dash-duel-team" style="color:${cB}">${b.team}</div>
          <div class="dash-duel-meta">${t("duel.metaRank", { rank: b.rank, pts: totalB })}</div>
        </div>
        <div class="dash-duel-photo-wrap" style="border-color:${cB}">${photoB}</div>
      </div>
    </div>

    <div class="dash-duel-metrics">
      ${metricBar(t("duel.totalPoints"), totalA, totalB)}
      ${metricBar(t("duel.bestRace"), bestA, bestB)}
      ${metricBar(t("duel.edge"), winsA, winsB, undefined, t("duel.edgeNote", { a: a.shortName, b: b.shortName }))}
    </div>

    <div class="dash-duel-chart">
      <div class="dash-duel-chart-title">${t("duel.cumChart", { a: a.shortName, b: b.shortName })}</div>
      <svg viewBox="0 0 ${W} ${H}" class="dash-duel-svg" aria-hidden="true">
        <!-- axes Y : labels max et min -->
        <text x="${PAD_L - 4}" y="${PAD_T + 4}" fill="#9aa3b2" font-size="10" text-anchor="end">+${maxAbs}</text>
        <text x="${PAD_L - 4}" y="${yMid + 3}" fill="#9aa3b2" font-size="10" text-anchor="end">0</text>
        <text x="${PAD_L - 4}" y="${H - PAD_B}" fill="#9aa3b2" font-size="10" text-anchor="end">−${maxAbs}</text>
        <!-- ligne zéro -->
        <line x1="${PAD_L}" x2="${W - PAD_R}" y1="${yMid}" y2="${yMid}" stroke="#3a4150" stroke-dasharray="2 3"/>
        <!-- courbe -->
        <polyline fill="none" stroke="${lineColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${pts.join(" ")}"/>
        <!-- points + valeurs -->
        ${cumDiff
          .map((v, i) => {
            const x = PAD_L + i * xStep;
            const y = yScale(v);
            return `
            <circle cx="${x}" cy="${y}" r="3" fill="${lineColor}"/>
            <text x="${x}" y="${y - 7}" fill="${lineColor}" font-size="10" text-anchor="middle">${v > 0 ? "+" + v : v}</text>
          `;
          })
          .join("")}
        <!-- labels GP -->
        ${progA
          .slice(0, n)
          .map(
            (p, i) => `
          <text x="${PAD_L + i * xStep}" y="${H - 6}" fill="#9aa3b2" font-size="10" text-anchor="middle">${p.shortName}</text>
        `,
          )
          .join("")}
      </svg>
    </div>

    <table class="dash-table dash-duel-table">
      <thead>
        <tr>
          <th>${t("duel.colGp")}</th>
          <th class="t-num" style="color:${cA}">${a.shortName}</th>
          <th class="t-num" style="color:${cB}">${b.shortName}</th>
          <th class="t-num">${t("col.delta")}</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (r) => `
          <tr>
            <td>${r.gp}</td>
            <td class="t-num ${r.winner === "a" ? "dash-duel-cell-win" : "muted"}" ${r.winner === "a" ? `style="color:${cA}"` : ""}><strong>${r.ga}</strong></td>
            <td class="t-num ${r.winner === "b" ? "dash-duel-cell-win" : "muted"}" ${r.winner === "b" ? `style="color:${cB}"` : ""}><strong>${r.gb}</strong></td>
            <td class="t-num muted">${r.diff > 0 ? "+" + r.diff : r.diff}</td>
          </tr>
        `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

// Câble les deux sélecteurs de l'onglet Duel et rend le panneau au changement.
export function initDuel(dashRes, teamColor) {
  const allDriversList = (dashRes.standings && dashRes.standings.drivers) || [];
  const selA = document.getElementById("duel-a");
  const selB = document.getElementById("duel-b");
  if (!selA || !selB || allDriversList.length < 2) return;

  const optHtml = allDriversList
    .map((d) => `<option value="${d.name}">${d.shortName} (${d.team})</option>`)
    .join("");
  selA.innerHTML = optHtml;
  selB.innerHTML = optHtml;
  selA.value = allDriversList[0].name;
  selB.value = allDriversList[1].name;

  const renderDuel = () => {
    const a = allDriversList.find((d) => d.name === selA.value);
    const b = allDriversList.find((d) => d.name === selB.value);
    const target = document.getElementById("dash-duel-content");
    if (!a || !b || a.name === b.name) {
      target.innerHTML = `<p class="dash-duel-empty">${t("duel.pickTwo")}</p>`;
      return;
    }
    target.innerHTML = renderDuelPanel(a, b, teamColor);
  };
  selA.addEventListener("change", renderDuel);
  selB.addEventListener("change", renderDuel);
  renderDuel();
}
