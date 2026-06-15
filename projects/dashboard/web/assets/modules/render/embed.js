/* Beautiful F1 — Dashboard : viz embarquées dans le cadre principal (iframe). */

import { LANG } from "../i18n.js";

export function initEmbed(manifestRes) {
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
      const h = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight);
      if (h > 0) embedFrame.style.height = h + "px";
    } catch (e) {
      /* cross-origin — ne devrait pas arriver (même domaine) */
    }
  }

  function showEmbed(item) {
    if (!embedHost || !embedFrame) return;
    // Marque le raccourci actif (utilisé pour restaurer après changement de langue)
    document
      .querySelectorAll(".dash-shortcut[data-viz-active]")
      .forEach((el) => delete el.dataset.vizActive);
    const sc = document.querySelector(`.dash-shortcut[data-viz-id="${item.id}"]`);
    if (sc) sc.dataset.vizActive = "1";
    // Masque la barre d'onglets + tous les panes
    standingsCard.querySelectorAll(".dash-card-header, .dash-tab-pane").forEach((el) => {
      el.dataset.hiddenByEmbed = "1";
      el.style.display = "none";
    });
    embedTitle.textContent = item.title;
    embedOpen.href = item.route + `?lang=${LANG}`;
    embedHost.hidden = false;

    embedFrame.onload = () => {
      fitEmbed();
      // La viz se rend / s'anime après le load : on remesure quelques fois
      [200, 700, 1500, 3000].forEach((ms) => setTimeout(fitEmbed, ms));
      // Suit les changements de taille du contenu (responsive, animations)
      try {
        const win = embedFrame.contentWindow;
        if (embedResizeObserver) embedResizeObserver.disconnect();
        embedResizeObserver = new win.ResizeObserver(() => fitEmbed());
        embedResizeObserver.observe(embedFrame.contentDocument.body);
      } catch (e) {
        /* ignore */
      }
    };
    embedFrame.src = item.route + `?embed=1&lang=${LANG}`;
  }

  function hideEmbed() {
    if (!embedHost) return;
    document
      .querySelectorAll(".dash-shortcut[data-viz-active]")
      .forEach((el) => delete el.dataset.vizActive);
    if (embedResizeObserver) {
      embedResizeObserver.disconnect();
      embedResizeObserver = null;
    }
    embedHost.hidden = true;
    embedFrame.onload = null;
    embedFrame.src = "about:blank";
    embedFrame.style.height = "";
    standingsCard.querySelectorAll('[data-hidden-by-embed="1"]').forEach((el) => {
      el.style.display = "";
      delete el.dataset.hiddenByEmbed;
    });
  }

  // Re-mesure quand la fenêtre du dashboard change de taille
  window.addEventListener("resize", () => fitEmbed());

  if (embedBack) embedBack.addEventListener("click", hideEmbed);

  if (vizContainer && manifestRes.items) {
    const vizItems = manifestRes.items.filter((it) => it.category === "viz");
    vizContainer.innerHTML = vizItems
      .map((it) => {
        const disabled = !it.available;
        const cls = `dash-shortcut ${disabled ? "is-disabled" : ""}`;
        const ariaAttr = disabled ? `aria-disabled="true"` : `role="button" tabindex="0"`;
        return `
        <div class="${cls}" data-viz-id="${it.id}" ${ariaAttr}>
          <span class="dash-shortcut-title">${it.title}</span>
          <span class="dash-shortcut-arrow">${disabled ? "·" : "→"}</span>
        </div>
      `;
      })
      .join("");

    vizContainer.querySelectorAll(".dash-shortcut:not(.is-disabled)").forEach((el) => {
      const item = vizItems.find((it) => it.id === el.dataset.vizId);
      if (!item) return;
      el.addEventListener("click", () => showEmbed(item));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          showEmbed(item);
        }
      });
    });
  }
}
