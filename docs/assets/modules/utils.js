/* Beautiful F1 — Dashboard : utilitaires de formatage + chargement de données. */

import { t, LANG } from "./i18n.js";

// Messages d'erreur bilingues codés en dur : la bannière peut s'afficher AVANT
// que i18n.json soit chargé (échec d'une ressource requise), donc on n'utilise pas t().
const ERROR_TEXT = {
  fr: "Certaines données n'ont pas pu être chargées. Réessayez plus tard.",
  en: "Some data could not be loaded. Please try again later.",
};

// Affiche une bannière d'erreur persistante en haut de page (idempotente).
export function showErrorBanner(message) {
  const text = message || ERROR_TEXT[LANG] || ERROR_TEXT.fr;
  let banner = document.getElementById("dash-error-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "dash-error-banner";
    banner.className = "dash-error-banner";
    banner.setAttribute("role", "alert");
    document.body.insertBefore(banner, document.body.firstChild);
  }
  banner.textContent = text;
}

/**
 * Charge un JSON avec gestion d'erreur explicite.
 * @param {string} url
 * @param {{required?: boolean, fallback?: any}} opts
 *   - required: si le chargement échoue, affiche la bannière et propage l'erreur.
 *   - fallback: valeur retournée si l'échec est toléré (ressource optionnelle).
 */
export async function fetchJson(url, { required = false, fallback = null } = {}) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    console.error(`[dashboard] échec de chargement de ${url} :`, e);
    if (required) {
      showErrorBanner();
      throw e;
    }
    return fallback;
  }
}

export function shortName(full) {
  const parts = (full || "").trim().split(/\s+/);
  if (parts.length < 2) return full;
  return parts[0][0] + ". " + parts.slice(1).join(" ");
}

export function escapeAttr(s) {
  return s.replace(/"/g, "&quot;");
}

export function formatCountdown(diffMs) {
  if (diffMs <= 0) return t("countdown.ongoing");
  const totalMin = Math.floor(diffMs / 60_000);
  const days = Math.floor(totalMin / (24 * 60));
  const hours = Math.floor((totalMin - days * 24 * 60) / 60);
  if (days >= 7) return t("countdown.days", { days });
  if (days >= 1) return t("countdown.dayHour", { days, hours: String(hours).padStart(2, "0") });
  const minutes = totalMin - days * 24 * 60 - hours * 60;
  return t("countdown.hourMin", {
    hours: String(hours).padStart(2, "0"),
    min: String(minutes).padStart(2, "0"),
  });
}

function dateLocale() {
  return LANG === "en" ? "en-GB" : "fr-FR";
}

export function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(dateLocale(), { day: "numeric", month: "short" });
}

export function formatDateShort(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  // ex. "08/03"
  return d.toLocaleDateString(dateLocale(), { day: "2-digit", month: "2-digit" });
}
