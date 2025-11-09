// ====== chemins & constantes
const CSV_PATH = "../f1_2025_wdc_projection_round14.csv";
const ZONES_ORDER = ["Safe","Warning","Danger","Critical","LastChance","Eliminated"];
const ZONE_COLORS = {
  Safe:"#2ecc71", Warning:"#f1c40f", Danger:"#e67e22",
  Critical:"#e74c3c", LastChance:"#9b59b6", Eliminated:"#95a5a6"
};

// ====== éléments UI
const leaderSlider = document.getElementById("leaderPct");
const leaderLbl    = document.getElementById("leaderPctValue");
const pilotSlider  = document.getElementById("pilotPct");
const pilotLbl     = document.getElementById("pilotPctValue");
const pilotSelect  = document.getElementById("pilotSelect");
const presetsWrap  = document.getElementById("presets");
const zoneFilters  = document.getElementById("zoneFilters");
const summaryBox   = document.getElementById("summary");

// ====== dimensions chart
const W = 980, H0 = 560, M = {t:28, r:40, b:40, l:180};

// ====== état global
let RAW = [];          // csv brut
let DRIVERS = [];      // {driver, risk_zone, points, max_points, remaining, leader_points, leader_remaining, leader_name}
let FILTER_ZONES = new Set(ZONES_ORDER); // par défaut: tout
let SCENARIO = [];     // résultat calculé
let svg, x, y;

// ====== helpers
const fmtPct = n => `${(Math.round(n*10)/10).toFixed(1)}%`;
const fmtPts = n => `${(Math.round(n*10)/10).toFixed(1)}`;
const leaderOf = rows => rows.reduce((acc, r) => (r.points > acc.points ? r : acc), rows[0]);

// ====== UI bindings
function bindUI(){
  // presets → déplacent le slider leader
  presetsWrap.querySelectorAll('input[name="preset"]').forEach(r => {
    r.addEventListener("change", () => {
      leaderSlider.value = r.value;
      leaderLbl.textContent = `${r.value}%`;
      update();
    });
  });

  // sliders
  leaderSlider.addEventListener("input", e => { leaderLbl.textContent = `${e.target.value}%`; update(); });
  pilotSlider .addEventListener("input", e => { pilotLbl.textContent  = `${e.target.value}%`; update(); });

  // pilote
  pilotSelect.addEventListener("change", update);

  // filtres zone
  ZONES_ORDER.forEach(z => {
    const id = `zone-${z}`;
    const lab = document.createElement("label");
    const cb  = document.createElement("input");
    cb.type="checkbox"; cb.id=id; cb.value=z; cb.checked = true;
    cb.addEventListener("change", () => {
      if (cb.checked) FILTER_ZONES.add(z); else FILTER_ZONES.delete(z);
      update();
    });
    lab.append(cb, document.createTextNode(z));
    zoneFilters.appendChild(lab);
  });
}

// ====== init chart
function initChart(){
  svg = d3.select("#chart").append("svg")
    .attr("viewBox", [0,0,W,H0])
    .attr("aria-label","Scenario margin vs leader");

  // scales initiales (domaines mis à jour dans render)
  x = d3.scaleLinear().range([M.l, W - M.r]);
  y = d3.scaleBand().range([M.t, H0 - M.b]).padding(0.2);

  // axes containers
  svg.append("g").attr("class","axis axis-x");
  svg.append("g").attr("class","axis axis-y").attr("transform", `translate(${M.l},0)`);

  // règle 0
  svg.append("line").attr("class","rule0").attr("y1", M.t).attr("y2", H0 - M.b);
}

// ====== data prep (depuis ton Observable “Cellule 2”)
function prepareDrivers(rows){
  const base = rows.map(d => ({
    driver: d.driver,
    risk_zone: d.risk_zone,
    points: +d.points,
    max_points: +d.max_points
  }));
  const lead = leaderOf(base);
  return base.map(r => ({
    ...r,
    remaining: Math.max(0, r.max_points - r.points),
    leader_points: lead.points,
    leader_remaining: Math.max(0, lead.max_points - lead.points),
    leader_name: lead.driver
  }));
}

// ====== logique scénario (inspirée de tes Cellules 7–9)
function computeScenario(){
  // paramètres
  const leaderPct = Number(leaderSlider.value) / 100;
  const pilotPct  = Number(pilotSlider.value)  / 100;
  const chosen    = pilotSelect.value;

  // filtrage zones
  const filtered = DRIVERS.filter(d => FILTER_ZONES.has(d.risk_zone));

  // leader (global, mais on garde la compat fallback si filtrage l’exclut)
  const globalLeader = leaderOf(DRIVERS);
  const leaderRow = filtered.find(d => d.driver === globalLeader.driver) || globalLeader;

  const leaderFinal = leaderRow.leader_points + leaderRow.leader_remaining * leaderPct;

  const out = filtered.map(d => {
    const share = (d.driver === chosen) ? pilotPct : 1.0; // les autres “parfaits” par défaut
    const pilotFinal = d.points + d.remaining * share;
    const margin = pilotFinal - leaderFinal; // >0 => passe
    return {
      driver: d.driver,
      risk_zone: d.risk_zone,
      points: d.points,
      remaining: d.remaining,
      leader_name: leaderRow.leader_name,
      leaderFinal, pilotFinal, margin,
      pass: margin > 0
    };
  });

  // tri marge décroissante
  out.sort((a,b) => b.margin - a.margin);
  return out;
}

