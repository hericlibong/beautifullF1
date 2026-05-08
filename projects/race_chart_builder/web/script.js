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

// Calendrier des sprints 2026 (FIA) — match par sous-chaîne sur le nom de colonne
const SPRINT_KEYWORDS = ["China", "Miami", "Belgium", "Austin", "Brazil", "Qatar"];
const isSprintGp = name => SPRINT_KEYWORDS.some(k => name.toLowerCase().includes(k.toLowerCase()));

const tooltip = d3.select("body").append("div").attr("class", "tooltip");

d3.csv("./data/f1_race_chart_fastf1_2026.csv").then(rows => {
  if (!rows.length) {
    document.getElementById("chart").innerHTML = "<p>Aucune donnée disponible.</p>";
    return;
  }

  const allColumns = rows.columns;
  const gpColumns = allColumns.filter(c => !META_COLS.has(c));
  const lastGp = gpColumns[gpColumns.length - 1];

  // Max de points par GP (tous pilotes confondus) — sert au mode "écart au leader".
  const maxByGp = { __START__: 0 };
  gpColumns.forEach(gp => {
    maxByGp[gp] = d3.max(rows, r => +r[gp] || 0) || 0;
  });

  const drivers = rows
    .map(r => ({
      name: r.Pilote,
      team: r.team,
      image: r.image,
      color: TEAM_COLORS[r.team] || FALLBACK_COLOR,
      points: [
        { gp: "__START__", value: 0 },
        ...gpColumns.map(gp => ({ gp, value: +r[gp] || 0 })),
      ],
      pointsDelta: [
        { gp: "__START__", value: 0 },
        ...gpColumns.map(gp => ({ gp, value: (+r[gp] || 0) - maxByGp[gp] })),
      ],
      total: +r[lastGp] || 0,
      totalDelta: (+r[lastGp] || 0) - maxByGp[lastGp],
    }))
    .filter(d => d.total > 0)
    .sort((a, b) => b.total - a.total);

  // ---- Méta par (GP, pilote) : rang, écart au leader, gain au GP ----
  // Classement de compétition (1, 2, 2, 4) en cas d'ex æquo.
  const metaByGp = {};
  gpColumns.forEach((gp, gpIdx) => {
    const sorted = drivers.map(d => ({ name: d.name, val: d.points[gpIdx + 1].value }))
      .sort((a, b) => b.val - a.val);
    const ranks = {};
    let lastVal = null, lastRank = 0;
    sorted.forEach((s, i) => {
      const rank = (lastVal !== null && s.val === lastVal) ? lastRank : i + 1;
      ranks[s.name] = rank;
      lastVal = s.val;
      lastRank = rank;
    });
    const tieCount = {};
    sorted.forEach(s => { tieCount[ranks[s.name]] = (tieCount[ranks[s.name]] || 0) + 1; });
    const leaderVal = sorted[0]?.val || 0;
    metaByGp[gp] = {};
    drivers.forEach(d => {
      const v = d.points[gpIdx + 1].value;
      const prev = gpIdx === 0 ? 0 : d.points[gpIdx].value;
      metaByGp[gp][d.name] = {
        rank: ranks[d.name],
        rankTied: tieCount[ranks[d.name]] > 1,
        leaderGap: v - leaderVal,
        gainAtGp: v - prev,
      };
    });
  });
  window.__chartCtx = { metaByGp, mode: "cumul" };

  let currentScale = "linear";
  let currentMode = "cumul";

  function fullRebuild() {
    d3.select("#chart").selectAll("*").remove();
    d3.select("#legend").selectAll("*").remove();
    d3.select("#quick-filters").selectAll("*").remove();
    ["play-btn", "reset-btn", "clear-selection-btn", "progress-slider"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.replaceWith(el.cloneNode(true));
    });
    const driversForMode = currentMode === "delta"
      ? drivers.map(d => ({ ...d, points: d.pointsDelta, total: d.totalDelta }))
      : drivers;
    window.__chartCtx.mode = currentMode;
    render(driversForMode, gpColumns, currentScale, currentMode);
  }

  fullRebuild();

  document.getElementById("scale-toggle-btn").addEventListener("click", function() {
    currentScale = currentScale === "linear" ? "log" : "linear";
    this.dataset.scale = currentScale;
    this.textContent = currentScale === "linear" ? "📏 Échelle : linéaire" : "📐 Échelle : log";
    fullRebuild();
  });

  document.getElementById("mode-toggle-btn").addEventListener("click", function() {
    currentMode = currentMode === "cumul" ? "delta" : "cumul";
    this.dataset.mode = currentMode;
    this.textContent = currentMode === "cumul" ? "📊 Mode : cumul" : "📊 Mode : écart leader";
    fullRebuild();
  });
});

