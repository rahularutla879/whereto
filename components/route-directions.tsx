import {safeMapsUrl} from '@/lib/venue-details';

/** Public identities only. Private endpoints are deliberately entered in Maps. */
export function RouteDirections({url,missing}:{url?:string|null;missing?:'origin'|'destination'}){
 if(!url||!safeMapsUrl(url))return null;
 return <div className="route-directions">
  <a href={url} target="_blank" rel="noopener noreferrer">View this leg on Google Maps</a>
  {missing&&<p className="details-note">{missing==='origin'?'Google Maps uses your current location if available; choose your confirmed starting place if different.':'Enter your original starting point in Google Maps to see this return leg. Your starting location is not included in this link.'}</p>}
 </div>;
}
