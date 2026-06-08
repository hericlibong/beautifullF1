/* Beautiful F1 — Dashboard 2026
 * Charge data/dashboard_2026.json + assets/teams.json et peuple la page.
 */

// ---------- i18n (FR / EN) ----------
let I18N = {};
let LANG = localStorage.getItem("bf1-lang") || "fr";

function t(key, vars) {
  const dict = I18N[LANG] || I18N.fr || {};
  let s = dict[key] != null ? dict[key] : key;
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}

function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.innerHTML = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
}

function setupLangSwitcher() {
  const sw = document.getElementById("lang-switch");
  if (!sw) return;
  sw.querySelectorAll("button[data-lang]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === LANG);
    btn.addEventListener("click", () => {
      if (btn.dataset.lang === LANG) return;
      localStorage.setItem("bf1-lang", btn.dataset.lang);
      location.reload();
    });
  });
}

(async function () {
  const [dashRes, teamsRes, manifestRes, qualiRes, circuitsRes, i18nRes] = await Promise.all([
    fetch("data/dashboard_2026.json").then(r => r.json()),
    fetch("assets/teams.json").then(r => r.json()),
    fetch("assets/manifest.json").then(r => r.json()),
    fetch("data/qualifying_2026.json").then(r => r.ok ? r.json() : null).catch(() => null),
    fetch("data/circuits_2026.json").then(r => r.ok ? r.json() : null).catch(() => null),
    fetch("assets/i18n.json").then(r => r.json()).catch(() => ({})),
  ]);

  I18N = i18nRes || {};
  document.documentElement.lang = LANG;
  applyStaticI18n();
  setupLangSwitcher();

  const teams = teamsRes.teams || {};
  const teamColor = name => (teams[name] && teams[name].color) || teamsRes.fallbackColor;

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

  kpiContainer.innerHTML = kpis.map((kpi, i) => `
    <div class="dash-kpi ${kpi.countdown ? 'dash-kpi--countdown' : ''}" data-kpi-idx="${i}">
      <div class="dash-kpi-label">${kpi.label}</div>
      <div class="dash-kpi-value" ${kpi.color ? `style="color:${kpi.color}"` : ""}>${kpi.value || ""}</div>
      <div class="dash-kpi-sub">${kpi.sub}</div>
    </div>
  `).join("");

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

  // ---------- Classements ----------
  const fmtDelta = n => n > 0 ? `+${n}` : (n === 0 ? "0" : `${n}`);
  const trophy = rank => rank === 1 ? "🏆" : rank;

  const driversTable = document.getElementById("standings-drivers");
  if (driversTable && dashRes.standings && dashRes.standings.drivers) {
    const allDrivers = dashRes.standings.drivers;
    const TOP_N = 10;
    const renderDriverRows = (list) => list.map(d => `
      <tr class="t-clickable" data-driver="${d.name}">
        <td class="t-rank ${d.rank === 1 ? 'leader' : ''}">${trophy(d.rank)}</td>
        <td class="t-name">
          <span class="t-swatch" style="background:${teamColor(d.team)}"></span>
          ${d.shortName}
        </td>
        <td class="t-team">${d.team}</td>
        <td class="t-num"><strong>${d.points}</strong></td>
        <td class="t-num ${d.deltaLastGp > 0 ? 'positive' : 'muted'}">${fmtDelta(d.deltaLastGp)}</td>
        <td class="t-num t-gap muted">${d.leaderGap === 0 ? '—' : d.leaderGap}</td>
      </tr>
    `).join("");
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
      driversTable.querySelectorAll("tr.t-detail").forEach(n => n.remove());
      driversTable.querySelectorAll("tr.t-active").forEach(n => n.classList.remove("t-active"));
      const wasOpen = tr.dataset.expanded === "1";
      // Reset all expanded markers
      driversTable.querySelectorAll("tr.t-clickable").forEach(n => n.dataset.expanded = "");
      if (wasOpen) return;
      tr.dataset.expanded = "1";
      tr.classList.add("t-active");
      const driver = allDrivers.find(d => d.name === tr.dataset.driver);
      if (!driver) return;
      const detail = document.createElement("tr");
      detail.className = "t-detail";
      detail.innerHTML = `<td colspan="6">${renderDriverDetail(driver, teamColor)}</td>`;
      tr.after(detail);
    });
  }

  const teamsTable = document.getElementById("standings-constructors");
  if (teamsTable && dashRes.standings && dashRes.standings.constructors) {
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
        ${dashRes.standings.constructors.map(c => `
          <tr>
            <td class="t-rank ${c.rank === 1 ? 'leader' : ''}">${trophy(c.rank)}</td>
            <td class="t-name">
              <span class="t-swatch" style="background:${teamColor(c.team)}"></span>
              ${c.team}
            </td>
            <td class="t-num"><strong>${c.points}</strong></td>
            <td class="t-num ${c.deltaLastGp > 0 ? 'positive' : 'muted'}">${fmtDelta(c.deltaLastGp)}</td>
            <td class="t-num t-gap muted">${c.leaderGap === 0 ? '—' : c.leaderGap}</td>
          </tr>
        `).join("")}
      </tbody>
    `;
  }

  // ---------- Onglets Pilotes / Constructeurs / Calendrier ----------
  const scrollCalendarToNext = () => {
    const list = document.getElementById("dash-calendar");
    const next = list && list.querySelector(".dash-cal-next");
    if (next) {
      const offset = next.offsetTop - list.offsetTop;
      list.scrollTop = Math.max(0, offset - 60);
    }
  };

  document.querySelectorAll(".dash-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      document.querySelectorAll(".dash-tab").forEach(b => {
        const isActive = b.dataset.tab === target;
        b.classList.toggle("active", isActive);
        b.setAttribute("aria-selected", isActive ? "true" : "false");
      });
      document.querySelectorAll(".dash-tab-pane").forEach(p => {
        p.classList.toggle("active", p.id === `standings-pane-${target}`);
      });
      if (target === "calendar") {
        // L'auto-scroll ne fonctionne que quand le pane est visible
        requestAnimationFrame(scrollCalendarToNext);
      }
    });
  });

  // ---------- Duel head-to-head ----------
  const allDriversList = (dashRes.standings && dashRes.standings.drivers) || [];
  const selA = document.getElementById("duel-a");
  const selB = document.getElementById("duel-b");
  if (selA && selB && allDriversList.length >= 2) {
    const optHtml = allDriversList.map(d =>
      `<option value="${d.name}">${d.shortName} (${d.team})</option>`
    ).join("");
    selA.innerHTML = optHtml;
    selB.innerHTML = optHtml;
    selA.value = allDriversList[0].name;
    selB.value = allDriversList[1].name;

    const renderDuel = () => {
      const a = allDriversList.find(d => d.name === selA.value);
      const b = allDriversList.find(d => d.name === selB.value);
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

  // ---------- Coéquipiers (duels qualif) ----------
  const teamSelect = document.getElementById("dash-teammates-team");
  const teammatesContent = document.getElementById("dash-teammates-content");
  const pillButtons = document.querySelectorAll(".dash-pill");

  if (teammatesContent && (!qualiRes || !qualiRes.teammates)) {
    teammatesContent.innerHTML = `<p class="dash-duel-empty">${t("tm.dataUnavailable")}</p>`;
  } else if (teammatesContent && teamSelect && qualiRes && qualiRes.teammates) {
    // Trie les équipes selon le classement constructeurs (en tête en premier)
    const teamRank = new Map();
    (dashRes.standings && dashRes.standings.constructors || []).forEach((c, i) => teamRank.set(c.team, i));
    const teams = qualiRes.teammates.slice().sort((x, y) => {
      const rx = teamRank.has(x.team) ? teamRank.get(x.team) : 999;
      const ry = teamRank.has(y.team) ? teamRank.get(y.team) : 999;
      return rx - ry;
    });

    teamSelect.innerHTML = teams.map(t => `<option value="${t.team}">${t.team}</option>`).join("");
    teamSelect.value = teams[0].team;

    let currentFilter = "ALL";
    const render = () => {
      const team = teams.find(t => t.team === teamSelect.value);
      if (!team) return;
      teammatesContent.innerHTML = renderTeammateView(team, currentFilter, teamColor);
      attachTimelineHover();
    };

    teamSelect.addEventListener("change", render);
    pillButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        currentFilter = btn.dataset.session;
        pillButtons.forEach(b => {
          const active = b.dataset.session === currentFilter;
          b.classList.toggle("active", active);
          b.setAttribute("aria-selected", active ? "true" : "false");
        });
        render();
      });
    });

    render();
  }

  // ---------- Calendrier ----------
  const calContainer = document.getElementById("dash-calendar");
  const calProgress = document.getElementById("dash-calendar-progress");
  if (calContainer && dashRes.calendar) {
    const cal = dashRes.calendar;
    const played = cal.filter(c => c.status === "played").length;
    if (calProgress) calProgress.textContent = `${played} / ${cal.length} GP`;

    const circuits = (circuitsRes && circuitsRes.circuits) || {};
    calContainer.innerHTML = cal.map(c => {
      const statusIcon =
        c.status === "played" ? "✓" :
        c.status === "next"   ? "▶" :
        "·";
      const winnerHtml = c.winner
        ? `<span class="dash-cal-winner" style="color:${teamColor(c.winner.team)}">${c.winner.shortName}</span>`
        : (c.status === "next" ? `<span class="dash-cal-next-tag">${t("cal.nextTag")}</span>` : "");
      const sprintBadge = c.isSprint ? `<span class="dash-cal-sprint" title="${t("cal.sprintWeekend")}">S</span>` : "";
      const hasInfo = !!circuits[c.name];
      return `
        <li class="dash-cal-item dash-cal-${c.status} ${hasInfo ? 'dash-cal-clickable' : ''}" data-gp="${c.name}">
          <span class="dash-cal-round">${c.round}</span>
          <span class="dash-cal-status">${statusIcon}</span>
          <span class="dash-cal-name">${c.shortName}${sprintBadge}</span>
          <span class="dash-cal-date">${formatDateShort(c.date)}</span>
          ${winnerHtml}
        </li>
      `;
    }).join("");

    // Drill-down circuit : clic sur une ligne → panneau détaillé déplié dessous
    calContainer.addEventListener("click", (e) => {
      const li = e.target.closest("li.dash-cal-clickable");
      if (!li) return;
      // Ferme tout panneau déjà ouvert
      calContainer.querySelectorAll(".dash-circuit-detail").forEach(n => n.remove());
      calContainer.querySelectorAll(".dash-cal-active").forEach(n => n.classList.remove("dash-cal-active"));
      const wasOpen = li.dataset.open === "1";
      calContainer.querySelectorAll("li.dash-cal-clickable").forEach(n => n.dataset.open = "");
      if (wasOpen) return;
      li.dataset.open = "1";
      li.classList.add("dash-cal-active");
      const circuit = circuits[li.dataset.gp];
      const calItem = cal.find(x => x.name === li.dataset.gp);
      if (!circuit) return;
      const detail = document.createElement("li");
      detail.className = "dash-circuit-detail";
      detail.innerHTML = renderCircuitDetail(circuit, calItem, teamColor);
      li.after(detail);
    });
  }

  // ---------- Raccourcis viz : affichent la viz DANS le cadre du dashboard ----------
  const vizContainer = document.getElementById("dash-viz");
  const embedHost = document.getElementById("dash-embed-host");
  const embedFrame = document.getElementById("dash-embed-frame");
  const embedTitle = document.getElementById("dash-embed-title");
  const embedOpen = document.getElementById("dash-embed-open");
  const embedBack = document.getElementById("dash-embed-back");
  const standingsCard = document.querySelector(".dash-card--standings");

  let embedResizeObserver = null;

  function fitEmbed() {
    if (!embedFrame || embedHost.hidden) return;
    try {
      const doc = embedFrame.contentDocument;
      if (!doc || !doc.body) return;
      const h = Math.max(
        doc.body.scrollHeight,
        doc.documentElement.scrollHeight
      );
      if (h > 0) embedFrame.style.height = h + "px";
    } catch (e) { /* cross-origin — ne devrait pas arriver (même domaine) */ }
  }

  function showEmbed(item) {
    if (!embedHost || !embedFrame) return;
    // Masque la barre d'onglets + tous les panes
    standingsCard.querySelectorAll(".dash-card-header, .dash-tab-pane").forEach(el => {
      el.dataset.hiddenByEmbed = "1";
      el.style.display = "none";
    });
    embedTitle.textContent = item.title;
    embedOpen.href = item.route + `?lang=${LANG}`;
    embedHost.hidden = false;

    embedFrame.onload = () => {
      fitEmbed();
      // La viz se rend / s'anime après le load : on remesure quelques fois
      [200, 700, 1500, 3000].forEach(t => setTimeout(fitEmbed, t));
      // Suit les changements de taille du contenu (responsive, animations)
      try {
        const win = embedFrame.contentWindow;
        if (embedResizeObserver) embedResizeObserver.disconnect();
        embedResizeObserver = new win.ResizeObserver(() => fitEmbed());
        embedResizeObserver.observe(embedFrame.contentDocument.body);
      } catch (e) { /* ignore */ }
    };
    embedFrame.src = item.route + `?embed=1&lang=${LANG}`;
  }

  function hideEmbed() {
    if (!embedHost) return;
    if (embedResizeObserver) { embedResizeObserver.disconnect(); embedResizeObserver = null; }
    embedHost.hidden = true;
    embedFrame.onload = null;
    embedFrame.src = "about:blank";
    embedFrame.style.height = "";
    standingsCard.querySelectorAll('[data-hidden-by-embed="1"]').forEach(el => {
      el.style.display = "";
      delete el.dataset.hiddenByEmbed;
    });
  }

  // Re-mesure quand la fenêtre du dashboard change de taille
  window.addEventListener("resize", () => fitEmbed());

  if (embedBack) embedBack.addEventListener("click", hideEmbed);

  if (vizContainer && manifestRes.items) {
    const vizItems = manifestRes.items.filter(it => it.category === "viz");
    vizContainer.innerHTML = vizItems.map(it => {
      const disabled = !it.available;
      const cls = `dash-shortcut ${disabled ? 'is-disabled' : ''}`;
      const ariaAttr = disabled ? `aria-disabled="true"` : `role="button" tabindex="0"`;
      return `
        <div class="${cls}" data-viz-id="${it.id}" ${ariaAttr}>
          <span class="dash-shortcut-title">${it.title}</span>
          <span class="dash-shortcut-arrow">${disabled ? '·' : '→'}</span>
        </div>
      `;
    }).join("");

    vizContainer.querySelectorAll(".dash-shortcut:not(.is-disabled)").forEach(el => {
      const item = vizItems.find(it => it.id === el.dataset.vizId);
      if (!item) return;
      el.addEventListener("click", () => showEmbed(item));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showEmbed(item); }
      });
    });
  }
})().catch(err => {
  console.error("Erreur de chargement du dashboard :", err);
  const sub = document.getElementById("dash-subtitle");
  if (sub) sub.textContent = t("header.loadError");
});

function renderTeammateView(team, filter, teamColor) {
  const color = teamColor(team.team);
  const drivers = team.drivers || [];
  if (drivers.length < 2) return `<p class="dash-duel-empty">${t("tm.singleDriver")}</p>`;
  const [dA, dB] = drivers; // ordre alpha (fixé par le builder)
  const shortA = shortName(dA);
  const shortB = shortName(dB);

  // Filtrage des sessions
  const sessions = (team.sessions || []).filter(s =>
    filter === "ALL" ? true : s.type === filter
  );

  // H2H affiché : recalculé pour le filtre (sur les sessions filtrées)
  let winsA = 0, winsB = 0;
  sessions.forEach(s => {
    if (s.fastest === dA) winsA++;
    else if (s.fastest === dB) winsB++;
  });

  const q3A = team.q3Count[dA] || 0;
  const q3B = team.q3Count[dB] || 0;

  // Timeline SVG : axe horizontal centré, dots positionnés selon gap signé
  // gap signé = (tB - tA) → si fastest=A, gap_signed = -gap (à gauche), si fastest=B, gap_signed = +gap (à droite)
  const points = sessions.map(s => {
    const signed = s.fastest === dA ? -s.gapSec : (s.fastest === dB ? s.gapSec : 0);
    return { ...s, signed };
  });

  const maxAbs = Math.max(0.5, ...points.map(p => Math.abs(p.signed)));
  // Arrondi pour graduations propres : ceil au 0.5s supérieur
  const axisMax = Math.ceil(maxAbs * 2) / 2;

  const W = 720, H = 130, PAD_T = 28, PAD_B = 28, PAD_X = 30;
  const innerW = W - 2 * PAD_X;
  const yMid = PAD_T + (H - PAD_T - PAD_B) / 2;
  const xFor = v => PAD_X + ((v + axisMax) / (2 * axisMax)) * innerW;

  // Graduations : -axisMax, -axisMax/2, 0, +axisMax/2, +axisMax (5 ticks)
  const ticks = [-axisMax, -axisMax/2, 0, axisMax/2, axisMax];

  const dotsSvg = points.map(p => {
    const cx = xFor(p.signed);
    const cy = yMid;
    const info = escapeAttr(buildTooltipPayload(p, dA, dB, color));
    if (p.type === "Q") {
      // Cercle plein pour Qualifs
      return `<circle cx="${cx}" cy="${cy}" r="6.5" fill="${color}" stroke="${color}" stroke-width="1.5" class="dash-tl-dot" data-info="${info}"/>`;
    }
    // Losange creux pour Sprint Qualifs (via polygon — pas de rotate, plus fiable)
    const s = 7.5;
    return `<polygon points="${cx},${cy-s} ${cx+s},${cy} ${cx},${cy+s} ${cx-s},${cy}" fill="none" stroke="${color}" stroke-width="2.2" class="dash-tl-dot" data-info="${info}"/>`;
  }).join("");

  const ticksSvg = ticks.map(t => {
    const x = xFor(t);
    const label = t === 0 ? "0" : (t > 0 ? `+${t.toFixed(1)}s` : `${t.toFixed(1)}s`);
    return `
      <line x1="${x}" x2="${x}" y1="${yMid-8}" y2="${yMid+8}" stroke="${t===0?'#5a6275':'#3a4150'}" stroke-width="${t===0?1.5:1}"/>
      <text x="${x}" y="${H-10}" fill="#9aa3b2" font-size="10" text-anchor="middle">${label}</text>
    `;
  }).join("");

  // Score H2H : on choisit la "barre" en fonction du filtre
  const flexA = Math.max(0.01, winsA);
  const flexB = Math.max(0.01, winsB);
  const filterLabel = filter === "Q" ? t("tm.scopeQ") : filter === "SQ" ? t("tm.scopeSQ") : t("tm.scopeAll");

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
        <line x1="${PAD_X}" x2="${W-PAD_X}" y1="${yMid}" y2="${yMid}" stroke="#3a4150" stroke-width="1"/>
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

function escapeAttr(s) { return s.replace(/"/g, "&quot;"); }

function attachTimelineHover() {
  const tooltip = document.getElementById("dash-tl-tooltip");
  if (!tooltip) return;
  document.querySelectorAll(".dash-tl-dot").forEach(el => {
    el.addEventListener("mouseenter", (e) => {
      let info;
      try { info = JSON.parse(el.getAttribute("data-info")); } catch { return; }
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

function renderDuelPanel(a, b, teamColor) {
  const cA = teamColor(a.team), cB = teamColor(b.team);
  const progA = a.progress || [];
  const progB = b.progress || [];
  const n = Math.min(progA.length, progB.length);

  // Métriques calculées
  const totalA = a.points, totalB = b.points;
  const gap = totalA - totalB;
  const avgA = n ? totalA / n : 0;
  const avgB = n ? totalB / n : 0;
  const bestA = progA.length ? Math.max(...progA.map(p => p.gain)) : 0;
  const bestB = progB.length ? Math.max(...progB.map(p => p.gain)) : 0;
  const scoredA = progA.filter(p => p.gain > 0).length;
  const scoredB = progB.filter(p => p.gain > 0).length;

  // Duel direct par GP
  let winsA = 0, winsB = 0, ties = 0;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const ga = progA[i].gain, gb = progB[i].gain;
    let winner = "tie";
    if (ga > gb) { winsA++; winner = "a"; }
    else if (gb > ga) { winsB++; winner = "b"; }
    else { ties++; }
    rows.push({ gp: progA[i].shortName, ga, gb, winner, diff: ga - gb });
  }

  // Helper : barre comparative pour une métrique
  // valA et valB peuvent être 0 simultanément (ex. wins).
  function metricBar(label, valA, valB, fmt, note) {
    fmt = fmt || (v => v);
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
        ${total > 0 ? `
        <div class="dash-duel-metric-pct">
          <span>${pctA.toFixed(0)}%</span>
          <span>${pctB.toFixed(0)}%</span>
        </div>` : ""}
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
  const W = 480, H = 160, PAD_L = 28, PAD_R = 12, PAD_T = 12, PAD_B = 22;
  const cumDiff = [];
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += progA[i].gain - progB[i].gain;
    cumDiff.push(acc);
  }
  const maxAbs = Math.max(1, ...cumDiff.map(v => Math.abs(v)));
  const xStep = (W - PAD_L - PAD_R) / Math.max(1, n - 1);
  const yMid = (H - PAD_T - PAD_B) / 2 + PAD_T;
  const ySpan = (H - PAD_T - PAD_B) / 2;
  const yScale = v => yMid - (v / maxAbs) * ySpan;
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
        ${gap === 0 ? "=" : (gap > 0 ? `+${gap}` : `${gap}`)}
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
      ${metricBar(t("duel.edge"), winsA, winsB,
        undefined,
        t("duel.edgeNote", { a: a.shortName, b: b.shortName }))}
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
        ${cumDiff.map((v, i) => {
          const x = PAD_L + i * xStep;
          const y = yScale(v);
          return `
            <circle cx="${x}" cy="${y}" r="3" fill="${lineColor}"/>
            <text x="${x}" y="${y - 7}" fill="${lineColor}" font-size="10" text-anchor="middle">${v > 0 ? '+' + v : v}</text>
          `;
        }).join("")}
        <!-- labels GP -->
        ${progA.slice(0, n).map((p, i) => `
          <text x="${PAD_L + i * xStep}" y="${H - 6}" fill="#9aa3b2" font-size="10" text-anchor="middle">${p.shortName}</text>
        `).join("")}
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
        ${rows.map(r => `
          <tr>
            <td>${r.gp}</td>
            <td class="t-num ${r.winner === 'a' ? 'dash-duel-cell-win' : 'muted'}" ${r.winner === 'a' ? `style="color:${cA}"` : ""}><strong>${r.ga}</strong></td>
            <td class="t-num ${r.winner === 'b' ? 'dash-duel-cell-win' : 'muted'}" ${r.winner === 'b' ? `style="color:${cB}"` : ""}><strong>${r.gb}</strong></td>
            <td class="t-num muted">${r.diff > 0 ? '+' + r.diff : r.diff}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderCircuitDetail(circuit, calItem, teamColor) {
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

  const specsHtml = specs.map(([k, v]) =>
    `<div class="dash-circuit-spec"><span class="dash-circuit-spec-k">${k}</span><span class="dash-circuit-spec-v">${v}</span></div>`
  ).join("");

  // Record du tour (saison source du tracé)
  const recordHtml = circuit.lapRecord
    ? `<div class="dash-circuit-record">${t("circuit.fastestLap", { year: circuit.lapRecord.year, driver: circuit.lapRecord.driver, time: circuit.lapRecord.time })}</div>`
    : "";

  // Vainqueur de la saison en cours (si GP joué) — vient du calendrier dashboard
  const winner2026 = calItem && calItem.winner
    ? `<div class="dash-circuit-winner-2026">${t("circuit.winner", { season: 2026, color: teamColor(calItem.winner.team), name: calItem.winner.shortName, team: calItem.winner.team })}</div>`
    : "";

  // Vainqueurs historiques
  const pastHtml = (circuit.pastWinners || []).map(w => `
    <div class="dash-circuit-past-row">
      <span class="dash-circuit-past-year">${w.year}</span>
      <span class="dash-circuit-past-driver" style="color:${teamColor(w.team)}">${w.driver}</span>
      <span class="dash-circuit-past-team">${w.team}</span>
    </div>
  `).join("");

  return `
    <div class="dash-circuit-detail-inner">
      <div class="dash-circuit-left">
        ${trackSvg}
      </div>
      <div class="dash-circuit-right">
        <div class="dash-circuit-specs">${specsHtml}</div>
        ${recordHtml}
        ${winner2026}
        ${pastHtml ? `
          <div class="dash-circuit-past">
            <div class="dash-circuit-past-title">${t("circuit.recentWinners")}</div>
            ${pastHtml}
          </div>` : ""}
      </div>
    </div>
  `;
}

function renderDriverDetail(driver, teamColor) {
  const color = teamColor(driver.team);
  const progress = driver.progress || [];
  // Mini sparkline SVG (cumul de points)
  const W = 240, H = 60, PAD = 4;
  let sparkSvg = "";
  if (progress.length >= 2) {
    const ys = progress.map(p => p.cumulative);
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
        <circle cx="${pts[pts.length-1].split(",")[0]}"
                cy="${pts[pts.length-1].split(",")[1]}"
                r="3" fill="${color}"/>
      </svg>
    `;
  }
  // Tableau GP par GP (gain + cumul)
  const gpRows = progress.map((p, i) => `
    <tr>
      <td class="t-rank muted">${i + 1}</td>
      <td>${p.shortName}</td>
      <td class="t-num ${p.gain > 0 ? 'positive' : 'muted'}">${p.gain > 0 ? '+' + p.gain : (p.gain === 0 ? '0' : p.gain)}</td>
      <td class="t-num"><strong>${p.cumulative}</strong></td>
    </tr>
  `).join("");
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
          <div><span class="dash-mini-label">${t("driver.deltaLast")}</span><span class="dash-mini-val ${driver.deltaLastGp > 0 ? 'positive' : 'muted'}">${driver.deltaLastGp > 0 ? '+' + driver.deltaLastGp : driver.deltaLastGp}</span></div>
          <div><span class="dash-mini-label">${t("driver.leaderGap")}</span><span class="dash-mini-val muted">${driver.leaderGap === 0 ? '—' : driver.leaderGap}</span></div>
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

function formatCountdown(diffMs) {
  if (diffMs <= 0) return t("countdown.ongoing");
  const totalMin = Math.floor(diffMs / 60_000);
  const days = Math.floor(totalMin / (24 * 60));
  const hours = Math.floor((totalMin - days * 24 * 60) / 60);
  if (days >= 7) return t("countdown.days", { days });
  if (days >= 1) return t("countdown.dayHour", { days, hours: String(hours).padStart(2, "0") });
  const minutes = totalMin - days * 24 * 60 - hours * 60;
  return t("countdown.hourMin", { hours: String(hours).padStart(2, "0"), min: String(minutes).padStart(2, "0") });
}

function shortName(full) {
  const parts = (full || "").trim().split(/\s+/);
  if (parts.length < 2) return full;
  return parts[0][0] + ". " + parts.slice(1).join(" ");
}

function dateLocale() { return LANG === "en" ? "en-GB" : "fr-FR"; }

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(dateLocale(), { day: "numeric", month: "short" });
}

function formatDateShort(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  // ex. "08/03"
  return d.toLocaleDateString(dateLocale(), { day: "2-digit", month: "2-digit" });
}
