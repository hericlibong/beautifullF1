/* Beautiful F1 — Dashboard : détection de données périmées.
 *
 * Pourquoi ce module existe : la publication des données dépend d'un cron
 * GitHub Actions, dont l'exécution n'est pas garantie. Le 28/09/2026, le cron
 * n'est pas parti et le GP de Bakou est resté non publié pendant deux jours
 * sans qu'aucun signal ne se déclenche — le site continuait de servir un
 * classement périmé, l'air parfaitement normal.
 *
 * Une alerte hébergée dans un workflow planifié hériterait de la panne qu'elle
 * surveille : si le cron ne part pas, l'alerte ne part pas non plus. D'où cette
 * détection **côté client**, recalculée à chaque chargement de page à partir de
 * données déjà présentes (le calendrier et le statut de chaque GP). Elle ne
 * dépend d'aucun cron, d'aucun réseau supplémentaire, et fonctionne même si le
 * workflow a été désactivé.
 *
 * Voir doc/probleme-ouvert-fraicheur-des-donnees.md.
 */

import { t } from "./i18n.js";
import { formatDate } from "./utils.js";

// Délai laissé à la chaîne de publication (FastF1 + cron + build) avant de
// considérer qu'un GP couru aurait dû être publié. FastF1 propage en général
// sous 24 h ; 2 jours laissent la marge d'un cron retardé ou d'un rattrapage.
export const STALE_AFTER_DAYS = 2;

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function parseDate(iso) {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d) ? null : d;
}

/**
 * Compare les GP courus aux GP publiés.
 *
 * @param {object} dash   contenu de dashboard_2026.json
 * @param {Date}   [now]  injectable pour les tests
 * @returns {{stale: boolean, missing: Array<{name: string, date: string, daysLate: number}>,
 *            generatedAt: string|null}}
 */
export function checkFreshness(dash, now = new Date()) {
  const generatedAt = (dash && dash.generatedAt) || null;
  const calendar = (dash && dash.calendar) || [];
  const cutoff = now.getTime() - STALE_AFTER_DAYS * MS_PER_DAY;

  const missing = [];
  for (const gp of calendar) {
    const d = parseDate(gp.date);
    if (!d || d.getTime() > cutoff) continue;
    if (gp.status === "played") continue;
    missing.push({
      name: gp.shortName || gp.name,
      date: gp.date,
      daysLate: Math.floor((now.getTime() - d.getTime()) / MS_PER_DAY),
    });
  }

  return { stale: missing.length > 0, missing, generatedAt };
}

/**
 * Affiche un bandeau si des GP courus manquent aux données publiées, et
 * renseigne dans tous les cas la date de dernière mise à jour du pied de page.
 */
export function initFreshness(dash, now = new Date()) {
  const { stale, missing, generatedAt } = checkFreshness(dash, now);

  const stampEl = document.getElementById("dash-updated");
  if (stampEl && generatedAt) {
    stampEl.textContent = t("freshness.updated", { date: formatDate(generatedAt) });
  }

  const banner = document.getElementById("dash-freshness");
  if (!banner) return { stale, missing };

  if (!stale) {
    banner.hidden = true;
    return { stale, missing };
  }

  const worst = missing.reduce((a, b) => (b.daysLate > a.daysLate ? b : a));
  const names = missing.map((m) => `${m.name} (${formatDate(m.date)})`).join(", ");
  banner.textContent =
    missing.length === 1
      ? t("freshness.staleOne", { gp: names, days: worst.daysLate })
      : t("freshness.staleMany", { n: missing.length, list: names, days: worst.daysLate });
  banner.hidden = false;

  console.warn(`[dashboard] données en retard : ${names} — dernière publication ${generatedAt}`);
  return { stale, missing };
}