function render(drivers, gpColumns, scaleType = "linear", mode = "cumul") {
  const isMobile = window.matchMedia && window.matchMedia("(max-width: 600px)").matches;
  const margin = isMobile
    ? { top: 16, right: 70, bottom: 140, left: 38 }
    : { top: 20, right: 140, bottom: 130, left: 50 };
  const width  = 1180;
  const height = Math.max(900, drivers.length * 34 + 280);
  const innerW = width  - margin.left - margin.right;
  const innerH = height - margin.top  - margin.bottom;
  const xRotation = isMobile ? -65 : -45;

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
  const minY = d3.min(drivers, d => d3.min(d.points, p => p.value)) || 0;
  const isDelta = mode === "delta";
  const domainLow = isDelta ? minY * 1.05 : 0;
  const domainHigh = isDelta ? 0 : maxY * 1.05;
  const yScale = scaleType === "log"
    ? d3.scaleSymlog().constant(1).domain([domainLow, domainHigh]).range([innerH, 0])
    : d3.scaleLinear().domain([domainLow, domainHigh]).range([innerH, 0]).nice();

  // Gridlines horizontales
  let gridTicks;
  if (scaleType === "log" && !isDelta) {
    gridTicks = [0, 1, 3, 10, 30, 100].filter(v => v <= maxY * 1.05);
  } else if (scaleType === "log" && isDelta) {
    gridTicks = [0, -1, -3, -10, -30, -100].filter(v => v >= minY * 1.05);
  } else {
    gridTicks = yScale.ticks(6);
  }
  g.append("g")
    .attr("class", "grid")
    .selectAll("line")
    .data(gridTicks)
    .join("line")
      .attr("class", "gridline")
      .attr("x1", 0).attr("x2", innerW)
      .attr("y1", d => yScale(d)).attr("y2", d => yScale(d));

  // Repères verticaux pour les week-ends sprint (rendu derrière les courbes)
  const sprintGps = gpColumns.filter(isSprintGp);
  g.insert("g", ".grid + *")
    .attr("class", "sprint-markers")
    .selectAll("line")
    .data(sprintGps)
    .join("line")
      .attr("class", "sprint-line")
      .attr("x1", d => xScale(d)).attr("x2", d => xScale(d))
      .attr("y1", 0).attr("y2", innerH);

  // Axes
  const xAxisG = g.append("g")
    .attr("class", "axis x-axis")
    .attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(xScale).tickSize(0).tickPadding(30));
  xAxisG.selectAll("text")
    .attr("text-anchor", "end")
    .attr("transform", `rotate(${xRotation})`)
    .classed("sprint-tick", d => isSprintGp(d));
  // Badge "S" au-dessus du tick pour les sprints
  xAxisG.selectAll(".tick")
    .filter(d => isSprintGp(d))
    .append("text")
      .attr("class", "sprint-badge")
      .attr("y", -8)
      .attr("text-anchor", "middle")
      .text("S");

  const yAxis = d3.axisLeft(yScale).tickSize(0).tickPadding(6);
  if (scaleType === "log") {
    yAxis.tickValues(gridTicks).tickFormat(d3.format("d"));
  } else {
    yAxis.ticks(6);
  }
  g.append("g").attr("class", "axis y-axis").call(yAxis);

  // Générateur de ligne (point sentinelle "__START__" ancré à l'origine x=0)
  const xPos = d => (d.gp === "__START__" ? 0 : xScale(d.gp));
  const line = d3.line()
    .x(xPos)
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
      .data(d.points.filter(p => p.gp !== "__START__"))
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

  // Endcap (photo + nom + score) en bout de ligne
  const PHOTO_R = isMobile ? 9 : 13;
  const PHOTO_GAP = 8;

  // <defs> avec un clipPath circulaire par pilote
  const defs = svg.append("defs");
  defs.selectAll("clipPath")
    .data(drivers, d => d.name)
    .join("clipPath")
      .attr("id", d => `clip-${slug(d.name)}`)
      .append("circle")
        .attr("r", PHOTO_R);

  // Position du dernier point (sur la courbe) — endcap par défaut s'y place.
  const tipOf = d => {
    const last = d.points[d.points.length - 1];
    return { x: xScale(last.gp), y: yScale(last.value) };
  };

  const labelGroup = g.append("g").attr("class", "labels");
  const labels = labelGroup.selectAll("g.driver-endcap")
    .data(drivers, d => d.name)
    .join("g")
      .attr("class", "driver-endcap")
      .attr("data-driver", d => d.name)
      .attr("transform", d => { const p = tipOf(d); return `translate(${p.x},${p.y})`; })
      .style("opacity", 0);

  // Disque de fond (couleur écurie, sert aussi de fallback si image absente)
  labels.append("circle")
    .attr("class", "driver-photo-bg")
    .attr("r", PHOTO_R)
    .attr("fill", d => d.color)
    .attr("fill-opacity", 0.18);

  // Image clippée
  const photoImages = labels.append("image")
    .attr("class", "driver-photo")
    .attr("data-image", d => d.image) // URL stockée, pas encore chargée
    .attr("x", -PHOTO_R)
    .attr("y", -PHOTO_R)
    .attr("width", PHOTO_R * 2)
    .attr("height", PHOTO_R * 2)
    .attr("preserveAspectRatio", "xMidYMid slice")
    .attr("clip-path", d => `url(#clip-${slug(d.name)})`)
    .on("error", function() { d3.select(this).style("display", "none"); });

  // Lazy-load via IntersectionObserver : les images ne sont fetchées
  // que lorsque le label entre (ou approche) le viewport.
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const node = entry.target;
        const img = node.querySelector("image.driver-photo");
        if (img && !img.getAttribute("href")) {
          const url = img.getAttribute("data-image");
          if (url) {
            img.setAttribute("href", url);
            img.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", url);
          }
        }
        obs.unobserve(node);
      });
    }, { rootMargin: "200px" });
    labels.each(function() { io.observe(this); });
  } else {
    photoImages
      .attr("href", d => d.image)
      .attr("xlink:href", d => d.image);
  }

  // Anneau coloré (couleur écurie)
  labels.append("circle")
    .attr("class", "driver-ring")
    .attr("r", PHOTO_R)
    .attr("fill", "none")
    .attr("stroke", d => d.color)
    .attr("stroke-width", 2);

  // Texte "L. Norris 51"
  labels.append("text")
    .attr("class", "driver-label-text")
    .attr("x", PHOTO_R + 6)
    .attr("dy", "0.35em")
    .attr("fill", d => d.color)
    .text(d => `${shortName(d.name)} ${d.total}`);

  // Index path-par-pilote pour faire suivre l'endcap pendant l'animation.
  const pathByDriver = new Map();
  paths.each(function(d) { pathByDriver.set(d.name, this); });

  // ---- Anti-collision des endcaps (positions finales) ----
  // Calcule pour chaque pilote une position Y ajustée à droite du dernier GP,
  // de sorte qu'aucune pastille ne se chevauche.
  const COLLIDE_R = PHOTO_R + 4;
  const finalNodes = drivers.map(d => {
    const tip = tipOf(d);
    return { name: d.name, x: tip.x, y: tip.y, targetY: tip.y };
  });
  d3.forceSimulation(finalNodes)
    .force("y", d3.forceY(d => d.targetY).strength(0.6))
    .force("x", d3.forceX(d => d.x).strength(1)) // X figé
    .force("collide", d3.forceCollide(COLLIDE_R))
    .stop()
    .tick(120);
  // Clamp dans la zone de tracé
  finalNodes.forEach(n => { n.y = Math.max(0, Math.min(innerH, n.y)); });
  const adjustedByName = new Map(finalNodes.map(n => [n.name, n]));

  // Connecteurs (petit trait entre la pointe de la courbe et l'endcap décalé)
  const connectors = g.insert("g", ".labels")
    .attr("class", "connectors")
    .selectAll("line")
    .data(drivers, d => d.name)
    .join("line")
      .attr("class", "label-connector")
      .attr("data-driver", d => d.name)
      .attr("stroke", d => d.color)
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.5)
      .style("opacity", 0);

  function placeConnectors(visible) {
    connectors
      .style("opacity", visible ? 1 : 0)
      .attr("x1", d => tipOf(d).x)
      .attr("y1", d => tipOf(d).y)
      .attr("x2", d => adjustedByName.get(d.name).x)
      .attr("y2", d => adjustedByName.get(d.name).y);
  }

  // Hover sur les lignes (zone élargie via une copie transparente épaisse)
  lineGroup.selectAll("path.hit")
    .data(drivers, d => d.name)
    .join("path")
      .attr("class", "hit")
      .attr("fill", "none")
      .attr("stroke", "transparent")
      .attr("stroke-width", 14)
      .attr("d", d => line(d.points))
      .style("cursor", "pointer")
      .on("mouseenter", (event, d) => highlight(d.name))
      .on("mouseleave", () => clearHighlight())
      .on("mousemove", (event, d) => {
        const [mx] = d3.pointer(event, g.node());
        const nearest = d3.least(d.points, p => Math.abs(xScale(p.gp) - mx));
        showTooltip(event, d, nearest);
      })
      .on("click", (event, d) => {
        const selected = window.__selectedDrivers;
        if (!selected) return;
        if (selected.has(d.name)) selected.delete(d.name);
        else selected.add(d.name);
        // un clic dans le graphique annule le filtre rapide actif
        d3.selectAll(".qf-btn").classed("active", false);
        applySelection(selected);
      });

  // Légende
  buildLegend(drivers);

  // Filtres rapides : Top 5 + une pastille par écurie
  buildQuickFilters(drivers);

  // Sélection initiale depuis l'URL (#drivers=Leclerc,Norris)
  applyHashSelection(drivers);
  window.addEventListener("hashchange", () => applyHashSelection(drivers));

  // ---- Slider de progression (scrub manuel, indépendant de l'animation) ----
  const slider = document.getElementById("progress-slider");
  const sliderLabel = document.getElementById("progress-label");

  function updateSliderUI(t) {
    if (!slider) return;
    const v = Math.round(t * 1000);
    if (document.activeElement !== slider) slider.value = v;
    slider.setAttribute("aria-valuenow", v);
    if (sliderLabel) {
      const nGp = gpColumns.length;
      const idx = Math.min(nGp - 1, Math.max(0, Math.floor(t * nGp - 0.0001)));
      const label = t <= 0 ? "Départ" : gpColumns[idx];
      sliderLabel.textContent = label;
      slider.setAttribute("aria-valuetext", label);
    }
  }

  // setProgress : peint le graphique à un t ∈ [0,1] arbitraire (scrub manuel)
  function setProgress(t) {
    t = Math.max(0, Math.min(1, t));
    paths.interrupt();
    labels.interrupt();
    dotGroup.selectAll("circle").interrupt();
    paths.each(function(d) {
      const len = totalLengths.get(d.name);
      d3.select(this)
        .attr("stroke-dasharray", `${len} ${len}`)
        .attr("stroke-dashoffset", len * (1 - t));
    });
    if (t >= 1) {
      labels
        .style("opacity", 1)
        .attr("transform", d => {
          const a = adjustedByName.get(d.name);
          return `translate(${a.x},${a.y})`;
        });
      placeConnectors(true);
    } else {
      labels
        .style("opacity", t > 0 ? 1 : 0)
        .attr("transform", function(d) {
          const node = pathByDriver.get(d.name);
          const len = totalLengths.get(d.name);
          const pt = node.getPointAtLength(t * len);
          return `translate(${pt.x},${pt.y})`;
        });
      placeConnectors(false);
    }
    const nGp = gpColumns.length;
    dotGroup.selectAll("circle").style("opacity", function() {
      const idx = gpColumns.indexOf(d3.select(this).datum().gp);
      return (t * nGp) >= (idx + 1) ? 1 : 0;
    });
    updateSliderUI(t);
  }

  if (slider) {
    slider.addEventListener("input", () => setProgress(+slider.value / 1000));
  }

  // Boutons : conservent leur comportement original (transitions D3)
  // En plus, on ajoute un tick parallèle pour faire vivre le slider pendant l'anim.
  function playWithSlider() {
    animate(drivers, paths, totalLengths, dotGroup, labels, pathByDriver, tipOf, adjustedByName, () => placeConnectors(true));
    const duration = 3500;
    const ease = d3.easeCubicInOut;
    const t = d3.timer(elapsed => {
      const k = Math.min(1, elapsed / duration);
      updateSliderUI(ease(k));
      if (k >= 1) t.stop();
    });
  }
  function resetWithSlider() {
    resetAnim(paths, totalLengths, dotGroup, labels, tipOf);
    placeConnectors(false);
    updateSliderUI(0);
  }

  document.getElementById("play-btn").addEventListener("click", playWithSlider);
  document.getElementById("reset-btn").addEventListener("click", resetWithSlider);
  document.getElementById("clear-selection-btn").addEventListener("click", () => {
    d3.selectAll(".legend-item").each(function() { this.classList.remove("active", "muted"); });
    d3.selectAll(".driver-line").classed("dimmed", false).classed("highlight", false);
    d3.selectAll(".driver-dot").classed("dimmed", false);
    d3.selectAll(".driver-endcap").classed("dimmed", false);
    if (window.__selectedDrivers) window.__selectedDrivers.clear();
  });

  // Lance l'animation au premier affichage
  playWithSlider();

  // ---- helpers internes ----
  function highlight(name) {
    const selected = window.__selectedDrivers;
    if (selected && selected.size > 0) return; // ne pas écraser la sélection active
    paths.classed("dimmed", d => d.name !== name).classed("highlight", d => d.name === name);
    dotGroup.selectAll("circle").classed("dimmed", function() { return this.dataset.driver !== name; });
    labels.classed("dimmed", d => d.name !== name);
    d3.selectAll(".legend-item").classed("muted", function() { return this.dataset.driver !== name; });
  }
  function clearHighlight() {
    hideTooltip();
    const selected = window.__selectedDrivers;
    if (selected && selected.size > 0) {
      // restaure l'état de sélection courant
      const isActive = n => selected.has(n);
      paths.classed("dimmed", d => !isActive(d.name)).classed("highlight", d => isActive(d.name));
      dotGroup.selectAll("circle").classed("dimmed", function() { return !isActive(this.dataset.driver); });
      labels.classed("dimmed", d => !isActive(d.name));
      d3.selectAll(".legend-item")
        .classed("muted", function() { return !isActive(this.dataset.driver); })
        .classed("active", function() { return isActive(this.dataset.driver); });
      return;
    }
    paths.classed("dimmed", false).classed("highlight", false);
    dotGroup.selectAll("circle").classed("dimmed", false);
    labels.classed("dimmed", false);
    d3.selectAll(".legend-item").classed("muted", false);
  }
}

