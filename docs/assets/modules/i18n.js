/* Beautiful F1 — Dashboard : internationalisation (FR / EN).
 *
 * I18N est un binding exporté "live" : il est peuplé par setI18n() depuis
 * l'orchestrateur après le fetch, et t() lit toujours la valeur courante.
 */

export let I18N = {};
export const LANG = localStorage.getItem("bf1-lang") || "fr";

export function setI18n(dict) {
  I18N = dict || {};
}

export function t(key, vars) {
  const dict = I18N[LANG] || I18N.fr || {};
  let s = dict[key] != null ? dict[key] : key;
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}

export function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.innerHTML = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
}

export function setupLangSwitcher() {
  const sw = document.getElementById("lang-switch");
  if (!sw) return;
  sw.querySelectorAll("button[data-lang]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === LANG);
    btn.addEventListener("click", () => {
      if (btn.dataset.lang === LANG) return;
      const embedHost = document.getElementById("dash-embed-host");
      const activeShortcut = document.querySelector(".dash-shortcut[data-viz-active='1']");
      if (embedHost && !embedHost.hidden && activeShortcut) {
        sessionStorage.setItem("bf1-active-embed", activeShortcut.dataset.vizId);
      } else {
        const activeTab = document.querySelector(".dash-tab.active");
        if (activeTab) sessionStorage.setItem("bf1-active-tab", activeTab.dataset.tab);
      }
      localStorage.setItem("bf1-lang", btn.dataset.lang);
      location.reload();
    });
  });
}
