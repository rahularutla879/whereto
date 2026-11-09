# Offline tests and deterministic clocks

From `~/Documents/whereto`, with the existing backend virtual environment and Node dependencies installed:

```sh
npm run test:backend
npm test
npm run lint
npm run build
npm run typecheck
```

Run type checking after the build finishes: the build replaces generated `.next/types` files. Neither test command needs a running AI model or development server. HTTP tests start temporary loopback fixture servers on available ports. Managed sandboxes need local socket/process/Node IPC permission. Provider transports remain mocked; no live AI, Maps or hosted database is needed for normally enabled tests.

The complete backend command remains ordinary unittest discovery. No clock is installed by the runner, no cases are excluded, and there is no production fixed-clock setting.

## Pick the clock the scenario actually needs

- Pure date/time functions: prefer their explicit timezone-aware `now=` argument. Test future, current and expired requests, relative dates, timezones and DST with declared instants.
- Synthetic Nov7 venue/event scenarios: `self.enterContext(calendar_clock())` from `backend.testing_clock` freezes only `backend.location_context.datetime` at **2026-11-01T12:00:00Z**. Keep the Nov7 Saturday fixtures; do not repeatedly move event dates forward. Cleanup restores the clock even if the test fails.
- Route-cache reuse/cost scenarios: explicitly enter `route_evidence_clock()` where creation and cache validation must share a fixed instant. Cache-expiry scenarios must advance this clock or supply an explicit `now=`. The real policy stays **0 ≤ evidence age < 300 seconds**; evidence from the future is invalid. Never change the TTL or weaken request-count assertions to hide aging.
- Session capabilities and quota windows: control the relevant **monotonic** clock independently. Ten-minute capability expiry still occurs at 600 seconds. Calendar fixtures do not freeze these clocks.
- Daily/monthly accounting: use an owned temporary ledger and explicit billing-clock fixture. Never reset or reuse an owner's ledger for tests.

```python
from datetime import datetime, timezone
from unittest import TestCase
from backend.models import OutingRequest
from backend.location_context import outing_problem
from backend.testing_clock import calendar_clock

class Example(TestCase):
    def setUp(self):
        self.enterContext(calendar_clock())

    def test_expiration(self):
        request = OutingRequest(activities=["coffee"], location="New York", date="2026-11-07")
        # An explicit now still takes precedence over the fixture clock.
        problem = outing_problem(request, now=datetime(2030, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(problem[0], 'outing_date_expired')
```

`backend.test_api` launches the **same real app/routes** through the explicit test-only `backend.testing_clock:fixture_api --factory` target. That factory freezes calendar freshness for the child server's lifespan and restores it at shutdown. A parent-process patch cannot freeze a spawned Python server. Normal development/start commands keep using `backend.main:app`; they never select this factory.

## Isolation and worker cleanup

Use `TestCase.enterContext` or `with`, not a suite-wide clock patch. A test that only advances a quota's monotonic counter has not advanced its calendar or route-evidence clock. Keep those assumptions explicit. Do not add sleeps, retries or larger timeouts to disguise an uncontrolled clock.

The fake exploration HTTP child receives a copied environment without the parent runner's `CI` flag. Its explicit fixture server rejects real provider sends; production CI/real-provider admission remains unchanged. The parent environment is not edited. Cleanup checks already-exited children and registers an exit listener **before** signalling running children; never await an exit event that already happened. Negative startup/early-exit cases must fail promptly rather than hang teardown.

## Opt-in resources

The unchanged 37 default skips comprise 29 hosted PostgreSQL checks and 8 local POSIX PTY/process-lifecycle checks. Hosted tests need private database configuration and `WHERETO_DB_SCHEMA_TESTS=1`; do not enable them without separate resource authorization. Lifecycle tests need `WHERETO_LIFECYCLE_TESTS=1`, both development ports 3000/8000 stopped, and permission to control their own process groups. They never kill unknown listeners. Do not stop owner development processes just to enable these optional tests.

Ordering V4 remains default OFF. `backend.test_ordering_shadow` explicitly selects local observation and checks HTTP/body, interpretation, capability/session and admission equivalence, failure/timeout isolation and raw-versus-normalized graphs. Saved effective snapshots are skipped rather than mislabeled raw evidence. Legacy normalization remains authoritative and can still erase start/finish edges; passing fixture tests does not activate enforcement.

[Task52B regression repair, exact baseline failures and results](../docs/task52-backend-regression-repair.md).
