"use client";
import { VenueRating } from "./real-venue-facts";
import { useState } from "react";
import type { DisplayVenue } from "../lib/planner";
import { ContactLookupError, safeWebsite, safeMapsUrl, type Credit, type ContactDetails, VenueDetailsSession } from "../lib/venue-details";

export function GoogleCredits({ credits = [],showGoogle=true }: { credits?: Credit[];showGoogle?:boolean }) {
  return <span className="provider-credits">{showGoogle&&<span className="google-attribution" translate="no">Google Maps</span>}{credits.filter((credit,i,all)=>all.findIndex(c=>c.provider===credit.provider&&c.uri===credit.uri)===i).map((credit, i) => <span key={i}>{safeWebsite(credit.uri) ? <a href={safeWebsite(credit.uri)!} target="_blank" rel="noopener noreferrer">{credit.provider ?? "Provider credit"}</a> : credit.provider}</span>)}</span>;
}
export function VenueDetails({ venue, token, session }: { venue: DisplayVenue; token?: string; session: VenueDetailsSession }) {
  const [open, setOpen] = useState(false);
  const [contact, setContact] = useState<ContactDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [unsent,setUnsent]=useState(false);
  async function toggle() {
    setOpen(!open);
    if (open || contact || loading || error || !venue.providerPlaceId || !token) return;
    setLoading(true);
    try { setContact(await session.get(token, venue.providerPlaceId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Contact details are unavailable.");setUnsent(e instanceof ContactLookupError&&e.notAdmitted); }
    finally { setLoading(false); }
  }
  if (!venue.providerPlaceId) return null;
  return <div className="venue-details">
    <button type="button" className="plan-link" aria-expanded={open} onClick={toggle}>{open ? "Close details" : "View details"}</button>
    <div hidden={!open} className="venue-contact" role="region" aria-label={`${venue.name} details`}>
      <strong>{venue.name}</strong>{venue.address && <p>{venue.address}</p>}<VenueRating venue={venue} />
      {loading && <p role="status">Loading contact information…</p>}
      {error && <p role="status">{error}</p>}
      {unsent&&token&&<button type="button" onClick={async()=>{
        session.retryUnsent(token,venue.providerPlaceId!);setLoading(true);setError("");setUnsent(false);
        try{setContact(await session.get(token,venue.providerPlaceId!));}
        catch(e){setError(e instanceof Error?e.message:"Contact lookup unavailable.");setUnsent(e instanceof ContactLookupError&&e.notAdmitted);}
        finally{setLoading(false);}
      }}>Try unsent lookup after fixing local access</button>}
      {!loading && !error && <><p>{contact?.telephoneUrl ? <a href={contact.telephoneUrl}>{contact.phone}</a> : "Phone number unavailable"}</p>
        <p>{contact?.website ? <a href={contact.website} target="_blank" rel="noopener noreferrer">Official venue website</a> : "Website unavailable"}</p></>}
      {safeMapsUrl(venue.mapsUrl) && <a href={safeMapsUrl(venue.mapsUrl)!} target="_blank" rel="noopener noreferrer">View location on Google Maps</a>}
      <p>Contact the venue to arrange your visit. No reservation or ticket is confirmed.</p>
      <GoogleCredits credits={contact?.attributions} showGoogle={false} />
    </div>
  </div>;
}
