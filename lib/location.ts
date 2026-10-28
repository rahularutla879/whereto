// Invoked only by the explicit location button; never on mount or page load.
export function requestLocation(geo: Pick<Geolocation, "getCurrentPosition"> | undefined, secure: boolean): Promise<{ latitude: number; longitude: number; accuracyMeters?: number }> {
  if (!secure || !geo) return Promise.reject(new Error("Location is unavailable here. Use localhost or HTTPS, or find a manual starting place below. A destination city/neighborhood can be entered in Set preferences."));
  return new Promise((resolve, reject) => geo.getCurrentPosition(position => {
    resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude, ...(Number.isFinite(position.coords.accuracy) ? {accuracyMeters:position.coords.accuracy} : {}) });
  }, error => reject(new Error((error.code===1?"Location permission was denied.":error.code===3?"Location request timed out.":"Your position is currently unavailable.")+" Enter and confirm a manual starting place or a destination city/neighborhood. Your outing is kept; no location was assumed.")),
  { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }));
}


// Travel preferences live in their own editor and are never captured by a GPS request.
export async function requestStartingLocation(geo: Pick<Geolocation, "getCurrentPosition"> | undefined, secure: boolean) {
  const {accuracyMeters,...coordinates} = await requestLocation(geo, secure);
  return { coordinates, ...(accuracyMeters!==undefined?{accuracyMeters}:{}) };
}
