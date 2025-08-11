// v1 — Heatmap D3 (D3 v7)
// Hypothèse de structure : d3_dataviz/ à côté du CSV à la racine du projet
// Si besoin, dépose le CSV à côté de ces fichiers et remplace DATA_URL par "./f1_2025_flourish_enriched.csv"
const DATA_URL = "f1_2025_flourish_enriched.csv";

const container = d3.select("#chart");
const tooltip = d3.select("#tooltip");

// Palette séquentielle proche "YlOrRd"
const color = d3.scaleSequential(d3.interpolateYlOrRd);

// Dimensions responsives (hauteur basée sur #drivers, largeur sur viewport)
function render(data) {
  container.selectAll("svg").remove();

  // Domaine X : GPs (ordre du CSV pour le premier pilote → calendrier)
  const events = Array.from(new Set(data.map(d => d.EventName)));

  // Domaine Y : pilotes par TotalPoints décroissant
  const totals = d3.rollup(
    data,
    v => d3.max(v, d => d.TotalPoints), // TotalPoints est constant par pilote, max suffit
    d => d.Driver
  );
  const drivers = Array.from(totals.entries())
    .sort((a, b) => d3.descending(a[1], b[1]) || d3.ascending(a[0], b[0]))
    .map(d => d[0]);

  // Marges + tailles
  const maxWidth = Math.min(1200, container.node().getBoundingClientRect().width - 24);
  const cellW = Math.max(12, Math.floor((maxWidth - 180) / events.length));
  const cellH = Math.max(12, 18); // fixe pour lisibilité
  const margin = { top: 40, right: 20, bottom: 70, left: 160 };
  const width =  margin.left + margin.right + cellW * events.length;
  const height = margin.top  + margin.bottom + cellH * drivers.length;

  // Échelles
  const x = d3.scaleBand().domain(events).range([margin.left, width - margin.right]).paddingInner(0.05);
  const y = d3.scaleBand().domain(drivers).range([margin.top, height - margin.bottom]).paddingInner(0.05);

  // Couleurs basées sur Points
  const maxPoints = d3.max(data, d => d.Points);
  color.domain([0, maxPoints || 1]);

  // SVG
  const svg = container
    .append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("width", "100%")
    .attr("height", Math.min(height, 900));

  // Axes
  const xAxis = g => g
    .attr("transform", `translate(0,${height - margin.bottom})`)
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
      // Option : ajouter le rang en suffixe s'il est disponible sur la première ligne du pilote
      const row = data.find(d => d.Driver === driver);
      if (row && row.RankLabel) {
        const t = d3.select(this);
        t.text(`${driver} (${row.RankLabel})`);
      }
    }));

  svg.append("g").call(xAxis);
  svg.append("g").call(yAxis);

  // Cells
  svg.append("g")
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
      .on("mouseleave", hideTooltip)
      .append("title") // fallback natif
        .text(d => `${d.DriverName} • ${d.Team}
${d.EventNameFull}
Grid: ${fmtPos(d.GridPosition)} • Finish: ${fmtPos(d.FinishPosition)}
Points: ${d.Points} • Total: ${d.TotalPoints}`);

  // Légende simple (graduations 0 → max)
  drawLegend(svg, { x: margin.left, y: 8, w: 200, h: 10, max: maxPoints });

  // Titres axes
  svg.append("text")
    .attr("x", (margin.left + (width - margin.right)) / 2)
    .attr("y", height - 26)
    .attr("text-anchor", "middle")
    .attr("fill", "#cfd6e4")
    .attr("font-size", 12)
    .text("Grand Prix (EventName)");

  svg.append("text")
    .attr("transform", `translate(16, ${(margin.top + (height - margin.bottom)) / 2}) rotate(-90)`)
    .attr("text-anchor", "middle")
    .attr("fill", "#cfd6e4")
    .attr("font-size", 12)
    .text("Pilote (Driver)");
}

// Tooltip HTML riche
function showTooltip(event, d){
  const html = `
    <h3>${d.DriverName} <span style="color:#9aa3b2">(${d.Driver})</span></h3>
    <div class="meta">
      <img src="${safeUrl(d.HeadshotUrl)}" alt="${d.DriverName}">
      <div class="kv">
        <div><b>Équipe :</b> ${d.Team}</div>
        <div><b>Grand Prix :</b> ${d.EventNameFull}</div>
        <div><b>Grille / Arrivée :</b> ${fmtPos(d.GridPosition)} / ${fmtPos(d.FinishPosition)}</div>
        <div><b>Points (course) :</b> ${d.Points}</div>
        <div><b>Total saison :</b> ${d.TotalPoints} • <b>Rang :</b> ${d.RankLabel ?? ""}</div>
      </div>
    </div>
  `;
  tooltip
    .style("opacity", 1)
    .html(html)
    .style("left", `${event.clientX + 16}px`)
    .style("top",  `${event.clientY + 16}px`);
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
    r.TotalPoints = +r.TotalPoints || 0;
    r.GridPosition = r.GridPosition != null ? +r.GridPosition : null;
    r.FinishPosition = r.FinishPosition != null ? +r.FinishPosition : null;
    r.Rank = r.Rank != null ? +r.Rank : null;
  });
  render(rows);

  // Re-render à resize
  window.addEventListener("resize", () => render(rows));
}).catch(err => {
  console.error("Erreur chargement CSV :", err);
  container.append("p").text("Impossible de charger le CSV. Vérifie le chemin DATA_URL.");
});
