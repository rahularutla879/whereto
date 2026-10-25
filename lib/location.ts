// Invoked only by the explicit location button; never on mount or page load.
export function requestLocation(geo: Pick<Geolocation, "getCurrentPosition"> | undefined, secure: boolean): Promise<{ latitude: number; longitude: number }> {
  if (!secure || !geo) return Promise.reject(new Error("Location is unavailable here. Use localhost or HTTPS, or enter a city/neighborhood in Set preferences."));
  return new Promise((resolve, reject) => geo.getCurrentPosition(position => {
    resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude });
  }, () => reject(new Error("Location permission was denied or unavailable. Enter a city/neighborhood in Set preferences. For first-stop travel, you can enter starting coordinates below.")),
  { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }));
}
