// One active submission per page. Cancellation invalidates late responses too.
export class PlanningSession {
  private active: AbortController | null = null;
  begin(): AbortController | null {
    if (this.active) return null;
    this.active = new AbortController();
    return this.active;
  }
  current(controller: AbortController): boolean { return this.active === controller; }
  finish(controller: AbortController): boolean {
    if (!this.current(controller)) return false;
    this.active = null;
    return true;
  }
  cancel(): void {
    this.active?.abort();
    this.active = null;
  }
}
