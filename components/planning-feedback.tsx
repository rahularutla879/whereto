import { ArrowUpRight, CircleHelp, Clock3, MapPin } from "lucide-react";
import { failureMessage } from "../lib/results-presentation";

export function PlanningFeedback({ loading, needsClarification, failed, message, onRetry, onEdit, stage }: {
  stage?: string; loading: boolean; needsClarification: boolean; failed: boolean; message: string;
  onRetry: () => void; onEdit: () => void;
}) {
  // Loading takes precedence even when a retained question/error is available.
  if (loading) return <div className="empty-state planning-feedback planning-loading" role="status" aria-busy="true"><Clock3 size={28} /><h3>{stage && stage !== "Generating itinerary" ? stage + "…" : "Planning your outing…"}</h3><p>{stage === "Choose nearby search area" ? "Location was unavailable. Confirm a manual search reference above; your request is kept." : stage === "Choose your starting place" ? "Choose a match above to continue your original outing." : stage === "Searching for starting place" ? "Your request is kept while we find matching places." : "We’re putting your stops together. Routing may wait briefly for capacity; you can cancel this request."}</p></div>;
  if (needsClarification) return <div className="empty-state planning-feedback" role="status"><CircleHelp size={28} /><h3>Just a little more detail.</h3><p>Answer the questions below your request to continue. Your original details are kept.</p></div>;
  return <div className="empty-state planning-feedback"><MapPin size={28} /><h3>{failed ? "We couldn’t complete your outing." : "Let’s tweak the plan."}</h3><p>{failureMessage(message)}</p>{failed && <button type="button" className="secondary-button" onClick={onRetry}>Retry <ArrowUpRight size={16} /></button>}<button type="button" className="secondary-button" onClick={onEdit}>Edit your request <ArrowUpRight size={16} /></button></div>;
}
