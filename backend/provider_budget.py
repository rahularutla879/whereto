"""Shared venue/travel/contact attempt accounting; no network transport.

One budget per backend process, one outing budget per plan. Every future attempt
must reserve before I/O, including pagination and failed attempts. Mock planning
and the separate local AI interpreter do not consume this budget.
"""

from contextlib import contextmanager, nullcontext
import os
from threading import Lock
from time import monotonic
from typing import Iterator, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderLimitError(RuntimeError):
    """Safe explanation for the future provider boundary to return to the user."""


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    # Real planning requires a separate, explicitly local development opt-in.
    mode: Literal["mock", "real"] = "mock"
    exploration: bool = False

    @model_validator(mode="after")
    def local_exploration(self):
        if self.exploration and (self.mode != "real" or not exploration_environment()):
            raise ValueError("Exploration requires explicitly local real development mode.")
        return self

    def ceiling(self, field):
        return float("inf") if self.exploration and field in EXPLORATION_UNCAPPED else getattr(self, field)

    searches_per_outing: int = Field(default=10, ge=0, le=10)
    details_per_outing: int = Field(default=6, ge=0, le=6)
    candidates_per_activity: int = Field(default=20, ge=1, le=20)
    matrix_elements_per_outing: int = Field(default=300, ge=0, le=300)
    requests_per_outing: int = Field(default=30, ge=0, le=30)
    concurrent_requests: int = Field(default=1, ge=1, le=1)
    retries: int = Field(default=0, ge=0, le=0)
    requests_per_session: int = Field(default=50, ge=0, le=50)
    matrix_elements_per_session: int = Field(default=1500, ge=0, le=1500)

    matrix_elements_per_minute: int = Field(default=150, ge=0, le=150)
    lookups_per_session: int = Field(default=10, ge=0, le=10)

    @classmethod
    def from_env(cls) -> "ProviderSettings":
        # Same explicit process-environment convention as AISettings; no dotenv.
        values = {field: int(os.environ[env]) for field, env in {
            "searches_per_outing": "WHERETO_SEARCHES_OUTING",
            "requests_per_outing": "WHERETO_REQUESTS_OUTING",
            "candidates_per_activity": "WHERETO_CANDIDATES",
            "matrix_elements_per_outing": "WHERETO_MATRIX_OUTING",
            "matrix_elements_per_session": "WHERETO_MATRIX_SESSION",
            "matrix_elements_per_minute": "WHERETO_MATRIX_MINUTE",
        }.items() if env in os.environ}
        flag = os.environ.get("WHERETO_EXPLORATION_DEV", "0")
        if flag not in ("0", "1"):
            raise ValueError("WHERETO_EXPLORATION_DEV must be 0 or 1.")
        return cls(mode=os.environ.get("VENUE_DATA_MODE", "mock"), exploration=flag == "1", **values)

    def require_live_provider(self) -> None:
        if self.mode == "real" and local_real_enabled() and (not self.exploration or exploration_environment()):
            return
        raise ProviderLimitError(
            "Real venue and route requests are disabled. Continue with fictional "
            "data until billing, alerts, restricted credentials and safeguards "
            "are verified and the owner explicitly authorizes live use."
        )


Operation = Literal["search", "lookup", "details", "route", "matrix"]


class ProviderBudget:
    """Thread-safe process/session counters. Restarting resets them, not billing.

    Reservation accounts for attempts; it does not authorize live use. A future
    adapter must ALSO call require_live_provider before any network operation.
    No automatic retries, waiting queue, response cache or persistent counters.
    """

    def __init__(self, settings: ProviderSettings | None = None):
        self.settings = ProviderSettings.model_validate(
            (settings or ProviderSettings.from_env()).model_dump())
        self._lock = Lock()
        self._requests = 0
        self._elements = 0
        self._active = 0
        self._matrix_window: list[tuple[float, int]] = []
        self._search_window = []
        self._lookups = 0
        from backend.development_cost import DevelopmentCost
        self.cost = DevelopmentCost() if self.settings.exploration else None

    def outing(self) -> "OutingBudget":
        return OutingBudget(self)


