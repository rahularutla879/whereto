// Only fixed labels and measured numeric counters enter the developer panel.
export function providerDiagnosticNotes(value:unknown):string[] {
  if(!value||typeof value!=="object")return [];
  const d=value as Record<string,unknown>;
  const service=["places.googleapis.com","routes.googleapis.com"].includes(String(d.service))?String(d.service):"local/unknown";
  const operation=["search","lookup","matrix","details"].includes(String(d.requestCategory))?String(d.requestCategory):"unknown";
  const boundary=["daily","minute","unknown"].includes(String(d.quotaBoundary))?String(d.quotaBoundary):"not established";
  const n=(key:string)=>typeof d[key]==="number"&&Number.isFinite(d[key])&&Number(d[key])>=0?String(d[key]):"unknown";
  return [`Development failure diagnostics — service ${service}; category ${operation}; quota boundary ${boundary}. Reserved attempts ${n("providerAttempts")}, searches ${n("placesSearchRequests")}, route elements ${n("reservedMatrixElements")}. Remaining Cloud quota is unknown.`];
}
