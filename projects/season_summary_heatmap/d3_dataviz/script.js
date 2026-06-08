// v2 — Heatmap D3 (D3 v7) - Version Leaders
// Hypothèse de structure : d3_dataviz/ à côté du CSV à la racine du projet
// Utilise le CSV leaders avec métriques avancées

// Mode embed (?embed=1) : intégration dans un iframe du dashboard.
const HM_PARAMS = new URLSearchParams(window.location.search);
if (HM_PARAMS.get("embed") === "1") {
  document.documentElement.classList.add("embed-mode");
}

// ---------- i18n (langue partagée avec le dashboard) ----------
const HM_LANG = HM_PARAMS.get("lang") || localStorage.getItem("bf1-lang") || "fr";
const HM_STR = {
  fr: {
    "hm.title": "F1 {season} — Heatmap des points par Grand Prix",
    "hm.sub": "X : <em>EventName</em> • Y : <em>Driver</em> (tri par TotalPoints) • Couleur : <em>Points</em>",
    "hm.footer": "Données : CSV enrichi {season} exporté depuis Fast-F1 • Version D3 v1 (baseline)",
    "hm.bigTitle": "Formule 1 {season}, course après course",
    "hm.intro1": "Cette heatmap suit le championnat {season} en cours : les points marqués par chaque pilote",
    "hm.intro2": "à chaque Grand Prix, enrichis au survol par les détails clés de la course et de la saison.",
    "hm.axisX": "Grand Prix",
    "hm.axisY": "Pilote",
    "hm.team": "Équipe",
    "hm.pointsGp": "Points (GP)",
    "hm.seasonTotal": "Total saison",
    "hm.rank": "Rang",
    "hm.cumulative": "Cumul",
    "hm.average": "Moyenne",
    "hm.avg5": "Moyenne 5 GP",
    "hm.podiums": "Podiums",
    "hm.gridGain": "Gain grille",
    "hm.ptsPerGp": "pts/GP",
    "hm.positions": "positions",
    "hm.sprintSuffix": "sprint",
    "hm.gp": "Grand Prix",
    "hm.gridFinish": "Grille / Arrivée",
    "hm.pts": "pts",
    "hm.loadError": "Impossible de charger le CSV leaders.",
  },
  en: {
    "hm.title": "F1 {season} — Points Heatmap by Grand Prix",
    "hm.sub": "X: <em>EventName</em> • Y: <em>Driver</em> (sorted by TotalPoints) • Color: <em>Points</em>",
    "hm.footer": "Data: enriched {season} CSV exported from Fast-F1 • D3 v1 (baseline)",
    "hm.bigTitle": "Formula 1 {season}, race after race",
    "hm.intro1": "This heatmap tracks the ongoing {season} season: points scored by each driver",
    "hm.intro2": "at each Grand Prix, enriched on hover with key race and season details.",
    "hm.axisX": "Grand Prix",
    "hm.axisY": "Driver",
    "hm.team": "Team",
    "hm.pointsGp": "Points (race)",
    "hm.seasonTotal": "Season total",
    "hm.rank": "Rank",
    "hm.cumulative": "Cumulative",
    "hm.average": "Average",
    "hm.avg5": "5-race average",
    "hm.podiums": "Podiums",
    "hm.gridGain": "Grid gain",
    "hm.ptsPerGp": "pts/race",
    "hm.positions": "positions",
    "hm.sprintSuffix": "sprint",
    "hm.gp": "Grand Prix",
    "hm.gridFinish": "Grid / Finish",
    "hm.pts": "pts",
    "hm.loadError": "Failed to load the leaders CSV.",
  },
}[HM_LANG] || {};

function htr(key, vars) {
  let s = HM_STR[key] != null ? HM_STR[key] : key;
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}

document.documentElement.lang = HM_LANG;
document.querySelectorAll("[data-i18n]").forEach(el => {
  el.innerHTML = htr(el.dataset.i18n, { season: 2026 });
});

const SEASON = 2026;
const DATA_URL = "f1_2026_leaders_heatmap.csv";

const container = d3.select("#chart");
const tooltip = d3.select("#tooltip");

// Palette séquentielle proche "YlOrRd"
const color = d3.scaleSequential(d3.interpolateYlOrRd);

