/* Beautiful F1 — Dashboard : zone "Histoire" du drill-down circuit
 * (scatter chronologie + palmarès en barres + interactions). */

import { t } from "../i18n.js";
import { HISTORY_TEAM_COLORS } from "../constants.js";

// Couleur d'une écurie pour le scatter (teamId historique prioritaire, puis teams.json, puis fallback)
export function histTeamColor(edition, teamColor) {
  return HISTORY_TEAM_COLORS[edition.teamId] || teamColor(edition.team);
}

// Scatter chronologie : X = année, Y = victoires (pilote ou écurie), carré coloré par écurie.
export function renderHistoryScatter(history, mode, teamColor) {
  const ed = history.editions;
  if (!ed.length) return `<div class="dash-history-empty">${t("history.empty")}</div>`;

  const winsKey = mode === "team" ? "teamWins" : "driverWins";
  const years = ed.map((e) => e.year);
  const xMin = Math.min(...years),
    xMax = Math.max(...years);
  const yMax = Math.max(...ed.map((e) => e[winsKey]), 1);

  // Géométrie SVG (coordonnées internes ; mise à l'échelle via viewBox)
  const W = 920,
    H = 300;
  const padL = 34,
    padR = 14,
    padT = 14,
    padB = 30;
  const plotW = W - padL - padR,
    plotH = H - padT - padB;
  const sq = 13; // côté du carré
  const xOf = (y) => padL + (xMax === xMin ? plotW / 2 : ((y - xMin) / (xMax - xMin)) * plotW);
  const yOf = (v) => padT + plotH - (yMax <= 1 ? plotH / 2 : ((v - 1) / (yMax - 1)) * plotH);

  // Lignes de victoires (Y) + libellés
  let gridSvg = "";
  for (let v = 1; v <= yMax; v++) {
    const y = yOf(v);
    gridSvg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" class="dash-history-grid"/>`;
    gridSvg += `<text x="${padL - 8}" y="${y + 4}" class="dash-history-axis" text-anchor="end">${v}</text>`;
  }

  // Repères d'années (tous les 5 ans + bornes)
  let xticks = "";
  for (let yr = Math.ceil(xMin / 5) * 5; yr <= xMax; yr += 5) {
    xticks += `<text x="${xOf(yr)}" y="${H - 8}" class="dash-history-axis" text-anchor="middle">${yr}</text>`;
  }

  // Carrés (un par édition), data-i = index dans editions pour le tooltip
  const squares = ed
    .map((e, i) => {
      const cx = xOf(e.year),
        cy = yOf(e[winsKey]);
      const color = histTeamColor(e, teamColor);
      const winnerAttr = (e.winner || "").replace(/"/g, "&quot;");
      return `<rect x="${(cx - sq / 2).toFixed(1)}" y="${(cy - sq / 2).toFixed(1)}" width="${sq}" height="${sq}" rx="2"
                  fill="${color}" class="dash-history-sq" data-i="${i}" data-winner="${winnerAttr}" tabindex="0"/>`;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${W} ${H}" class="dash-history-svg" role="img" aria-label="${t("history.title")}">
      ${gridSvg}${xticks}${squares}
    </svg>
  `;
}

// Agrège les éditions par vainqueur (palmarès du circuit).
// Couleur retenue = couleur de l'écurie majoritaire dans les victoires du pilote sur ce circuit.
function aggregateHistoryWinners(history, teamColor) {
  const byWinner = new Map();
  for (const e of history.editions) {
    if (!e.winner) continue;
    let agg = byWinner.get(e.winner);
    if (!agg) {
      agg = { winner: e.winner, wins: 0, teamCounts: new Map(), photo: null, lastYear: -1 };
      byWinner.set(e.winner, agg);
    }
    agg.wins += 1;
    const teamKey = e.teamId || e.team || "";
    agg.teamCounts.set(teamKey, (agg.teamCounts.get(teamKey) || 0) + 1);
    if (e.year >= agg.lastYear) {
      agg.lastYear = e.year;
      if (e.photo) agg.photo = e.photo;
    }
  }
  const list = [];
  for (const agg of byWinner.values()) {
    let bestTeam = "",
      bestCount = -1;
    for (const [k, c] of agg.teamCounts) {
      if (c > bestCount) {
        bestCount = c;
        bestTeam = k;
      }
    }
    const sample = history.editions.find(
      (e) => e.winner === agg.winner && (e.teamId || e.team) === bestTeam,
    );
    const color = sample ? histTeamColor(sample, teamColor) : teamColor("");
    list.push({ winner: agg.winner, wins: agg.wins, color, photo: agg.photo });
  }
  list.sort((a, b) => b.wins - a.wins || a.winner.localeCompare(b.winner));
  return list;
}

// Rendu du palmarès en barres horizontales (couleur = écurie majoritaire du pilote sur ce circuit).
export function renderHistoryBars(history, teamColor) {
  const list = aggregateHistoryWinners(history, teamColor);
  if (!list.length) return "";
  const maxWins = list[0].wins;
  const rows = list
    .map((d) => {
      const pct = (d.wins / maxWins) * 100;
      const initials = d.winner
        .split(/\s+/)
        .map((w) => w[0])
        .filter(Boolean)
        .slice(0, 2)
        .join("")
        .toUpperCase();
      const attrName = (d.winner || "").replace(/"/g, "&quot;");
      const photoNode = d.photo
        ? `<span class="dash-history-bar-photo-wrap" style="background:${d.color}">
           <span class="dash-history-bar-photo-initials">${initials}</span>
           <img class="dash-history-bar-photo" src="${d.photo}" alt="" loading="lazy" onerror="this.style.display='none'"/>
         </span>`
        : `<span class="dash-history-bar-photo-wrap dash-history-bar-photo-empty" style="background:${d.color}">
           <span class="dash-history-bar-photo-initials">${initials}</span>
         </span>`;
      return `
      <li class="dash-history-bar-row" data-winner="${attrName}" tabindex="0">
        ${photoNode}
        <span class="dash-history-bar-name">${d.winner}</span>
        <span class="dash-history-bar-track">
          <span class="dash-history-bar-fill" style="width:${pct.toFixed(2)}%;background:${d.color}"></span>
        </span>
        <span class="dash-history-bar-count">${d.wins}</span>
      </li>
    `;
    })
    .join("");
  return `
    <div class="dash-history-bars">
      <div class="dash-history-bars-head">
        <div class="dash-history-bars-title">${t("history.barsTitle")}</div>
        <div class="dash-history-bars-sub">${t("history.barsSub")}</div>
      </div>
      <ul class="dash-history-bars-list">${rows}</ul>
    </div>
  `;
}

// Câblage des interactions de la zone Histoire : tooltip au survol + bascule de l'axe Y.
export function wireCircuitHistory(detail, history, teamColor) {
  const root = detail.querySelector(".dash-history");
  if (!root) return;
  const plot = root.querySelector(".dash-history-plot");
  const tip = root.querySelector(".dash-history-tip");
  const yselect = root.querySelector(".dash-history-yselect");

  const positionTip = (sq) => {
    if (!sq) return;
    const plotRect = plot.getBoundingClientRect();
    const sqRect = sq.getBoundingClientRect();
    const cx = sqRect.left + sqRect.width / 2 - plotRect.left;
    const cy = sqRect.top - plotRect.top;
    const tipW = tip.offsetWidth;
    const tipH = tip.offsetHeight;
    let left = cx - tipW / 2;
    const maxLeft = plotRect.width - tipW - 4;
    if (left < 4) left = 4;
    if (left > maxLeft) left = Math.max(4, maxLeft);
    let top = cy - tipH - 12;
    if (top < 4) top = cy + sqRect.height + 12;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  };

  const showTip = (i, sq) => {
    const e = history.editions[i];
    if (!e) return;
    const color = histTeamColor(e, teamColor);
    const rows = [];
    rows.push(
      `<div class="dash-history-tip-row"><span>${t("history.tipTeam")}</span><strong style="color:${color}">${e.team}</strong></div>`,
    );
    if (e.engine)
      rows.push(
        `<div class="dash-history-tip-row"><span>${t("history.tipEngine")}</span><strong>${e.engine}</strong></div>`,
      );
    if (e.grid)
      rows.push(
        `<div class="dash-history-tip-row"><span>${t("history.tipGrid")}</span><strong>${e.grid}</strong></div>`,
      );
    if (e.poleman)
      rows.push(
        `<div class="dash-history-tip-row"><span>${t("history.tipPole")}</span><strong>${e.poleman}${e.poleTime ? " · " + e.poleTime : ""}</strong></div>`,
      );
    if (e.podium && e.podium.length === 3)
      rows.push(
        `<div class="dash-history-tip-row"><span>${t("history.tipPodium")}</span><strong>2. ${e.podium[1]} · 3. ${e.podium[2]}</strong></div>`,
      );
    if (e.champion)
      rows.push(
        `<div class="dash-history-tip-row"><span>${t("history.tipChampion")}</span><strong>${e.champion}</strong></div>`,
      );
    rows.push(
      `<div class="dash-history-tip-row"><span>${t("history.tipDriverWins")}</span><strong>${"🏆".repeat(Math.min(e.driverWins, 8))} (${e.driverWins})</strong></div>`,
    );
    rows.push(
      `<div class="dash-history-tip-row"><span>${t("history.tipTeamWins")}</span><strong>${e.teamWins}</strong></div>`,
    );
    tip.innerHTML = `
      <div class="dash-history-tip-head" style="border-color:${color}">
        ${e.photo ? `<img src="${e.photo}" alt="" class="dash-history-tip-photo" loading="lazy"/>` : ""}
        <div>
          <div class="dash-history-tip-name">${e.flag} ${e.winner}</div>
          <div class="dash-history-tip-year">${e.year}${e.raceTime ? " · " + e.raceTime : ""}</div>
        </div>
      </div>
      ${rows.join("")}
    `;
    tip.hidden = false;
    positionTip(sq);
  };

  const hideTip = () => {
    tip.hidden = true;
  };

  // Highlight croisé entre scatter et barres : ajoute/retire .is-dim et .is-active selon le pilote actif.
  const setActiveWinner = (name) => {
    plot.querySelectorAll(".dash-history-sq").forEach((s) => {
      if (!name) {
        s.classList.remove("is-dim", "is-active");
        return;
      }
      if (s.dataset.winner === name) {
        s.classList.add("is-active");
        s.classList.remove("is-dim");
      } else {
        s.classList.add("is-dim");
        s.classList.remove("is-active");
      }
    });
    root.querySelectorAll(".dash-history-bar-row").forEach((b) => {
      if (!name) {
        b.classList.remove("is-dim", "is-active");
        return;
      }
      if (b.dataset.winner === name) {
        b.classList.add("is-active");
        b.classList.remove("is-dim");
      } else {
        b.classList.add("is-dim");
        b.classList.remove("is-active");
      }
    });
  };

  plot.addEventListener("mouseover", (ev) => {
    const sq = ev.target.closest(".dash-history-sq");
    if (sq) {
      showTip(+sq.dataset.i, sq);
      setActiveWinner(sq.dataset.winner);
    }
  });
  plot.addEventListener("mouseout", (ev) => {
    const sq = ev.target.closest(".dash-history-sq");
    if (!sq) return;
    const next =
      ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest(".dash-history-sq");
    if (next !== sq) {
      hideTip();
      setActiveWinner(null);
    }
  });
  plot.addEventListener("focusin", (ev) => {
    const sq = ev.target.closest(".dash-history-sq");
    if (sq) {
      showTip(+sq.dataset.i, sq);
      setActiveWinner(sq.dataset.winner);
    }
  });
  plot.addEventListener("focusout", (ev) => {
    const sq = ev.target.closest(".dash-history-sq");
    if (sq) {
      hideTip();
      setActiveWinner(null);
    }
  });

  const barsList = root.querySelector(".dash-history-bars-list");
  if (barsList) {
    barsList.addEventListener("mouseover", (ev) => {
      const row = ev.target.closest(".dash-history-bar-row");
      if (row) setActiveWinner(row.dataset.winner);
    });
    barsList.addEventListener("mouseout", (ev) => {
      const row = ev.target.closest(".dash-history-bar-row");
      if (!row) return;
      const next =
        ev.relatedTarget &&
        ev.relatedTarget.closest &&
        ev.relatedTarget.closest(".dash-history-bar-row");
      if (next !== row) setActiveWinner(null);
    });
    barsList.addEventListener("focusin", (ev) => {
      const row = ev.target.closest(".dash-history-bar-row");
      if (row) setActiveWinner(row.dataset.winner);
    });
    barsList.addEventListener("focusout", (ev) => {
      const row = ev.target.closest(".dash-history-bar-row");
      if (row) setActiveWinner(null);
    });
  }

  yselect.addEventListener("change", () => {
    plot.innerHTML = renderHistoryScatter(history, yselect.value, teamColor);
    tip.hidden = true;
    plot.appendChild(tip);
    setActiveWinner(null);
  });
}
