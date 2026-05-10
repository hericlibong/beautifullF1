/* Beautiful F1 — Dashboard 2026
 * Charge data/dashboard_2026.json + assets/teams.json et peuple la page.
 */

(async function () {
  const [dashRes, teamsRes, manifestRes] = await Promise.all([
    fetch("data/dashboard_2026.json").then(r => r.json()),
    fetch("assets/teams.json").then(r => r.json()),
    fetch("assets/manifest.json").then(r => r.json()),
  ]);

  const teams = teamsRes.teams || {};
  const teamColor = name => (teams[name] && teams[name].color) || teamsRes.fallbackColor;

  // ---------- Header ----------
  const lastGpDate = formatDate(dashRes.lastGp.date);
  document.getElementById("dash-subtitle").textContent =
    `Dernier GP joué : ${dashRes.lastGp.shortName} (${lastGpDate}) • ${dashRes.kpis.raceCount} / ${dashRes.kpis.totalRaces} GP`;

  // ---------- KPI ----------
  const kpiContainer = document.getElementById("dash-kpis");
  const k = dashRes.kpis;
  const kpis = [
    {
      label: "Leader actuel",
      value: shortName(k.leader.name),
      sub: `${k.leader.points} pts • ${k.leader.team}`,
      color: teamColor(k.leader.team),
    },
    {
      label: "Écart leader / 2e",
      value: `+${k.leaderGap}`,
      sub: `vs ${shortName(k.second.name)} (${k.second.points} pts)`,
    },
    {
      label: "Dernier vainqueur",
      value: shortName(k.lastWinner.name),
      sub: `${k.lastWinner.gp} • ${k.lastWinner.team}`,
      color: teamColor(k.lastWinner.team),
    },
    {
      label: "Prochain GP",
      countdown: dashRes.nextGp ? dashRes.nextGp.date : null,
      gpName: dashRes.nextGp ? dashRes.nextGp.shortName : "—",
      sub: dashRes.nextGp
        ? `${dashRes.nextGp.shortName} • ${formatDate(dashRes.nextGp.date)}${dashRes.nextGp.isSprint ? " • Sprint" : ""}`
        : "Saison terminée",
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
            <th class="t-rank">#</th>
            <th class="t-name">Pilote</th>
            <th class="t-team">Écurie</th>
            <th class="t-num">Pts</th>
            <th class="t-num">Δ</th>
            <th class="t-num t-gap">Écart</th>
          </tr>
        </thead>
        <tbody>${renderDriverRows(visible)}</tbody>
      `;
      const card = driversTable.closest(".dash-card");
      let toggle = card.querySelector(".dash-table-toggle");
      if (allDrivers.length > TOP_N) {
        if (!toggle) {
          toggle = document.createElement("button");
          toggle.type = "button";
          toggle.className = "dash-table-toggle";
          card.appendChild(toggle);
          toggle.addEventListener("click", () => renderTable(!toggle.dataset.expanded));
        }
        toggle.dataset.expanded = expanded ? "1" : "";
        toggle.textContent = expanded
          ? `▲ Voir le top ${TOP_N}`
          : `▼ Voir les ${allDrivers.length} pilotes`;
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
          <th class="t-rank">#</th>
          <th class="t-name">Écurie</th>
          <th class="t-num">Pts</th>
          <th class="t-num">Δ</th>
          <th class="t-num t-gap">Écart</th>
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

  // ---------- Calendrier ----------
  const calContainer = document.getElementById("dash-calendar");
  const calProgress = document.getElementById("dash-calendar-progress");
  if (calContainer && dashRes.calendar) {
    const cal = dashRes.calendar;
    const played = cal.filter(c => c.status === "played").length;
    if (calProgress) calProgress.textContent = `${played} / ${cal.length} GP`;

    calContainer.innerHTML = cal.map(c => {
      const statusIcon =
        c.status === "played" ? "✓" :
        c.status === "next"   ? "▶" :
        "·";
      const winnerHtml = c.winner
        ? `<span class="dash-cal-winner" style="color:${teamColor(c.winner.team)}">${c.winner.shortName}</span>`
        : (c.status === "next" ? `<span class="dash-cal-next-tag">Prochain</span>` : "");
      const sprintBadge = c.isSprint ? `<span class="dash-cal-sprint" title="Week-end sprint">S</span>` : "";
      return `
        <li class="dash-cal-item dash-cal-${c.status}">
          <span class="dash-cal-round">${c.round}</span>
          <span class="dash-cal-status">${statusIcon}</span>
          <span class="dash-cal-name">${c.shortName}${sprintBadge}</span>
          <span class="dash-cal-date">${formatDateShort(c.date)}</span>
          ${winnerHtml}
        </li>
      `;
    }).join("");

  }

  // ---------- Raccourcis viz (cartes compactes) ----------
  const vizContainer = document.getElementById("dash-viz");
  if (vizContainer && manifestRes.items) {
    const vizItems = manifestRes.items.filter(it => it.category === "viz");
    vizContainer.innerHTML = vizItems.map(it => {
      const disabled = !it.available;
      const tag = disabled ? "div" : "a";
      const hrefAttr = disabled ? "" : `href="${it.route}"`;
      const cls = `dash-shortcut ${disabled ? 'is-disabled' : ''}`;
      const ariaAttr = disabled ? `aria-disabled="true"` : "";
      return `
        <${tag} class="${cls}" ${hrefAttr} ${ariaAttr}>
          <span class="dash-shortcut-title">${it.title}</span>
          <span class="dash-shortcut-arrow">${disabled ? '·' : '→'}</span>
        </${tag}>
      `;
    }).join("");
  }
})().catch(err => {
  console.error("Erreur de chargement du dashboard :", err);
  const sub = document.getElementById("dash-subtitle");
  if (sub) sub.textContent = "Erreur de chargement des données.";
});

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
          <div><span class="dash-mini-label">Rang</span><span class="dash-mini-val">${driver.rank}</span></div>
          <div><span class="dash-mini-label">Points</span><span class="dash-mini-val">${driver.points}</span></div>
          <div><span class="dash-mini-label">Δ dernier GP</span><span class="dash-mini-val ${driver.deltaLastGp > 0 ? 'positive' : 'muted'}">${driver.deltaLastGp > 0 ? '+' + driver.deltaLastGp : driver.deltaLastGp}</span></div>
          <div><span class="dash-mini-label">Écart leader</span><span class="dash-mini-val muted">${driver.leaderGap === 0 ? '—' : driver.leaderGap}</span></div>
        </div>
        ${sparkSvg}
      </div>
      <table class="dash-table dash-driver-progress">
        <thead>
          <tr>
            <th class="t-rank">#</th>
            <th>Grand Prix</th>
            <th class="t-num">Gain</th>
            <th class="t-num">Cumul</th>
          </tr>
        </thead>
        <tbody>${gpRows}</tbody>
      </table>
    </div>
  `;
}

function formatCountdown(diffMs) {
  if (diffMs <= 0) return "🏁 En cours";
  const totalMin = Math.floor(diffMs / 60_000);
  const days = Math.floor(totalMin / (24 * 60));
  const hours = Math.floor((totalMin - days * 24 * 60) / 60);
  if (days >= 7) return `${days} jours`;
  if (days >= 1) return `${days}j ${String(hours).padStart(2, "0")}h`;
  const minutes = totalMin - days * 24 * 60 - hours * 60;
  return `${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m`;
}

function shortName(full) {
  const parts = (full || "").trim().split(/\s+/);
  if (parts.length < 2) return full;
  return parts[0][0] + ". " + parts.slice(1).join(" ");
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function formatDateShort(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  // ex. "08/03"
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}
