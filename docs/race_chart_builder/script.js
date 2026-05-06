// F1 2026 — Race Chart Line (D3 v7)
// Source: data/f1_race_chart_fastf1_2026.csv (généré par race_chart_builder_fastf1.py)

const TEAM_COLORS = {
  "McLaren":         "#FF8000",
  "Ferrari":         "#DC0000",
  "Mercedes":        "#27F4D2",
  "Red Bull Racing": "#3671C6",
  "Racing Bulls":    "#6692FF",
  "Williams":        "#64C4FF",
  "Aston Martin":    "#229971",
  "Alpine":          "#FF87BC",
  "Haas F1 Team":    "#B6BABD",
  "Audi":            "#52E252",
  "Cadillac":        "#FFC000",
};
const FALLBACK_COLOR = "#888888";

const META_COLS = new Set(["Pilote", "image", "team", "start"]);

const tooltip = d3.select("body").append("div").attr("class", "tooltip");

d3.csv("./data/f1_race_chart_fastf1_2026.csv").then(rows => {
  if (!rows.length) {
    document.getElementById("chart").innerHTML = "<p>Aucune donnée disponible.</p>";
    return;
  }

  const allColumns = rows.columns;
  const gpColumns = allColumns.filter(c => !META_COLS.has(c));
  const lastGp = gpColumns[gpColumns.length - 1];

  // Pilotes ayant marqué (cumul final > 0)
  const drivers = rows
    .map(r => ({
      name: r.Pilote,
      team: r.team,
      image: r.image,
      color: TEAM_COLORS[r.team] || FALLBACK_COLOR,
      points: gpColumns.map(gp => ({ gp, value: +r[gp] || 0 })),
      total: +r[lastGp] || 0,
    }))
    .filter(d => d.total > 0)
    .sort((a, b) => b.total - a.total);

  render(drivers, gpColumns);
});

function render(drivers, gpColumns) {
  const margin = { top: 20, right: 170, bottom: 40, left: 50 };
  const width  = 1180;
  const height = Math.max(520, drivers.length * 22 + 120);
  const innerW = width  - margin.left - margin.right;
  const innerH = height - margin.top  - margin.bottom;

  const svg = d3.select("#chart")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const xScale = d3.scalePoint()
    .domain(gpColumns)
    .range([0, innerW])
    .padding(0.4);

  const maxY = d3.max(drivers, d => d3.max(d.points, p => p.value)) || 1;
  const yScale = d3.scaleLinear()
    .domain([0, maxY * 1.05])
    .range([innerH, 0])
    .nice();

  // Gridlines horizontales
  g.append("g")
    .attr("class", "grid")
    .selectAll("line")
    .data(yScale.ticks(6))
    .join("line")
      .attr("class", "gridline")
      .attr("x1", 0).attr("x2", innerW)
      .attr("y1", d => yScale(d)).attr("y2", d => yScale(d));

  // Axes
  g.append("g")
    .attr("class", "axis x-axis")
    .attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(xScale).tickSize(0).tickPadding(8))
    .selectAll("text")
      .attr("text-anchor", "end")
      .attr("transform", "rotate(-30)");

  g.append("g")
    .attr("class", "axis y-axis")
    .call(d3.axisLeft(yScale).ticks(6).tickSize(0).tickPadding(6));

  // Générateur de ligne
  const line = d3.line()
    .x(d => xScale(d.gp))
    .y(d => yScale(d.value))
    .curve(d3.curveMonotoneX);

  // Lignes pilotes
  const lineGroup = g.append("g").attr("class", "lines");
  const paths = lineGroup.selectAll("path")
    .data(drivers, d => d.name)
    .join("path")
      .attr("class", "driver-line")
      .attr("data-driver", d => d.name)
      .attr("stroke", d => d.color)
      .attr("d", d => line(d.points));

  // Animation du tracé
  const totalLengths = new Map();
  paths.each(function(d) {
    const len = this.getTotalLength();
    totalLengths.set(d.name, len);
    d3.select(this)
      .attr("stroke-dasharray", `${len} ${len}`)
      .attr("stroke-dashoffset", len);
  });

  // Points sur chaque GP
  const dotGroup = g.append("g").attr("class", "dots");
  drivers.forEach(d => {
    dotGroup.selectAll(null)
      .data(d.points)
      .join("circle")
        .attr("class", "driver-dot")
        .attr("data-driver", d.name)
        .attr("cx", p => xScale(p.gp))
        .attr("cy", p => yScale(p.value))
        .attr("r", 3)
        .attr("fill", d.color)
        .style("opacity", 0)
        .on("mouseenter", (event, p) => showTooltip(event, d, p))
        .on("mousemove", moveTooltip)
        .on("mouseleave", hideTooltip);
  });

  // Étiquettes (nom + score) en bout de ligne
  const labelGroup = g.append("g").attr("class", "labels");
  const labels = labelGroup.selectAll("text")
    .data(drivers, d => d.name)
    .join("text")
      .attr("class", "driver-label")
      .attr("data-driver", d => d.name)
      .attr("x", innerW + 8)
      .attr("y", d => yScale(d.points[d.points.length - 1].value))
      .attr("dy", "0.35em")
      .attr("fill", d => d.color)
      .style("opacity", 0)
      .text(d => `${shortName(d.name)} ${d.total}`);

  // Anti-collision verticale des labels (greedy)
  resolveLabelCollisions(labels, 14);

  // Hover sur les lignes (zone élargie via une copie transparente épaisse)
  lineGroup.selectAll("path.hit")
    .data(drivers, d => d.name)
    .join("path")
      .attr("class", "hit")
      .attr("fill", "none")
      .attr("stroke", "transparent")
      .attr("stroke-width", 14)
      .attr("d", d => line(d.points))
      .on("mouseenter", (event, d) => highlight(d.name))
      .on("mouseleave", () => clearHighlight())
      .on("mousemove", (event, d) => {
        const [mx] = d3.pointer(event, g.node());
        const nearest = d3.least(d.points, p => Math.abs(xScale(p.gp) - mx));
        showTooltip(event, d, nearest);
      });

  // Légende
  buildLegend(drivers);

  // Boutons
  document.getElementById("play-btn").addEventListener("click", () => animate(drivers, paths, totalLengths, dotGroup, labels));
  document.getElementById("reset-btn").addEventListener("click", () => resetAnim(paths, totalLengths, dotGroup, labels));

  // Lance l'animation au premier affichage
  animate(drivers, paths, totalLengths, dotGroup, labels);

  // ---- helpers internes ----
  function highlight(name) {
    paths.classed("dimmed", d => d.name !== name).classed("highlight", d => d.name === name);
    dotGroup.selectAll("circle").classed("dimmed", function() { return this.dataset.driver !== name; });
    labels.classed("dimmed", d => d.name !== name);
    d3.selectAll(".legend-item").classed("muted", function() { return this.dataset.driver !== name; });
  }
  function clearHighlight() {
    paths.classed("dimmed", false).classed("highlight", false);
    dotGroup.selectAll("circle").classed("dimmed", false);
    labels.classed("dimmed", false);
    d3.selectAll(".legend-item").classed("muted", false);
    hideTooltip();
  }
}