// Dimensions responsives (hauteur basée sur #drivers, largeur sur viewport)
function render(data, driverAvgPoints) {
  container.selectAll("svg").remove();

  const events = Array.from(new Set(data.map(d => d.EventName)));

  const totals = d3.rollup(
    data,
    v => d3.max(v, d => d.TotalPoints),
    d => d.Driver
  );
  const drivers = Array.from(totals.entries())
    .sort((a, b) => d3.descending(a[1], b[1]) || d3.ascending(a[0], b[0]))
    .map(d => d[0]);

  const maxWidth = Math.min(1200, container.node().getBoundingClientRect().width - 24);
  const cellW = Math.max(12, Math.floor((maxWidth - 180) / events.length));
  const cellH = Math.max(12, 24);

  // ⬇️ MODIF ICI : plus d’espace entre jauge et heatmap
  const margin = { top: 180, right: 20, bottom: 200, left: 180 };

  const width = margin.left + margin.right + cellW * events.length;
  const height = margin.top + margin.bottom + cellH * drivers.length;

  const x = d3.scaleBand().domain(events).range([margin.left, width - margin.right]).paddingInner(0.05);
  const y = d3.scaleBand().domain(drivers).range([margin.top, height - margin.bottom]).paddingInner(0.05);

  const maxPoints = 33;
  color.domain([0, maxPoints]);

  const svg = container.append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("width", "100%")
    .attr("height", Math.min(height, 900));

  /* TITRE */
  const headX = margin.left;

  svg.append("text")
    .attr("x", headX)
    .attr("y", 40)
    .attr("text-anchor", "start")
    .attr("fill", "#e6e9f2")
    .attr("font-size", 20)
    .attr("font-weight", "700")
    .text(htr("hm.bigTitle", { season: SEASON }));

  const subtitle = svg.append("text")
    .attr("x", headX)
    .attr("y", 68)
    .attr("text-anchor", "start")
    .attr("fill", "#cfd6e4")
    .attr("font-size", 14)
    .attr("font-weight", "600");

  subtitle.append("tspan")
    .attr("x", headX)
    .attr("dy", 0)
    .text(htr("hm.intro1", { season: SEASON }));

  subtitle.append("tspan")
    .attr("x", headX)
    .attr("dy", 18)
    .text(htr("hm.intro2"));

  /* SÉPARATEUR */
  const sepY = 110;

  svg.append("line")
    .attr("x1", margin.left)
    .attr("x2", width - margin.right)
    .attr("y1", sepY)
    .attr("y2", sepY)
    .attr("stroke", "#3a3f4b")
    .attr("stroke-width", 1)
    .attr("stroke-dasharray", "4,4");

  /* JAUGE */
  drawLegend(svg, {
    x: margin.left,
    y: sepY + 14,
    w: 220,
    h: 10,
    max: maxPoints
  });

  /* AXES */
  const xAxis = g => g
    .attr("transform", `translate(0,${height - margin.bottom + 20})`)
    .attr("class", "axis")
    .call(d3.axisBottom(x).tickSizeOuter(0))
    .selectAll("text")
      .attr("transform", "rotate(-35)")
      .style("text-anchor", "end");

  const yAxis = g => g
    .attr("transform", `translate(${margin.left},0)`)
    .attr("class", "axis")
    .call(d3.axisLeft(y).tickSizeOuter(0))
    .call(g => g.selectAll(".tick text").each(function(driver){
      const row = data.find(d => d.Driver === driver);
      if (row && row.DriverName) d3.select(this).text(row.DriverName);
    }));

  svg.append("g").call(xAxis);
  svg.append("g").call(yAxis);

  /* CELLS */
  const cells = svg.append("g")
    .selectAll("rect")
    .data(data)
    .join("rect")
      .attr("class", "cell")
      .attr("x", d => x(d.EventName))
      .attr("y", d => y(d.Driver))
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("fill", d => color(d.Points ?? 0))
      .on("mousemove", (event, d) => showTooltip(event, d))
      .on("mouseleave", hideTooltip);

  cells
    .on("mouseenter.focus", (event, d) => {
      cells.attr("opacity", c =>
        (c.Driver === d.Driver && c.EventName === d.EventName) ? 1 : 0.25
      );
    })
    .on("mouseleave.focus", () => {
      cells.attr("opacity", 1);
    });

  svg.append("text")
    .attr("x", (margin.left + (width - margin.right)) / 2)
    .attr("y", height - 26)
    .attr("text-anchor", "middle")
    .attr("fill", "#cfd6e4")
    .attr("font-size", 12)
    .text(htr("hm.axisX"));

  svg.append("text")
    .attr("transform", `translate(16, ${(margin.top + (height - margin.bottom)) / 2}) rotate(-90)`)
    .attr("text-anchor", "middle")
    .attr("fill", "#cfd6e4")
    .attr("font-size", 12)
    .text(htr("hm.axisY"));
}

/* === TOOLTIP & HELPERS : STRICTEMENT IDENTIQUES === */
// (inchangé, je ne les recopie pas ici pour ne pas rallonger inutilement)



