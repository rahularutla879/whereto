import { EMPTY_PREFERENCES, type Preferences } from "./planner";

export type PreferenceField = Exclude<keyof Preferences, "costExplicit">;
export type PreferenceState = {
  values: Preferences;
  manual: Partial<Record<PreferenceField, boolean>>;
};

export function emptyPreferenceState(): PreferenceState {
  return { values: { ...EMPTY_PREFERENCES }, manual: {} };
}

export function editPreference(state: PreferenceState, field: PreferenceField, value: string): PreferenceState {
  return {
    values: { ...state.values, [field]: value, ...(field === "cost" ? { costExplicit: true } : {}) },
    manual: { ...state.manual, [field]: field === "cost" || value.trim() !== "" },
  };
}

// Displayed extraction is never submitted as a manual override. Clearing a
// field releases its override; zero strings and deliberate Balanced stay real.
export function manualPreferences(state: PreferenceState): Preferences {
  const result = { ...EMPTY_PREFERENCES };
  for (const field of ["location", "date", "people", "budget", "travel"] as const) {
    if (state.manual[field]) result[field] = state.values[field];
  }
  if (state.manual.transport) result.transport=state.values.transport;
  if (state.manual.cost) {
    result.cost = state.values.cost;
    result.costExplicit = true;
  }
  return result;
}

export function displayInterpretedPreferences(state: PreferenceState, inferred: Preferences): PreferenceState {
  const values = { ...inferred, costExplicit: !!state.manual.cost };
  for (const field of ["location", "date", "people", "budget", "travel"] as const) {
    if (state.manual[field]) values[field] = state.values[field];
  }
  if (state.manual.transport) values.transport=state.values.transport;
  if (state.manual.cost) values.cost = state.values.cost;
  return { values, manual: { ...state.manual } };
}

// Consume the effective structured request already validated by Python. Never
// reparse prose, infer missing optional caps, or make a second model call.
export function interpretedPreferences(value: unknown): Preferences {
  const request = value as Record<string, unknown> | null;
  const nullableNumber = (n: unknown) => n === null || (typeof n === "number" && Number.isFinite(n) && n >= 0);
  if (!request || typeof request.location !== "string" || !request.location.trim()
    || !(request.date === null || (typeof request.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(request.date)))
    || !nullableNumber(request.budget) || !nullableNumber(request.travel)
    || !["budget", "balanced", "experience"].includes(request.cost as string)) {
    throw new Error("Invalid interpreted preference values");
  }
  return {
    ...(request.transport === "walking" || request.transport === "driving" ? {transport: request.transport} : {}),
    location: request.location, date: request.date as string | null ?? "", people: "",
    budget: request.budget === null ? "" : String(request.budget),
    travel: request.travel === null ? "" : String(request.travel),
    cost: request.cost as Preferences["cost"], costExplicit: false,
  };
}
