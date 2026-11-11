"""Disposable local fixture bridge. No application/evaluator imports this module."""
from collections import OrderedDict
import re
from copy import deepcopy
from hashlib import sha256
from threading import Lock
from time import monotonic

from backend.interpretation import (InterpretationInput, InterpretationResult, PendingClarification,
                                    advanced_travel_fields)
from backend.journey import REPHRASE
from backend.date_resolution import resolve_datetime
from backend.location_policy import geographic_intent
from backend.travel_mode import resolve_mode
from scripts.task52_ordering_preservation_dev import interpret_for_development

IDENTITY = '52b-v51-local-manual-pending-v1'


class LocalContinuation:
    """Provenance cache for existing DTOs, never planning/admission authority.

    Client effective snapshots must match an issued snapshot; the graph used
    below always comes from renewed proof of server-owned raw evidence.
    """
    def __init__(self, *, clock=monotonic):
        self.clock = clock
        self.issued = OrderedDict()
        self.lock = Lock()

    @staticmethod
    def key(pending):
        return sha256(pending.model_dump_json().encode()).hexdigest()

    def interpret(self, value, raw, reference):
        def block():
            from backend.ai import Interpretation
            return InterpretationResult(interpretation=Interpretation.model_validate(deepcopy(raw)),
                request=None, notes=[], issues=[REPHRASE], executionStatus='clarification_required')

        deadline = self.clock() + 600
        from backend.ai import Interpretation
        raw_hash = sha256(Interpretation.model_validate(raw).model_dump_json().encode()).hexdigest()
        answers = value.answers.model_copy(deep=True)
        if value.pending is not None:
            with self.lock:
                deadline, issued_raw = self.issued.get(self.key(value.pending), (0, None))
            if (deadline <= self.clock() or issued_raw != raw_hash or value.pending.text != value.text
                    or value.pending.referenceTime != reference):
                return block()
            retained = value.pending.answers.model_copy(deep=True)
            for name, answer in answers.model_dump().items():
                if answer.strip():
                    setattr(retained, name, answer.strip())
            answers = retained
        elif answers.model_dump(exclude_defaults=True):
            return block()
        # Activity/order/endpoint meaning cannot be repaired through unrelated
        # answer fields. Edit the original text and supply a new raw extraction.
        if any(getattr(answers, f) for f in ('activities','time','endpoint','people')):
            return block()
        manual = value.preferences
        if (manual.people or manual.budget or manual.costExplicit or manual.cost.value != 'balanced'
                or value.hasCurrentLocation):
            return block()

        # The immutable generalized proof and original grammar stay unchanged.
        fresh = InterpretationInput(text=value.text)
        result = interpret_for_development(fresh, extraction=deepcopy(raw), now=reference, preserve_order=True)
        if result.executionStatus != 'advanced_unavailable' or result.context is None:
            return result
        result = result.model_copy(deep=True)
        context = result.context
        destination = manual.location.strip() or answers.location or context.destination
        date = manual.date.strip() or answers.date
        calendar = resolve_datetime(answers.date or value.text, [] if answers.date else result.interpretation.date_expressions, [], destination,
                                    manual_date=date if manual.date or re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) else '', now=reference)
        mode, mode_issues = resolve_mode(value.text, result.interpretation.transport, manual.transport)
        travel, travel_issues = advanced_travel_fields(value.text, manual)
        first_limit = travel.pop('first_limit', None)
        if first_limit is not None:  # existing first-origin policy is not broadened here
            return block()
        if (not manual.date.strip() and answers.date and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', answers.date)
                and calendar.timezone == 'UTC'):
            return block()
        if (calendar.issues or mode_issues or travel_issues
                or value.calendarTimezone not in (None, calendar.timezone)):
            return block()
        context.destination = destination
        context.date = calendar.date
        context.dateOverride = bool(date)
        context.timezone = calendar.timezone
        context.timezoneBasis = 'destination_calendar' if calendar.timezone != 'UTC' else 'unknown'
        context.geography = geographic_intent(value.text, destination)
        context.transport = mode
        for name, item in travel.items():
            setattr(context, name, item)
        # Leave the raw extraction and its source quotes untouched. Effective
        # user controls live in context/answers, not fabricated extraction fields.
        result.pending = PendingClarification(text=value.text, interpretation=result.interpretation.model_copy(deep=True),
                                              answers=answers, referenceTime=reference)
        with self.lock:
            now = self.clock()
            if deadline <= now:
                return block()
            self.issued = OrderedDict((k,v) for k,v in self.issued.items() if v[0] > now)
            self.issued[self.key(result.pending)] = (deadline, raw_hash)
            while len(self.issued) > 50:
                self.issued.popitem(last=False)
        return result