// ====== rendu
function render(){
  SCENARIO = computeScenario();

  // hauteur selon nombre de lignes
  const H = Math.max(240, 26 * SCENARIO.length + 80);
  svg.attr("viewBox", [0,0,W,H]);
  y.range([M.t, H - M.b]).domain(SCENARIO.map(d => d.driver));

  // x symétrique autour de 0
  const maxAbs = Math.max(1, d3.max(SCENARIO, d => Math.abs(d.margin)));
  x.domain([-maxAbs, maxAbs]);

  // axe x
  svg.select(".axis-x")
    .attr("transform", `translate(0,${H - M.b})`)
    .call(d3.axisBottom(x).ticks(6).tickFormat(d => d));

  // axe y (labels pilotes)
  svg.select(".axis-y")
    .call(d3.axisLeft(y).tickSize(0))
    .selectAll("text")
    .attr("class","driver-label");

  // règle 0
  svg.select(".rule0")
    .attr("x1", x(0)).attr("x2", x(0));

  // data join
  const g = svg.selectAll("g.row").data(SCENARIO, d => d.driver);
  const gEnter = g.enter().append("g").attr("class","row");

  // barres
  gEnter.append("rect").attr("class","bar");
  g.select(".bar").interrupt();
  g.merge(gEnter).select(".bar")
    .attr("y", d => y(d.driver))
    .attr("x", d => x(Math.min(0, d.margin)))
    .attr("height", y.bandwidth())
    .transition().duration(200)
    .attr("width", d => Math.abs(x(d.margin) - x(0)))
    .attr("fill", d => d.pass ? ZONE_COLORS.Safe : ZONE_COLORS.Critical)
    .selection()
    .append("title")
      .text(d => `${d.driver}
${d.pass ? "✅ Passe" : "❌ Ne passe pas"}
Marge: ${fmtPts(d.margin)} pts
Scénario pilote: ${fmtPts(d.pilotFinal)} pts
Scénario leader: ${fmtPts(d.leaderFinal)} pts`);

  // badge ✅/❌
  gEnter.append("text").attr("class","badge");
  g.merge(gEnter).select(".badge")
    .attr("y", d => y(d.driver) + y.bandwidth()/2 + 1)
    .attr("x", d => x(d.margin) + (d.margin >= 0 ? 10 : -10))
    .attr("text-anchor", d => d.margin >= 0 ? "start" : "end")
    .text(d => d.pass ? "✅" : "❌");

  // valeur marge
  gEnter.append("text").attr("class","value-label");
  g.merge(gEnter).select(".value-label")
    .attr("y", d => y(d.driver) + y.bandwidth()/2 + 1)
    .attr("x", d => x(d.margin) + (d.margin >= 0 ? -8 : 8))
    .attr("text-anchor", d => d.margin >= 0 ? "end" : "start")
    .text(d => `${fmtPts(d.margin)}`);

  g.exit().remove();

  // résumé
  const nPass = SCENARIO.filter(d => d.pass).length;
  const counts = Object.fromEntries(ZONES_ORDER.map(z => [z,0]));
  SCENARIO.forEach(d => { counts[d.risk_zone] = (counts[d.risk_zone]||0) + 1; });

  summaryBox.innerHTML = `
    <b>${SCENARIO[0]?.leader_name ?? "Leader"}</b> pris à <b>${leaderSlider.value}%</b> des points restants ·
    Pilote <b>${pilotSelect.value}</b> à <b>${pilotSlider.value}%</b> — 
    <b>${nPass}</b> sur <b>${SCENARIO.length}</b> passent ✅
    <span style="color:#9ca3af">| Safe ${counts.Safe||0} · Warning ${counts.Warning||0} · Danger ${counts.Danger||0} · Critical ${counts.Critical||0} · LastChance ${counts.LastChance||0} · Eliminated ${counts.Eliminated||0}</span>
  `;
}

function update(){ render(); }

// ====== bootstrap
(async function main(){
  bindUI();
  initChart();

  RAW = await d3.csv(CSV_PATH, d3.autoType);
  // remplir le select pilote (ordre du CSV)
  RAW.forEach((d,i) => {
    const opt = document.createElement("option");
    opt.value = d.driver; opt.textContent = d.driver;
    if (i === 0) opt.selected = true;
    pilotSelect.appendChild(opt);
  });

  DRIVERS = prepareDrivers(RAW);
  render();
})();
