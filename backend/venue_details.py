"""On-demand contact details. No persistent Google content cache or retries."""
from collections import OrderedDict
from secrets import token_urlsafe
from threading import Lock
from time import monotonic
import os
import re
from urllib.parse import urlsplit

import requests

from backend.places import DiscoveryError, PROJECT
from backend.provider_budget import local_real_enabled

DETAILS_MASK = "id,nationalPhoneNumber,internationalPhoneNumber,websiteUri,attributions"


def contact_links(data, place_id):
    if not isinstance(data, dict) or data.get("id") != place_id:
        raise DiscoveryError("invalid_response", "Venue contact details could not be verified.")
    phone = data.get("internationalPhoneNumber") or data.get("nationalPhoneNumber")
    if not isinstance(phone, str) or not re.fullmatch(r"\+?[0-9 ()\.\-]{7,35}", phone) or not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
        phone = None
    website = data.get("websiteUri")
    try:
        parsed = urlsplit(website) if isinstance(website, str) else None
        if (not parsed or parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or any(ord(c) < 33 for c in website) or len(website) > 2048):
            website = None
    except ValueError:
        website = None
    # Validate credits with the same canonical attribution parser.
    from backend.venue_models import Attribution
    from pydantic import ValidationError
    try:
        credits = [Attribution(provider=a.get("provider"), uri=a.get("providerUri")).model_dump(mode="json")
                   for a in data.get("attributions", [])]
    except (TypeError, AttributeError, ValidationError):
        raise DiscoveryError("invalid_response", "Venue credits could not be verified.") from None
    return {"placeId": place_id, "phone": phone, "telephoneUrl": "tel:" + re.sub(r"[^+0-9]", "", phone) if phone else None,
            "website": website, "attributions": credits}


def fetch_details(place_id):
    if not local_real_enabled() or os.environ.get("WHERETO_CONTACT_DETAILS_DEV") != "1":
        raise DiscoveryError("disabled", "Phone and website lookup is disabled for this development session. Use the Google Maps link to contact the venue.")
    from backend.places_transport import access_token
    with requests.Session() as session:
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        token = access_token(session)
        try:
            from backend.development_cost import dispatch
            dispatch("details", 1)
            response = session.get(f"https://places.googleapis.com/v1/places/{place_id}",
                headers={"Authorization": f"Bearer {token}", "X-Goog-User-Project": PROJECT,
                         "X-Goog-FieldMask": DETAILS_MASK}, timeout=(5, 15), allow_redirects=False)
            if response.status_code != 200:
                message = {429: "Contact lookup quota reached. Stop and review usage.",
                           401: "Contact lookup authentication failed.", 403: "Contact lookup permission or billing is unavailable."}.get(response.status_code, "Contact lookup is unavailable. No automatic retry was made.")
                raise DiscoveryError("details_unavailable", message)
            return contact_links(response.json(), place_id)
        except (requests.RequestException, ValueError):
            raise DiscoveryError("details_unavailable", "Contact lookup could not return valid details. No retry was made.") from None


class DetailsSessions:
    """Short-lived capability + original IDs/budget only; never stores venue content.

    The browser retains the active rendered panel's response while hiding/showing
    it. No HTTP/localStorage/disk cache. Regeneration/page close discards content.
    """
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = Lock()

    def create(self, ids, outing):
        with self.lock:
            now = monotonic()
            self.entries = OrderedDict((k, v) for k, v in self.entries.items() if now - v[0] < 1800)
            while len(self.entries) >= 50:
                self.entries.popitem(last=False)
            token = token_urlsafe(32)
            self.entries[token] = (now, set(ids), outing, set())
            return token

    def extend(self, token, ids):
        # Extend only the existing outing capability; keep its age and budget.
        with self.lock:
            entry = self.entries.get(token)
            if entry and monotonic() - entry[0] < 1800:
                entry[1].update(ids)

    def get(self, token, place_id):
        with self.lock:
            entry = self.entries.get(token)
            if not entry or monotonic() - entry[0] >= 1800 or place_id not in entry[1]:
                raise DiscoveryError("expired", "This outing has expired. Generate a new plan before looking up contact details.")
            if place_id in entry[3]:
                raise DiscoveryError("duplicate", "Contact lookup was already attempted. Reuse the open panel or generate a new outing; retries are disabled.")
            if not local_real_enabled() or os.environ.get("WHERETO_CONTACT_DETAILS_DEV") != "1":
                raise DiscoveryError("disabled", "Phone and website lookup is disabled. Use the Google Maps link to contact the venue.")
            entry[3].add(place_id)
        with entry[2].reserve("details", place_id):
            return {**fetch_details(place_id), "diagnostics": entry[2].usage()}


details_sessions = DetailsSessions()
