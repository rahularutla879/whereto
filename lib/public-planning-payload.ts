// Production browser payloads omit internal monitoring. The backend keeps its
// counters; authorized localhost development has a separate diagnostic endpoint.
export function publicPlanningPayload(value:unknown):unknown{
 if(process.env.NODE_ENV!=="production"||!value||typeof value!=="object")return value;
 const data={...(value as Record<string,unknown>)};
 const diagnostics=data.diagnostics as Record<string,unknown>|undefined;
 delete data.diagnostics;delete data.diagnosticNotes;
 if(diagnostics&&typeof diagnostics.contactRequestAdmitted==="boolean")data.diagnostics={contactRequestAdmitted:diagnostics.contactRequestAdmitted};
 if(Array.isArray(data.notes))data.notes=data.notes.filter(n=>typeof n==="string"&&!/^Development |^Calendar reference:|^Location-first discovery:/.test(n));
 return data;
}
