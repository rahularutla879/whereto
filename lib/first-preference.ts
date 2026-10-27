import type { FirstTravel } from "./starting-areas";
// One active editor owns precedence; validated extraction may hydrate it only
// until a person edits it. Rerenders and asynchronous lookups never reset it.
export class FirstPreference {
  value: FirstTravel | null = null;
  edited = false;
  hydrate(value?: FirstTravel | null) { if (!this.edited) this.value=value ?? null; return this.value; }
  edit(value: FirstTravel | null) { this.edited=true; this.value=value; }
}
