/* Beautiful F1 — Dashboard : utilitaires de formatage. */

import { t, LANG } from "./i18n.js";

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
