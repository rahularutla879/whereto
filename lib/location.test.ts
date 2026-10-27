import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { LocationControls } from "../components/location-controls";
import { VenueDetails } from "../components/venue-details";
import { FirstPreference } from "./first-preference";
import { requestLocation, requestStartingLocation } from "./location";
import { VenueDetailsSession } from "./venue-details";
import type { DisplayVenue } from "./planner";

test("rendering location controls and venue details never requests permission or contact data", () => {
  const html = renderToStaticMarkup(createElement(LocationControls, { onChange: () => { throw new Error("Unexpected location request"); } }));
  assert.match(html, /Use my current location/);
  assert.match(html, /Enter my starting location/);
  assert.doesNotMatch(html, /Search radius near me|Plan without a starting point|Optional starting location/);
  assert.match(html, /First-stop travel preference/);
  assert.doesNotMatch(html, /latitude|longitude|starting coordinates/i);
  const venue = { id: "real", providerPlaceId: "real", name: "Venue", address: "Synthetic address" } as DisplayVenue;
  const session = new VenueDetailsSession(); session.get = () => { throw new Error("Prefetched contact data"); };
  const details = renderToStaticMarkup(createElement(VenueDetails, { venue, token: "token", session }));
  assert.match(details, /aria-expanded="false"/);
  assert.match(details, /Phone number unavailable/);
  assert.match(details, /Website unavailable/);
  assert.match(details, /No reservation or ticket is confirmed/);
  assert.equal(renderToStaticMarkup(createElement(VenueDetails, { venue: { ...venue, providerPlaceId: null }, session })), "");
});

test("explicit location request: authorized point, denied permission, timeout and unsupported HTTPS context", async () => {
  let requests = 0;
  const geo = { getCurrentPosition(success: PositionCallback, _error?: PositionErrorCallback | null, options?: PositionOptions) {
    requests++; assert.equal(options?.maximumAge, 0);
    success({ coords: { latitude: 0, longitude: 0 } } as GeolocationPosition);
  } };
  assert.equal(requests, 0);
  assert.deepEqual(await requestLocation(geo, true), { latitude: 0, longitude: 0 });
  assert.equal(requests, 1);
  for (const code of [1, 2, 3]) {
    const denied = { getCurrentPosition(_success: PositionCallback, error?: PositionErrorCallback | null) { error?.({ code } as GeolocationPositionError); } };
    await assert.rejects(requestLocation(denied, true), /neighborhood/);
  }
  await assert.rejects(requestLocation(undefined, true), /localhost or HTTPS/);
  await assert.rejects(requestLocation(geo, false), /localhost or HTTPS/);
  assert.equal(requests, 1);
});


test("permission completion does not overwrite separately edited travel preferences", async () => {
  let success: PositionCallback | undefined;
  const preference=new FirstPreference();preference.hydrate({value:5,unit:"minutes",mode:"strict"});
  const pending = requestStartingLocation({ getCurrentPosition(callback) { success = callback; } }, true);
  preference.edit({value:2,unit:"minutes",mode:"strict"});
  success!({ coords: { latitude: 0, longitude: 0 } } as GeolocationPosition);
  assert.deepEqual(await pending, { coordinates: { latitude: 0, longitude: 0 } });
  assert.equal(preference.value?.value,2);
});
