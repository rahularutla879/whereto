"""Single backend Routes POST; shared protected impersonated ADC, zero retries."""
import requests

from backend.places import DiscoveryError, PROJECT
from backend.places_transport import access_token
from backend.routes import (ENDPOINT, FIELD_MASK, RouteError, RoutePoint,
                            matrix_body, require_development_routes)


def _validate_basic_body(body):
    """Rebuild the strict minimal request; reject extra/nested premium inputs."""
    try:
        mode = {"DRIVE": "drive", "WALK": "walk"}[body["travelMode"]]
        groups = []
        for name in ("origins", "destinations"):
            if not isinstance(body[name], list):
                raise ValueError("Invalid waypoints")
            points = []
            for i, record in enumerate(body[name]):
                waypoint = record["waypoint"]
                points.append(RoutePoint(id=str(i), place_id=waypoint["placeId"]) if "placeId" in waypoint else
                              RoutePoint(id=str(i), coordinates=waypoint["location"]["latLng"]))
            groups.append(points)
        if body != matrix_body(*groups, mode):
            raise ValueError("Unsupported request options")
    except (KeyError, TypeError, ValueError, RouteError):
        raise RouteError("invalid_request", "Only validated basic driving or walking matrix requests are permitted.") from None


def compute_matrix(body: dict) -> list:
    require_development_routes()
    # Defense in depth: no direct caller can add premium/traffic options here.
    _validate_basic_body(body)
    with requests.Session() as session:
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        try:
            token = access_token(session)
        except DiscoveryError:
            raise RouteError("authentication", "Local impersonated authentication is unavailable. No Routes request was sent.") from None
        try:
            from backend.development_cost import dispatch
            dispatch("matrix", len(body['origins']) * len(body['destinations']))
            response = session.post(
                ENDPOINT, json=body, timeout=(5, 15), allow_redirects=False,
                headers={"Authorization": f"Bearer {token}", "X-Goog-User-Project": PROJECT,
                         "X-Goog-FieldMask": FIELD_MASK, "Content-Type": "application/json"})
            if response.status_code != 200:
                code = {400: "invalid_request", 401: "authentication", 403: "permission", 429: "quota"}.get(response.status_code, "provider")
                raise RouteError(code, "Google routing failed. The reservation counts; no automatic retry was made.")
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Invalid matrix response")
            return data
        except requests.Timeout:
            raise RouteError("timeout", "Google routing timed out. No automatic retry was made.") from None
        except (requests.RequestException, ValueError):
            raise RouteError("provider", "Google routing returned no valid response. No automatic retry was made.") from None
