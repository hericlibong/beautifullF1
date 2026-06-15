/* Beautiful F1 — Dashboard : onglet Coéquipiers (duels qualif). */

import { t } from "../i18n.js";
import { shortName, escapeAttr, fetchJson } from "../utils.js";

export function renderTeammateView(team, filter, teamColor) {
  const color = teamColor(team.team);
  const drivers = team.drivers || [];
  if (drivers.length < 2) return `<p class="dash-duel-empty">${t("tm.singleDriver")}</p>`;
  const [dA, dB] = drivers; // ordre alpha (fixé par le builder)
  const shortA = shortName(dA);
  const shortB = shortName(dB);

  // Filtrage des sessions
  const sessions = (team.sessions || []).filter((s) =>
    filter === "ALL" ? true : s.type === filter,
  );

  // H2H affiché : recalculé pour le filtre (sur les sessions filtrées)
  let winsA = 0,
    winsB = 0;
  sessions.forEach((s) => {
    if (s.fastest === dA) winsA++;
    else if (s.fastest === dB) winsB++;
  });

  const q3A = team.q3Count[dA] || 0;
  const q3B = team.q3Count[dB] || 0;

  // Timeline SVG : axe horizontal centré, dots positionnés selon gap signé
  // gap signé = (tB - tA) → si fastest=A, gap_signed = -gap (à gauche), si fastest=B, gap_signed = +gap (à droite)
  const points = sessions.map((s) => {
    const signed = s.fastest === dA ? -s.gapSec : s.fastest === dB ? s.gapSec : 0;
    return { ...s, signed };
  });

  const maxAbs = Math.max(0.5, ...points.map((p) => Math.abs(p.signed)));
  // Arrondi pour graduations propres : ceil au 0.5s supérieur
  const axisMax = Math.ceil(maxAbs * 2) / 2;

  const W = 720,
    H = 130,
    PAD_T = 28,
    PAD_B = 28,
    PAD_X = 30;
  const innerW = W - 2 * PAD_X;
  const yMid = PAD_T + (H - PAD_T - PAD_B) / 2;
  const xFor = (v) => PAD_X + ((v + axisMax) / (2 * axisMax)) * innerW;

  // Graduations : -axisMax, -axisMax/2, 0, +axisMax/2, +axisMax (5 ticks)
  const ticks = [-axisMax, -axisMax / 2, 0, axisMax / 2, axisMax];

  const dotsSvg = points
    .map((p) => {
      const cx = xFor(p.signed);
      const cy = yMid;
      const info = escapeAttr(buildTooltipPayload(p, dA, dB, color));
      if (p.type === "Q") {
        // Cercle plein pour Qualifs
        return `<circle cx="${cx}" cy="${cy}" r="6.5" fill="${color}" stroke="${color}" stroke-width="1.5" class="dash-tl-dot" data-info="${info}"/>`;
      }
      // Losange creux pour Sprint Qualifs (via polygon — pas de rotate, plus fiable)
      const s = 7.5;
      return `<polygon points="${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}" fill="none" stroke="${color}" stroke-width="2.2" class="dash-tl-dot" data-info="${info}"/>`;
    })
    .join("");

  const ticksSvg = ticks
    .map((tick) => {
      const x = xFor(tick);
      const label = tick === 0 ? "0" : tick > 0 ? `+${tick.toFixed(1)}s` : `${tick.toFixed(1)}s`;
      return `
      <line x1="${x}" x2="${x}" y1="${yMid - 8}" y2="${yMid + 8}" stroke="${tick === 0 ? "#5a6275" : "#3a4150"}" stroke-width="${tick === 0 ? 1.5 : 1}"/>
      <text x="${x}" y="${H - 10}" fill="#9aa3b2" font-size="10" text-anchor="middle">${label}</text>
    `;
    })
    .join("");

  // Score H2H : on choisit la "barre" en fonction du filtre
  const flexA = Math.max(0.01, winsA);
  const flexB = Math.max(0.01, winsB);
  const filterLabel =
    filter === "Q" ? t("tm.scopeQ") : filter === "SQ" ? t("tm.scopeSQ") : t("tm.scopeAll");

  return `
    <div class="dash-teammate-card" style="border-left-color:${color}">
      <div class="dash-teammate-head">
        <span class="dash-teammate-team" style="color:${color}">${team.team}</span>
        <span class="dash-teammate-filter">${filterLabel} • ${t("tm.sessions", { n: sessions.length })}</span>
      </div>

      <div class="dash-tl-scoreline">
        <div class="dash-tl-driver dash-tl-driver--a">
          <span class="dash-tl-name" style="color:${color}">${shortA}</span>
          <span class="dash-tl-wins">${winsA}</span>
        </div>
        <div class="dash-teammate-bar dash-tl-bar">
          <div class="dash-teammate-side" style="flex:${flexA};background:${color};opacity:1">
            <span>${winsA}</span>
          </div>
          <div class="dash-teammate-side dash-teammate-side--b" style="flex:${flexB};background:${color};opacity:0.55">
            <span>${winsB}</span>
          </div>
        </div>
        <div class="dash-tl-driver dash-tl-driver--b">
          <span class="dash-tl-wins">${winsB}</span>
          <span class="dash-tl-name" style="color:${color}">${shortB}</span>
        </div>
      </div>

      <div class="dash-teammate-q3">
        ${t("tm.q3Reached", { a: shortA, qa: q3A, b: shortB, qb: q3B })}
      </div>

      <div class="dash-tl-axis-labels">
        <span>${t("tm.fasterLeft", { name: shortA })}</span>
        <span>${t("tm.fasterRight", { name: shortB })}</span>
      </div>
      <svg viewBox="0 0 ${W} ${H}" class="dash-tl-svg" aria-label="${t("tm.timelineAria")}">
        <line x1="${PAD_X}" x2="${W - PAD_X}" y1="${yMid}" y2="${yMid}" stroke="#3a4150" stroke-width="1"/>
        ${ticksSvg}
        ${dotsSvg}
      </svg>
      <div class="dash-tl-legend">
        <span><span class="dash-tl-legend-dot" style="background:${color}"></span> ${t("tm.quali")}</span>
        <span><span class="dash-tl-legend-diamond" style="border-color:${color}"></span> ${t("tm.sprintQuali")}</span>
      </div>

      <div id="dash-tl-tooltip" class="dash-tl-tooltip"></div>
    </div>
  `;
}