function animate(drivers, paths, totalLengths, dotGroup, labels) {
  const duration = 3500;
  paths
    .attr("stroke-dashoffset", function(d) { return totalLengths.get(d.name); })
    .transition()
    .duration(duration)
    .ease(d3.easeCubicInOut)
    .attr("stroke-dashoffset", 0);

  dotGroup.selectAll("circle")
    .style("opacity", 0)
    .transition()
    .delay((p, i, nodes) => {
      const pts = nodes.length;
      return (i % drivers[0].points.length) / drivers[0].points.length * duration;
    })
    .duration(150)
    .style("opacity", 1);

  labels
    .style("opacity", 0)
    .transition()
    .delay(duration - 200)
    .duration(400)
    .style("opacity", 1);
}

function resetAnim(paths, totalLengths, dotGroup, labels) {
  paths.interrupt().attr("stroke-dashoffset", function(d) { return totalLengths.get(d.name); });
  dotGroup.selectAll("circle").interrupt().style("opacity", 0);
  labels.interrupt().style("opacity", 0);
}

function buildLegend(drivers) {
  const container = d3.select("#legend");
  container.selectAll("*").remove();
  const items = container.selectAll(".legend-item")
    .data(drivers, d => d.name)
    .join("div")
      .attr("class", "legend-item")
      .attr("data-driver", d => d.name);

  items.append("span").attr("class", "legend-swatch").style("background", d => d.color);
  items.append("span").attr("class", "legend-name").text(d => d.name);
  items.append("span").attr("class", "legend-points").text(d => `${d.total} pts`);

  let isolated = null;
  items.on("click", function(event, d) {
    if (isolated === d.name) {
      isolated = null;
      d3.selectAll(".driver-line").classed("dimmed", false).classed("highlight", false);
      d3.selectAll(".driver-dot").classed("dimmed", false);
      d3.selectAll(".driver-label").classed("dimmed", false);
      d3.selectAll(".legend-item").classed("muted", false);
    } else {
      isolated = d.name;
      d3.selectAll(".driver-line")
        .classed("dimmed", function() { return this.dataset.driver !== d.name; })
        .classed("highlight", function() { return this.dataset.driver === d.name; });
      d3.selectAll(".driver-dot").classed("dimmed", function() { return this.dataset.driver !== d.name; });
      d3.selectAll(".driver-label").classed("dimmed", function() { return this.dataset.driver !== d.name; });
      d3.selectAll(".legend-item").classed("muted", function() { return this.dataset.driver !== d.name; });
    }
  });
}

function showTooltip(event, driver, point) {
  tooltip
    .style("opacity", 1)
    .html(`
      <strong>${driver.name}</strong>
      <div class="tt-team">${driver.team}</div>
      <div>${point.gp} : <strong>${point.value} pts</strong></div>
    `);
  moveTooltip(event);
}
function moveTooltip(event) {
  const pad = 14;
  tooltip
    .style("left", (event.pageX + pad) + "px")
    .style("top",  (event.pageY + pad) + "px");
}
function hideTooltip() { tooltip.style("opacity", 0); }

function shortName(full) {
  // "Lando Norris" -> "L. Norris"
  const parts = full.trim().split(/\s+/);
  if (parts.length < 2) return full;
  return parts[0][0] + ". " + parts.slice(1).join(" ");
}

function resolveLabelCollisions(selection, minGap) {
  const nodes = selection.nodes()
    .map(n => ({ node: n, y: +n.getAttribute("y") }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < nodes.length; i++) {
    const dy = nodes[i].y - nodes[i - 1].y;
    if (dy < minGap) {
      nodes[i].y = nodes[i - 1].y + minGap;
      nodes[i].node.setAttribute("y", nodes[i].y);
    }
  }
}
