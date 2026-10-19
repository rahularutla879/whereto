import { CATALOG, type Activity } from "./mock-data";

const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const DAY_PATTERN = /\b(?:(?:this|next)\s+)?(?:sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b/i;
const MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
const MONTH_PATTERN = new RegExp(`\\b(${MONTHS.join("|")})\\s+(\\d{1,2})(?:st|nd|rd|th)?(?:,?\\s+(\\d{4}))?\\b`, "i");

export function todayInBaltimore() {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const part = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function resolveDate(text: string, override: string, today: string) {
  if (override) return validDate(override) ? { date: override } : { error: "Choose a valid date in Set preferences." };
  const descriptions = [
    ...text.matchAll(/\b\d{4}-\d{2}-\d{2}\b/g),
    ...text.matchAll(new RegExp(MONTH_PATTERN.source, "gi")),
    ...text.matchAll(new RegExp(DAY_PATTERN.source, "gi")),
    ...text.matchAll(/\b(?:today|tonight|tomorrow)\b/gi),
  ];
  if (descriptions.length > 1) return { error: "Please choose one outing date in Set preferences; multiple date descriptions were found." };
  const iso = text.match(/\b\d{4}-\d{2}-\d{2}\b/g);
  if (iso && new Set(iso).size > 1) return { error: "Please choose one outing date in Set preferences." };
  if (iso) return validDate(iso[0]) ? { date: iso[0] } : { error: "That date is not valid. Choose a date in Set preferences." };
  const named = text.match(MONTH_PATTERN);
  if (named) {
    const date = `${named[3] || today.slice(0, 4)}-${String(MONTHS.indexOf(named[1].toLowerCase()) + 1).padStart(2, "0")}-${named[2].padStart(2, "0")}`;
    return validDate(date) ? { date } : { error: "That calendar date is not valid. Choose a date in Set preferences." };
  }
  const relative = text.match(/\b(today|tonight|tomorrow)\b/i);
  const weekday = text.match(DAY_PATTERN);
  if (relative && weekday) return { error: "The request has multiple day descriptions. Choose one date in Set preferences." };
  if (!relative && !weekday) return { date: undefined };
  const date = new Date(`${today}T12:00:00Z`);
  if (relative?.[1].toLowerCase() === "tomorrow") date.setUTCDate(date.getUTCDate() + 1);
  if (weekday) {
    const name = weekday[0].toLowerCase().split(/\s+/).at(-1)!;
    let offset = (WEEKDAYS.indexOf(name) - date.getUTCDay() + 7) % 7;
    if (weekday[0].toLowerCase().startsWith("next") && offset === 0) offset = 7;
    date.setUTCDate(date.getUTCDate() + offset);
  }
  return { date: date.toISOString().slice(0, 10) };
}

export function parseRequest(request: string) {
  const text = request.toLowerCase().replace(/[’‘]/g, "'");
  // Longest match wins: an art museum is a museum, not a gallery plus a museum.
  const matches = Object.entries(CATALOG).flatMap(([activity, item]) =>
    [...text.matchAll(item.pattern)].map((match) => ({ activity: activity as Activity, start: match.index!, end: match.index! + match[0].length })),
  ).sort((a, b) => a.start - b.start || b.end - a.end);
  const accepted: typeof matches = [];
  for (const match of matches) {
    if (!accepted.some((other) => match.start < other.end && match.end > other.start)) accepted.push(match);
  }
  const activities = [...new Set(accepted.map((match) => match.activity))];
  const locationMatch = text.match(/\bin\s+([a-z][a-z '-]*?)(?=[.,!?]|\s+(?:and|for|with|this|next|today|tomorrow|tonight|on|we|want|would)\b|$)/i);
  const location = locationMatch?.[1]?.trim();
  let remaining = [...text].map((character, index) => accepted.some((m) => index >= m.start && index < m.end) ? " " : character).join("");
  if (locationMatch) remaining = remaining.replace(locationMatch[0], " ");
  remaining = remaining
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, " ")
    .replace(new RegExp(MONTH_PATTERN.source, "gi"), " ")
    .replace(new RegExp(DAY_PATTERN.source, "gi"), " ")
    .replace(/\b(?:this weekend|today|tonight|tomorrow)\b/gi, " ")
    .replace(/\b(?:group|party) of \d+\b/g, " ")
    .replace(/\b\d+\s+(?:friends|people|persons|of us)\b/g, " ")
    .replace(/\$\s*\d+(?:\.\d+)?\s*(?:per person|each|a person)\b/g, " ")
    .replace(/\b(?:we|re|i|i'm|am|m|are|is|our|us|my|me|we'd|d|would|like|love|want|wants|to|a|an|the|and|then|also|plus|with|for|of|on|in|at|go|going|do|doing|see|watch|attend|visit|try|please|plan|outing|out|let|s|have|some|something|fun|friends|people|day|night|together|birthday|under|up|budget|md|maryland)\b/g, " ")
    .replace(/[.,!?;:'"&+()–—-]/g, " ")
    .replace(/\s+/g, " ").trim();
  return { activities, location, remaining };
}