function animate(drivers, paths, totalLengths, dotGroup, labels, pathByDriver, tipOf, adjustedByName, onEnd) {
  const duration = 3500;
  const settle = 600; // durée du recalage anti-collision en fin d'anim
  const ease = d3.easeCubicInOut;

  paths
    .interrupt()
    .attr("stroke-dashoffset", d => totalLengths.get(d.name))
    .transition()
    .duration(duration)
    .ease(ease)
    .attr("stroke-dashoffset", 0);

  dotGroup.selectAll("circle")
    .interrupt()
    .style("opacity", 0)
    .transition()
    .delay((p, i) => (i % drivers[0].points.length) / drivers[0].points.length * duration)
    .duration(150)
    .style("opacity", 1);

  const labelTransition = labels
    .interrupt()
    .style("opacity", 1)
    .transition()
    .duration(duration)
    .ease(ease)
    .attrTween("transform", function(d) {
      const node = pathByDriver.get(d.name);
      const len = totalLengths.get(d.name);
      return t => {
        const pt = node.getPointAtLength(t * len);
        return `translate(${pt.x},${pt.y})`;
      };
    });

  // À la fin, on transitionne vers les positions anti-collision puis on déclenche onEnd.
  if (adjustedByName) {
    labelTransition.transition()
      .duration(settle)
      .ease(d3.easeCubicOut)
      .attr("transform", d => {
        const a = adjustedByName.get(d.name);
        return `translate(${a.x},${a.y})`;
      })
      .on("end", () => { if (onEnd) onEnd(); });
  } else if (onEnd) {
    labelTransition.on("end", () => onEnd());
  }
}

