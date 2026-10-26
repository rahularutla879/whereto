import { ACTIVITY_LABELS, type Activity } from "./mock-data";

type HeadlineVenue = { name: string; activity: Activity; address?: string | null };
const compact = (name: string) => {
  const letters = Array.from(name.trim());
  return letters.length <= 28 ? name.trim() : `${letters.slice(0, 23).join("")}…${letters.slice(-4).join("")}`;
};

// Presentation only: every word comes from selected venue/activity evidence.
export function realHeadlines(options: HeadlineVenue[][], dinnerStops: number[] = []) {
  const full = options.map(venues => venues.map(v => v.name.trim()).join(" & "));
  const titles = options.map((venues, i) => venues.length <= 2 ? full[i] : venues.map(v => compact(v.name)).join(" · "));
  return options.map((venues, i) => {
    // Do not let abbreviations make otherwise distinct recommendations identical.
    let title = titles.some((other, j) => i !== j && other === titles[i]) ? full[i] : titles[i];
    if (full.some((other, j) => i !== j && other === full[i])) {
      const distinct = venues.find((v, stop) => v.address && options.some((other, j) => j !== i && full[j] === full[i] && other[stop]?.address !== v.address));
      if (distinct) title += ` (${distinct.address})`;
    }
    return { title, fullTitle: full[i], label: `OPTION ${i + 1} · ${venues.map((v, stop) => v.activity === "food" && dinnerStops.includes(stop) ? "DINNER" : ACTIVITY_LABELS[v.activity].toUpperCase()).join(" + ")}` };
  });
}