function buildTooltipPayload(p, dA, dB, color) {
  // Encodé pour stockage dans data-info ; format JSON minimal
  return JSON.stringify({
    gp: p.shortName,
    type: p.type === "Q" ? t("tm.quali") : t("tm.sprintQuali"),
    timeA: p.timeA,
    timeB: p.timeB,
    fastest: p.fastest === dA ? "A" : "B",
    nameA: shortName(dA),
    nameB: shortName(dB),
    gap: p.gapSec.toFixed(3),
    color,
  });
}

function attachTimelineHover() {
  const tooltip = document.getElementById("dash-tl-tooltip");
  if (!tooltip) return;
  document.querySelectorAll(".dash-tl-dot").forEach((el) => {
    el.addEventListener("mouseenter", () => {
      let info;
      try {
        info = JSON.parse(el.getAttribute("data-info"));
      } catch {
        return;
      }
      const winnerName = info.fastest === "A" ? info.nameA : info.nameB;
      tooltip.innerHTML = `
        <div class="dash-tl-tt-head"><strong>${info.gp}</strong> · ${info.type}</div>
        <div class="dash-tl-tt-row">${info.nameA} : ${info.timeA || "—"}</div>
        <div class="dash-tl-tt-row">${info.nameB} : ${info.timeB || "—"}</div>
        <div class="dash-tl-tt-row" style="color:${info.color}"><strong>${winnerName} +${info.gap}s</strong></div>
      `;
      tooltip.style.opacity = "1";
    });
    el.addEventListener("mousemove", (e) => {
      const card = el.closest(".dash-teammate-card");
      if (!card) return;
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left + 12;
      const y = e.clientY - rect.top + 12;
      tooltip.style.left = `${x}px`;
      tooltip.style.top = `${y}px`;
    });
    el.addEventListener("mouseleave", () => {
      tooltip.style.opacity = "0";
    });
  });
}

// Câble l'onglet Coéquipiers. Les données qualif (~80 Ko) sont chargées à la
// demande au premier affichage de l'onglet → allège le chargement initial.
export function initTeammates(dashRes, teamColor) {
  let loaded = false;
  const load = async () => {
    if (loaded) return;
    loaded = true;
    const qualiRes = await fetchJson("data/qualifying_2026.json");
    renderTeammatesPane(dashRes, qualiRes, teamColor);
  };
  const tab = document.querySelector('.dash-tab[data-tab="teammates"]');
  if (tab) tab.addEventListener("click", load);
  if (tab && tab.classList.contains("active")) load();
}

function renderTeammatesPane(dashRes, qualiRes, teamColor) {
  const teamSelect = document.getElementById("dash-teammates-team");
  const teammatesContent = document.getElementById("dash-teammates-content");
  const pillButtons = document.querySelectorAll(".dash-pill");

  if (teammatesContent && (!qualiRes || !qualiRes.teammates)) {
    teammatesContent.innerHTML = `<p class="dash-duel-empty">${t("tm.dataUnavailable")}</p>`;
    return;
  }
  if (!teammatesContent || !teamSelect || !qualiRes || !qualiRes.teammates) return;

  // Trie les équipes selon le classement constructeurs (en tête en premier)
  const teamRank = new Map();
  ((dashRes.standings && dashRes.standings.constructors) || []).forEach((c, i) =>
    teamRank.set(c.team, i),
  );
  const teams = qualiRes.teammates.slice().sort((x, y) => {
    const rx = teamRank.has(x.team) ? teamRank.get(x.team) : 999;
    const ry = teamRank.has(y.team) ? teamRank.get(y.team) : 999;
    return rx - ry;
  });

  teamSelect.innerHTML = teams.map((tm) => `<option value="${tm.team}">${tm.team}</option>`).join("");
  teamSelect.value = teams[0].team;

  let currentFilter = "ALL";
  const render = () => {
    const team = teams.find((tm) => tm.team === teamSelect.value);
    if (!team) return;
    teammatesContent.innerHTML = renderTeammateView(team, currentFilter, teamColor);
    attachTimelineHover();
  };

  teamSelect.addEventListener("change", render);
  pillButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      currentFilter = btn.dataset.session;
      pillButtons.forEach((b) => {
        const active = b.dataset.session === currentFilter;
        b.classList.toggle("active", active);
        b.setAttribute("aria-selected", active ? "true" : "false");
      });
      render();
    });
  });

  render();
}