function resetAnim(paths, totalLengths, dotGroup, labels, tipOf) {
  paths.interrupt().attr("stroke-dashoffset", d => totalLengths.get(d.name));
  dotGroup.selectAll("circle").interrupt().style("opacity", 0);
  labels.interrupt()
    .style("opacity", 0)
    .attr("transform", d => { const p = tipOf(d); return `translate(${p.x},${p.y})`; });
}

function buildLegend(drivers) {
  const container = d3.select("#legend");
  container.selectAll("*").remove();
  const items = container.selectAll(".legend-item")
    .data(drivers, d => d.name)
    .join("div")
      .attr("class", "legend-item")
      .attr("data-driver", d => d.name)
      .attr("role", "listitem")
      .attr("tabindex", 0)
      .attr("aria-label", d => `${d.name}, ${d.team}, ${d.total} points. Entrée pour ajouter ou retirer de la sélection.`)
      .on("keydown", function(event, d) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.click();
        }
      });

  items.append("span").attr("class", "legend-swatch").style("background", d => d.color);
  items.append("span").attr("class", "legend-name").text(d => d.name);
  items.append("span").attr("class", "legend-points").text(d => `${d.total} pts`);

  const selected = new Set();
  window.__selectedDrivers = selected;
  items.on("click", function(event, d) {
    if (selected.has(d.name)) {
      selected.delete(d.name);
    } else {
      selected.add(d.name);
    }
    applySelection(selected);
  });
}

