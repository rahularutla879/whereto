import type { LocationContext } from "./planning-client";

// A submitted outing waits for explicit choice. Edits/unmount cancel its wait;
// a later selection cannot accidentally resume the old request.
export class StartingConfirmation {
  private resolve: ((value: LocationContext | null) => void) | null = null;
  get waiting() { return this.resolve !== null; }
  wait() {
    this.cancel();
    return new Promise<LocationContext | null>(resolve => { this.resolve = resolve; });
  }
  confirm(value: LocationContext) {
    const resolve = this.resolve;
    this.resolve = null;
    resolve?.(value);
    return resolve !== null;
  }
  cancel() {
    const resolve = this.resolve;
    this.resolve = null;
    resolve?.(null);
  }
}
