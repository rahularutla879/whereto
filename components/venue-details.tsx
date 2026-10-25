"use client";
import { useState } from "react";
import type { DisplayVenue } from "../lib/planner";
import { safeWebsite, type Credit, type ContactDetails, VenueDetailsSession } from "../lib/venue-details";

export function GoogleCredits({ credits = [] }: { credits?: Credit[] }) {
  return <span className="provider-credits"><span className="google-attribution" translate="no">Google Maps</span>{credits.map((credit, i) => <span key={i}>{safeWebsite(credit.uri) ? <a href={safeWebsite(credit.uri)!} target="_blank" rel="noopener noreferrer">{credit.provider ?? "Provider credit"}</a> : credit.provider}</span>)}</span>;
}
export function VenueDetails({ venue, token, session }: { venue: DisplayVenue; token?: string; session: VenueDetailsSession }) {
  const [open, setOpen] = useState(false);
  const [contact, setContact] = useState<ContactDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function toggle() {
    setOpen(!open);
    if (open || contact || loading || error || !venue.providerPlaceId || !token) return;
    setLoading(true);
    try { setContact(await session.get(token, venue.providerPlaceId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Contact details are unavailable."); }
    finally { setLoading(false); }
  }
  if (!venue.providerPlaceId) return null;
  return <div className="venue-details">
    <button type="button" className="plan-link" aria-expanded={open} onClick={toggle}>{open ? "Close details" : "View details"}</button>
    <div hidden={!open} className="venue-contact" role="region" aria-label={`${venue.name} details`}>
      <strong>{venue.name}</strong><p>{venue.address ?? "Address unavailable"}</p>
      {loading && <p role="status">Loading contact information…</p>}
      {error && <p role="status">{error}</p>}
      {!loading && <><p>{contact?.telephoneUrl ? <a href={contact.telephoneUrl}>{contact.phone}</a> : "Phone number unavailable"}</p>
        <p>{contact?.website ? <a href={contact.website} target="_blank" rel="noopener noreferrer">Official venue website</a> : "Website unavailable"}</p></>}
      {safeWebsite(venue.mapsUrl) && <a href={safeWebsite(venue.mapsUrl)!} target="_blank" rel="noopener noreferrer">View location on Google Maps</a>}
      <p>Contact the venue to arrange your visit. No reservation or ticket is confirmed.</p>
      <GoogleCredits credits={[...(venue.evidenceLabels?.attribution?.third_party ?? []), ...(contact?.attributions ?? [])]} />
    </div>
  </div>;
}