// Tooltip HTML riche - Version Leaders
function showTooltip(event, d){
  // 1) Remplir le contenu
  const sprintInfo = d.SprintPoints > 0 ? ` (+${d.SprintPoints} ${htr("hm.sprintSuffix")})` : "";
  const finishIcon = d.FinishIcon || "";
  const P = htr("hm.pts");

  tooltip.html(`
    <h3>${d.DriverName} <span style="color:#9aa3b2">(${d.Driver})</span> ${finishIcon}</h3>
    <div class="meta">
      <img src="${safeUrl(d.HeadshotUrl)}" alt="${d.DriverName}">
      <div class="kv">
        <div><b>${htr("hm.team")} :</b> ${d.Team}</div>
        <div><b>${htr("hm.gp")} :</b> ${d.EventNameFull}</div>
        <div><b>${htr("hm.gridFinish")} :</b> ${fmtPos(d.GridPosition)} / ${fmtPos(d.FinishPosition)}</div>
        <div><b>${htr("hm.pointsGp")} :</b> ${d.Points}${sprintInfo}</div>
        <div><b>${htr("hm.seasonTotal")} :</b> ${d.TotalPoints} • <b>${htr("hm.rank")} :</b> ${d.RankLabel ?? ""}</div>
        <div><b>${htr("hm.cumulative")} :</b> ${d.CumulativePoints} ${P} • ${htr("hm.average")} : ${d.AvgPointsToDate?.toFixed(1)} ${htr("hm.ptsPerGp")}</div>
        <div><b>${htr("hm.avg5")} :</b> ${d.Last5Avg?.toFixed(1)} ${P} • ${htr("hm.podiums")} : ${(d.PodiumRate*100)?.toFixed(0)}%</div>
        <div><b>${htr("hm.gridGain")} :</b> ${d.GridGain >= 0 ? "+" : ""}${d.GridGain?.toFixed(1)} ${htr("hm.positions")}</div>
      </div>
    </div>
  `);

  // 2) Rendre visible pour pouvoir mesurer
  tooltip.style("opacity", 1);

  // 3) Calculer une position qui ne sort pas de l'écran (clamp)
  const OFFSET = 16;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let x = event.clientX + OFFSET;
  let y = event.clientY + OFFSET;

  const rect = tooltip.node().getBoundingClientRect();

  if (x + rect.width > vw - 8) {
    x = event.clientX - rect.width - OFFSET;
  }
  if (y + rect.height > vh - 8) {
    y = vh - rect.height - 8;
  }
  if (x < 8) x = 8;
  if (y < 8) y = 8;

  tooltip.style("left", `${x}px`).style("top", `${y}px`);
}
function hideTooltip(){
  tooltip.style("opacity", 0);
}

// Légende couleur horizontale
function drawLegend(svg, {x, y, w, h, max}){
  const grd = svg.append("defs")
    .append("linearGradient")
      .attr("id", "lg")
      .attr("x1", "0%").attr("x2", "100%")
      .attr("y1", "0%").attr("y2", "0%");
  const stops = d3.range(0, 1.0001, 0.1);
  grd.selectAll("stop")
    .data(stops)
    .join("stop")
      .attr("offset", d => `${d*100}%`)
      .attr("stop-color", d => d3.interpolateYlOrRd(d));

  svg.append("rect")
    .attr("x", x).attr("y", y).attr("width", w).attr("height", h)
    .attr("fill", "url(#lg)").attr("stroke", "#2a2f3a");

  const s = d3.scaleLinear().domain([0, max || 1]).range([x, x + w]);
  const axis = d3.axisBottom(s).ticks(4).tickSize(4);
  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0, ${y + h})`)
    .call(axis);
}

// Utilitaires
function fmtPos(v){
  if (v == null || v === "" || Number.isNaN(+v)) return "–";
  const n = +v;
  if (n === 1) return "1";
  if (n === 2) return "2";
  if (n === 3) return "3";
  return `${n}`;
}

function safeUrl(u){
  if (!u || String(u).toLowerCase() === "nan" || String(u).toLowerCase() === "none") return "";
  return u;
}

  // Chargement CSV + cast des types requis
d3.csv(DATA_URL, d3.autoType).then(rows => {
  // Garantir les colonnes numériques
  rows.forEach(r => {
    r.Points = +r.Points || 0;
    r.SprintPoints = +r.SprintPoints || 0;
    r.TotalPoints = +r.TotalPoints || 0;
    r.GridPosition = r.GridPosition != null ? +r.GridPosition : null;
    r.FinishPosition = r.FinishPosition != null ? +r.FinishPosition : null;
    r.Rank = r.Rank != null ? +r.Rank : null;
    r.CumulativePoints = +r.CumulativePoints || 0;
    r.AvgPointsToDate = +r.AvgPointsToDate || 0;
    r.Last5Avg = +r.Last5Avg || 0;
    r.PodiumRate = +r.PodiumRate || 0;
    r.GridGain = +r.GridGain || 0;
  });

  // Calculer les moyennes de points par pilote pour détecter les surprises
  const driverAvgPoints = d3.rollup(
    rows,
    v => d3.mean(v, d => d.Points),
    d => d.Driver
  );

  render(rows, driverAvgPoints);  // Re-render à resize
  window.addEventListener("resize", () => render(rows, driverAvgPoints));
}).catch(err => {
  console.error("Erreur chargement CSV :", err);
  container.append("p").text(htr("hm.loadError"));
});
