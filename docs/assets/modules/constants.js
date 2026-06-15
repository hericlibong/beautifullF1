/* Beautiful F1 — Dashboard : constantes partagées. */

// Mapping nom de GP (calendrier) -> circuitId Ergast (clé de gp_history.json).
// À étendre au fur et à mesure que des circuits sont couverts par le builder.
export const GP_TO_CIRCUIT = {
  Spain: "catalunya",
};

// Couleurs d'écuries historiques (par teamId Ergast), pour le scatter chronologie.
// Utilisé en priorité car certains noms diffèrent de teams.json (ex. "Red Bull" vs "Red Bull Racing").
export const HISTORY_TEAM_COLORS = {
  williams: "#1868DB",
  ferrari: "#DC0000",
  mclaren: "#FF8000",
  mercedes: "#00D2BE",
  red_bull: "#1E2A78",
  benetton: "#00913A",
  brawn: "#B6FF1B",
  renault: "#FFD800",
  lotus_f1: "#000000",
  jordan: "#F5D800",
  brabham: "#0a3d91",
  ligier: "#1d6fb8",
  tyrrell: "#1d6fb8",
  honda: "#e10600",
  bmw_sauber: "#0066b3",
};
