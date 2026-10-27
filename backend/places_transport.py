"""Keyless local ADC transport, with one Places POST and no retries/redirects."""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import google.auth
from google.auth import impersonated_credentials
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
import requests

from backend.provider_budget import local_real_enabled
from backend.places import (DiscoveryError, ENDPOINT, FIELD_MASK, PROJECT,
                            SERVICE_ACCOUNT, require_development_discovery)


class _AuthRequest(Request):
    """Bound auth to known hosts and refuse library-level retry attempts."""
    def __init__(self, session):
        super().__init__(session=session)
        self.seen = set()

    def __call__(self, url, method="GET", body=None, headers=None, timeout=15, **kwargs):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in (
                "oauth2.googleapis.com", "iamcredentials.googleapis.com") or url in self.seen:
            raise TransportError("Authentication endpoint or retry refused.")
        self.seen.add(url)
        return super().__call__(url, method=method, body=body, headers=headers, timeout=15, **kwargs)


def access_token(session: requests.Session) -> str:
    """Tokens stay in memory. Never fall back to broad user or key credentials."""
    path = Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
                Path(os.environ.get("CLOUDSDK_CONFIG", Path.home() / ".config/gcloud")) /
                "application_default_credentials.json")
    try:
        # Inspect only the local ADC configuration, never discover metadata/IP.
        config = json.loads(path.read_text())
        expected = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SERVICE_ACCOUNT}:generateAccessToken"
        if (not isinstance(config, dict) or path.stat().st_mode & 0o077
                or config.get("type") != "impersonated_service_account"
                or config.get("service_account_impersonation_url") != expected):
            raise ValueError("Unexpected ADC configuration")
        credentials, _ = google.auth.load_credentials_from_file(
            str(path), scopes=["https://www.googleapis.com/auth/cloud-platform"], quota_project_id=PROJECT)
        if (not isinstance(credentials, impersonated_credentials.Credentials)
                or credentials.service_account_email != SERVICE_ACCOUNT):
            raise ValueError("Unexpected identity")
        credentials.refresh(_AuthRequest(session))
        if not credentials.valid or not credentials.token:
            raise ValueError("Invalid token")
        return credentials.token
    except (OSError, ValueError, GoogleAuthError, requests.RequestException):
        raise DiscoveryError("authentication", "Local impersonated authentication is missing, expired or unavailable. Check the existing ADC setup; no Places request was sent.") from None


def text_search(body: dict, *, field_mask: str | None = None) -> dict:
    require_development_discovery()
    mask = field_mask if field_mask is not None else (FIELD_MASK + ",places.rating,places.userRatingCount" if
        os.environ.get("WHERETO_RATINGS_DEV") == "1" and local_real_enabled() else FIELD_MASK)
    allowed = {FIELD_MASK}
    if local_real_enabled() and os.environ.get("WHERETO_RATINGS_DEV") == "1":
        allowed.add(FIELD_MASK + ",places.rating,places.userRatingCount")
    if mask not in allowed:
        raise DiscoveryError("invalid_request", "Unsupported Places field selection.")
    with requests.Session() as session:
        # Plain Session has zero adapter retries. Do not use AuthorizedSession,
        # whose authentication recovery could resend a billable Places request.
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        token = access_token(session)
        try:
            from backend.development_cost import dispatch
            dispatch("search", 1)
            response = session.post(
                ENDPOINT, json=body, timeout=(5, 15), allow_redirects=False,
                headers={"Authorization": f"Bearer {token}", "X-Goog-User-Project": PROJECT,
                         "X-Goog-FieldMask": mask, "Content-Type": "application/json"})
            if response.status_code != 200:
                from backend.provider_errors import classify
                code,message,diagnostics=classify(response,'lookup' if field_mask is not None else 'search')
                error=DiscoveryError(code,message);error.diagnostics=diagnostics
                raise error
            data = response.json()
            if not isinstance(data, dict) or "error" in data:
                raise ValueError("Invalid success response")
            return data
        except requests.Timeout:
            raise DiscoveryError("timeout", "Google discovery timed out. The attempt counts; no retry was made.") from None
        except (requests.RequestException, ValueError):
            raise DiscoveryError("provider", "Google discovery could not return a valid response. No retry was made.") from None
