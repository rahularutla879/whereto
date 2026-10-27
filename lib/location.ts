// Invoked only by the explicit location button; never on mount or page load.
export function requestLocation(geo: Pick<Geolocation, "getCurrentPosition"> | undefined, secure: boolean): Promise<{ latitude: number; longitude: number; accuracyMeters?: number }> {
  if (!secure || !geo) return Promise.reject(new Error("Location is unavailable here. Use localhost or HTTPS, or find a manual starting place below. A destination city/neighborhood can be entered in Set preferences."));
  return new Promise((resolve, reject) => geo.getCurrentPosition(position => {
    resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude, ...(Number.isFinite(position.coords.accuracy) ? {accuracyMeters:position.coords.accuracy} : {}) });
  }, () => reject(new Error("Location permission was denied or unavailable. Enter a starting place below and select Find starting place, or enter a destination city/neighborhood in Set preferences. No starting point was assumed.")),
  { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }));
}


// Travel preferences live in their own editor and are never captured by a GPS request.
export async function requestStartingLocation(geo: Pick<Geolocation, "getCurrentPosition"> | undefined, secure: boolean) {
  const {accuracyMeters,...coordinates} = await requestLocation(geo, secure);
  return { coordinates, ...(accuracyMeters!==undefined?{accuracyMeters}:{}) };
}