function applySelection(selected) {
  writeSelectionToHash(selected);
  const isActive = name => selected.size === 0 || selected.has(name);
  d3.selectAll(".driver-line")
    .classed("dimmed", function() { return !isActive(this.dataset.driver); })
    .classed("highlight", function() { return selected.size > 0 && selected.has(this.dataset.driver); });
  d3.selectAll(".driver-dot")
    .classed("dimmed", function() { return !isActive(this.dataset.driver); });
  d3.selectAll(".driver-endcap")
    .classed("dimmed", function() { return !isActive(this.dataset.driver); });
  d3.selectAll(".legend-item")
    .classed("muted", function() { return !isActive(this.dataset.driver); })
    .classed("active", function() { return selected.size > 0 && selected.has(this.dataset.driver); });
}

function lastName(full) {
  const parts = full.trim().split(/\s+/);
  return parts[parts.length - 1];
}

function writeSelectionToHash(selected) {
  if (!selected || selected.size === 0) {
    if (window.location.hash) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    return;
  }
  const names = Array.from(selected).map(lastName);
  const hash = "#drivers=" + names.map(encodeURIComponent).join(",");
  if (window.location.hash !== hash) {
    history.replaceState(null, "", hash);
  }
}

function applyHashSelection(drivers) {
  const selected = window.__selectedDrivers;
  if (!selected) return;
  const m = window.location.hash.match(/#drivers=([^&]+)/);
  if (!m) return;
  const tokens = decodeURIComponent(m[1]).split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
  if (!tokens.length) return;
  selected.clear();
  for (const tok of tokens) {
    const match = drivers.find(d => lastName(d.name).toLowerCase() === tok)
              || drivers.find(d => d.name.toLowerCase().includes(tok));
    if (match) selected.add(match.name);
  }
  d3.selectAll(".qf-btn").classed("active", false);
  applySelection(selected);
}

function buildQuickFilters(drivers) {
  const container = d3.select("#quick-filters");
  container.selectAll("*").remove();

  const teams = Array.from(new Set(drivers.map(d => d.team)))
    .map(t => ({ team: t, color: drivers.find(d => d.team === t).color }));

  const filters = [
    { id: "top5", label: "Top 5", names: drivers.slice(0, 5).map(d => d.name) },
    ...teams.map(t => ({
      id: `team-${slug(t.team)}`,
      label: t.team,
      color: t.color,
      names: drivers.filter(d => d.team === t.team).map(d => d.name),
    })),
  ];

  const buttons = container.selectAll("button")
    .data(filters)
    .join("button")
      .attr("class", "qf-btn")
      .attr("type", "button")
      .attr("data-filter-id", d => d.id)
      .attr("aria-pressed", "false")
      .attr("aria-label", d => `Filtre rapide : ${d.label}`);

  buttons.each(function(d) {
    const btn = d3.select(this);
    if (d.color) {
      btn.append("span").attr("class", "qf-swatch").style("background", d.color);
    }
    btn.append("span").text(d.label);
  });

  let activeFilter = null;
  buttons.on("click", function(event, d) {
    const selected = window.__selectedDrivers;
    if (!selected) return;
    selected.clear();
    if (activeFilter === d.id) {
      activeFilter = null;
    } else {
      d.names.forEach(n => selected.add(n));
      activeFilter = d.id;
    }
    d3.selectAll(".qf-btn")
      .classed("active", function() { return this.dataset.filterId === activeFilter; })
      .attr("aria-pressed", function() { return this.dataset.filterId === activeFilter ? "true" : "false"; });
    applySelection(selected);
  });

  // Reset le filtre actif quand on touche la légende ou le bouton "Tout afficher"
  document.getElementById("clear-selection-btn").addEventListener("click", () => {
    activeFilter = null;
    d3.selectAll(".qf-btn").classed("active", false);
  });
  d3.selectAll(".legend-item").on("click.qf", () => {
    activeFilter = null;
    d3.selectAll(".qf-btn").classed("active", false);
  });
}

function showTooltip(event, driver, point) {
  if (point.gp === "__START__") { hideTooltip(); return; }
  const ctx = window.__chartCtx || {};
  const meta = ctx.metaByGp && ctx.metaByGp[point.gp] && ctx.metaByGp[point.gp][driver.name];
  const isDeltaMode = ctx.mode === "delta";

  let lines = `<div>${point.gp} : <strong>${point.value} pts</strong></div>`;
  if (meta) {
    const rankSuffix = meta.rank === 1 ? "er" : "e";
    const tied = meta.rankTied ? " ex æquo" : "";
    lines += `<div class="tt-row">Position : <strong>${meta.rank}${rankSuffix}${tied}</strong></div>`;
    if (!isDeltaMode && meta.leaderGap < 0) {
      lines += `<div class="tt-row">Écart au leader : <strong>${meta.leaderGap} pts</strong></div>`;
    }
    if (meta.gainAtGp !== 0) {
      const sign = meta.gainAtGp > 0 ? "+" : "";
      lines += `<div class="tt-row">Gain ce GP : <strong>${sign}${meta.gainAtGp} pts</strong></div>`;
    }
  }
  const sprintLine = isSprintGp(point.gp)
    ? '<div class="tt-sprint">Week-end sprint</div>'
    : '';
  tooltip
    .style("opacity", 1)
    .html(`
      <strong>${driver.name}</strong>
      <div class="tt-team">${driver.team}</div>
      ${lines}
      ${sprintLine}
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

function slug(s) {
  return s
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .toLowerCase();
}