class OutingBudget:
    def __init__(self, session: ProviderBudget):
        self._session = session
        self._requests = 0
        self._searches = 0
        self._details = 0
        self._elements = 0
        self._pagination = 0
        self._matrix_requests = 0
        self._gross = 0
        self._dispatched = {"search":0,"details":0,"matrix":0,"matrixElements":0}
        self.stop_reason = None
        self._seen: set[tuple[str, str]] = set()

    @property
    def settings(self) -> ProviderSettings:
        """Immutable session limits for discovery request sizing."""
        return self._session.settings

    def usage(self) -> dict:
        result = {"placesSearchRequests": self._searches, "placesDetailsRequests": self._details,
                "reservedMatrixElements": self._elements, "providerAttempts": self._requests}
        if self.settings.exploration:
            result.update(explorationMode=True, paginationRequests=self._pagination, matrixRequests=self._matrix_requests,
                          estimatedOutingGrossUsd=self._gross/1000000, stopReason=self.stop_reason, dispatched=dict(self._dispatched),
                          estimateBasis="Gross list-price estimate; failed/unsent reserved batch work is conservatively charged. Not verified Cloud billing.",
                          **self.cost_snapshot())
        return result

    def cost_snapshot(self):
        from backend.development_cost import AccountingError
        try: return self._session.cost.snapshot()
        except AccountingError as error: raise ProviderLimitError(str(error)) from None

    def _record_dispatch(self, operation, count):
        self._dispatched[operation] += 1
        if operation == "matrix": self._dispatched["matrixElements"] += count

    def note_page(self):
        self._pagination += 1

    def routing_capacity(self) -> dict[str, int]:
        """Advisory capacity; atomic reservation still decides before any I/O.

        Keep six on-demand contacts available in the outing attempt allowance.
        Other outings/manual searches share the unchanged process ceiling.
        """
        session = self._session
        with session._lock:
            now = monotonic()
            used_minute = sum(n for t, n in session._matrix_window if now - t < 60)
            return {
                "elements": max(0, min(64 if self.settings.exploration else float("inf"), self.settings.ceiling("matrix_elements_per_outing") - self._elements,
                                       self.settings.ceiling("matrix_elements_per_session") - session._elements)),
                "minuteElements": max(0, self.settings.matrix_elements_per_minute - used_minute),
                "attempts": max(0, min(64 if self.settings.exploration else float("inf"), self.settings.ceiling("requests_per_outing") - self._requests -
                                      (self.settings.details_per_outing - self._details),
                                      self.settings.ceiling("requests_per_session") - session._requests)),
            }

    def check_candidates(self, count: int) -> None:
        if type(count) is not int or count < 0:
            raise ValueError("Candidate count must be a nonnegative integer.")
        if count > self.settings.ceiling("candidates_per_activity"):
            raise ProviderLimitError(
                "Too many venue candidates for one activity; narrow the search "
                "before calculating routes. No route request was started."
            )

    @contextmanager
    def reserve(self, operation: Operation, request_id: str, *,
                origins: int = 0, destinations: int = 0) -> Iterator[None]:
        """request_id identifies an exact request within this outing, never a key.

        Matrix accounting charges the full origins × destinations, not one HTTP
        request or the number of results that happen to succeed. Errors retain
        consumed counters and request identity, so retries cannot loop for free.
        """
        with self._reserve_batch([(operation, request_id, origins, destinations)]):
            yield

    @contextmanager
    def reserve_matrices(self, matrices: list[tuple[str, int, int]]) -> Iterator[None]:
        """Admit a complete routing plan atomically, before authentication/I/O.

        All planned attempts remain charged locally even if a failure stops the
        batch early. This conservative reservation prevents partial budget work.
        """
        if not matrices:
            raise ValueError("A matrix reservation needs at least one request.")
        with self._reserve_batch([("matrix", key, rows, cols) for key, rows, cols in matrices]):
            yield

    @contextmanager
    def _reserve_batch(self, attempts: list[tuple[Operation, str, int, int]]) -> Iterator[None]:
        for operation, request_id, origins, destinations in attempts:
            self._validate_attempt(operation, request_id, origins, destinations)
        identities = {(op, key) for op, key, _, _ in attempts}
        if len(identities) != len(attempts):
            raise ProviderLimitError("Duplicate provider requests are not allowed.")
        elements = sum(rows * cols for _, _, rows, cols in attempts)
        requests = len(attempts)
        searches = sum(op in ("search", "lookup") for op, _, _, _ in attempts)
        details = sum(op == "details" for op, _, _, _ in attempts)
        session = self._session
        limits = session.settings
        with session._lock:
            if identities & self._seen:
                raise ProviderLimitError("This provider request was already attempted. Reuse its result or stop; automatic retries are disabled.")
            if session._active >= limits.concurrent_requests:
                raise ProviderLimitError("Another external request is running. Wait for it to finish before continuing.")
            if session._requests + requests > limits.ceiling("requests_per_session"):
                raise ProviderLimitError("Local testing session request limit reached. Stop and review usage before starting a new session.")
            if self._requests + requests > limits.ceiling("requests_per_outing"):
                raise ProviderLimitError("This outing's provider request limit was reached. Narrow the request.")
            if self._details + details > limits.details_per_outing:
                raise ProviderLimitError("This outing’s contact-detail request limit was reached. Use the Google Maps venue link instead.")
            if self._searches + searches > limits.ceiling("searches_per_outing"):
                raise ProviderLimitError("This outing's venue search limit was reached. Narrow the activities or search area.")
            if self._elements + elements > limits.ceiling("matrix_elements_per_outing"):
                raise ProviderLimitError("This outing's route matrix element limit would be exceeded. Reduce candidates before requesting routes.")
            if session._elements + elements > limits.ceiling("matrix_elements_per_session"):
                raise ProviderLimitError("Local testing session route matrix element limit reached. Stop and review usage.")
            now = monotonic()
            session._search_window = [t for t in session._search_window if now - t < 60]
            lookups = sum(op == "lookup" for op, _, _, _ in attempts)
            if len(session._search_window) + searches > 10:
                raise ProviderLimitError("Local Places minute limit reached. Wait before a new deliberate search; no retry is scheduled.")
            if session._lookups + lookups > limits.lookups_per_session:
                raise ProviderLimitError("Starting-place lookup session limit reached. Stop and review usage.")
            session._matrix_window = [(t, n) for t, n in session._matrix_window if now - t < 60]
            if elements + sum(n for _, n in session._matrix_window) > limits.matrix_elements_per_minute:
                raise ProviderLimitError("Local route matrix minute quota reached. Stop and review usage; no automatic retry is scheduled.")
            from backend.development_cost import AccountingError
            units = {"search_enterprise" if os.environ.get("WHERETO_RATINGS_DEV") == "1" else "search_pro": searches - lookups,
                     "search_pro": lookups} if os.environ.get("WHERETO_RATINGS_DEV") == "1" else {"search_pro": searches}
            units.update(details=details, matrix_element=elements)
            reservation = session.cost.reserve(units, self._record_dispatch) if session.cost else nullcontext(0)
            try:
                charge = reservation.__enter__()
            except AccountingError as error:
                self.stop_reason = str(error)
                raise ProviderLimitError(str(error)) from None
            self._gross += charge
            self._matrix_requests += sum(op == "matrix" for op, _, _, _ in attempts)
            self._seen.update(identities)
            self._requests += requests
            self._searches += searches
            self._details += details
            self._elements += elements
            session._search_window.extend([now] * searches)
            session._lookups += lookups
            session._requests += requests
            session._elements += elements
            if elements:
                session._matrix_window.append((now, elements))
            session._active += 1
        try:
            yield
        finally:
            with session._lock:
                session._active -= 1
            reservation.__exit__(None, None, None)

    @staticmethod
    def _validate_attempt(operation, request_id, origins, destinations):
        if operation not in ("search", "lookup", "details", "route", "matrix"):
            raise ValueError("Unsupported provider operation.")
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 200:
            raise ValueError("A bounded nonblank request identity is required.")
        if any(type(n) is not int or n < 0 for n in (origins, destinations)):
            raise ValueError("Matrix dimensions must be nonnegative integers.")
        if operation == "matrix":
            if not origins or not destinations:
                raise ValueError("A route matrix needs positive origins and destinations.")
        elif origins or destinations:
            raise ValueError("Only matrix requests may specify dimensions.")


def local_real_enabled() -> bool:
    """Local-only two-part opt-in. Never activated by a production environment."""
    return (os.environ.get("VENUE_DATA_MODE", "mock") == "real"
            and os.environ.get("WHERETO_REAL_DEV") == "1"
            and os.environ.get("WHERETO_ENV", "development") == "development"
            and os.environ.get("NODE_ENV") != "production"
            and not any(os.environ.get(k) for k in ("VERCEL", "RENDER", "K_SERVICE", "WEBSITE_HOSTNAME")))


EXPLORATION_UNCAPPED = {"searches_per_outing", "candidates_per_activity", "matrix_elements_per_outing",
                       "requests_per_outing", "requests_per_session", "matrix_elements_per_session"}


def exploration_environment():
    return (local_real_enabled() and os.environ.get("WHERETO_ENV") == "development"
            and os.environ.get("NODE_ENV") in (None, "development")
            and not any(os.environ.get(k) for k in ("CI", "NETLIFY", "FLY_APP_NAME", "RAILWAY_ENVIRONMENT", "DYNO", "AWS_EXECUTION_ENV", "CODESPACES", "GITHUB_ACTIONS")))
