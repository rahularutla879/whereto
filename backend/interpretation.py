"""AI extraction -> conservative validation/overrides -> resolved planner contract.

Date/time resolution delegates to date_resolution; no itinerary arithmetic lives here.
"""
import re
from backend.provider_budget import local_real_enabled
from datetime import datetime, timezone
from datetime import date as CalendarDate
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, ValidationError, field_validator

from backend.location_context import DestinationContext
from backend.date_resolution import (DATE_WORDING, TIME_WORDING, CalendarReason, DATE_HELP,
                                     complete_year_answer, resolve_datetime)
from backend.location_policy import FirstTravel, Geography, first_intent, geographic_intent
from backend.between_policy import between_intent, mask
from backend.travel_constraints import travel_evidence, exclusive_limit, resolved_travel_label, normalize_verbatim_travel, CONTEXT
from backend.ai import AIProvider, Interpretation, create_provider
from backend.models import (ContractModel, CostPreference, Nonblank,
                            PlanningRequest, TransportationMode)


# Exact phrase normalization, not a fallback text interpreter. Unknown phrases
# are rejected in full; 'skydiving and dinner' cannot become a dinner-only plan.
ALIASES = {
    "bowling": "bowling", "bowl": "bowling",
    "drinks": "drinks", "drink": "drinks", "cocktails": "drinks", "cocktail": "drinks",
    "beer": "drinks", "beers": "drinks", "wine": "drinks", "mocktails": "drinks", "bar": "drinks",
    "movie theater": "movie", "movie theaters": "movie", "movie theatre": "movie", "movie theatres": "movie", "cinemas": "movie",
    "movie": "movie", "movies": "movie", "cinema": "movie", "film": "movie", "films": "movie", "show movies": "movie",
    "watch a movie": "movie", "watch a film": "movie", "go to the movies": "movie", "see a film": "movie",
    "food": "food", "dinner": "food", "lunch": "food", "breakfast": "food", "brunch": "food",
    "pizza": "food", "restaurant": "food", "dining": "food",
    "coffee": "coffee", "coffees": "coffee", "tea": "coffee", "cafe": "coffee", "café": "coffee",
    "outdoor": "outdoors", "outdoors": "outdoors", "outdoor activities": "outdoors",
    "park": "outdoors", "walk": "outdoors", "walking": "outdoors", "nature": "outdoors",
    "art": "art", "art gallery": "art", "gallery": "art", "art galleries": "art",
    "museum": "museum", "museums": "museum", "art museum": "museum", "science museum": "museum", "history museum": "museum",
    "karaoke": "karaoke", "arcade": "arcade", "video games": "arcade",
    "escape room": "escape", "escape rooms": "escape", "mini golf": "miniGolf", "mini-golf": "miniGolf", "miniature golf": "miniGolf", "putt-putt": "miniGolf",
    "shopping": "shopping", "thrifting": "shopping", "zoo": "zoo",
    "groceries": "custom:supermarket", "grocery shopping": "custom:supermarket",
    "grocery store": "custom:supermarket", "supermarket": "custom:supermarket",
    "pharmacy": "custom:pharmacy", "atm": "custom:atm", "bank": "custom:bank",
    "bookstore": "custom:bookstore", "book store": "custom:bookstore",
    "hiking": "hiking", "hike": "hiking", "trail": "hiking", "picnic": "picnic",
    "skating": "skating", "ice skating": "skating", "roller skating": "skating",
    "baseball": "baseball", "baseball game": "baseball", "watch a baseball game": "baseball", "basketball": "basketball", "basketball game": "basketball",
    "football": "football", "football game": "football", "soccer": "soccer", "soccer game": "soccer", "soccer match": "soccer",
    "hockey": "hockey", "hockey game": "hockey", "sports event": "sports", "sporting event": "sports", "sports game": "sports",
    "concert": "concert", "live music": "concert", "gig": "concert",
    "theater": "theater", "theatre": "theater", "play": "theater", "musical": "musical", "musical theater": "musical",
    "ballet": "ballet", "opera": "opera", "comedy": "comedy", "comedy show": "comedy", "stand-up": "comedy",
}
def activity_category(phrase):
    import unicodedata
    text = unicodedata.normalize("NFKC", phrase).casefold().strip()
    text = re.sub(r'\s+(?:afterward|afterwards|first|finally)$','',text)
    text = re.sub(r"^(?:(?:go to|stop at|stop for|go|show|watch|see|visit|try|do|take|have|enjoy|get|buy|grab|pick up|play)\s+)(?:a |an |the )?", "", text)
    text = re.sub(r"^(?:a|an|the)\s+", "", text).strip()
    if text in ('coffee shop','coffee shops'):
        return 'coffee'
    mentioned={ALIASES[m.group().casefold()] for m in OCCURRENCES.finditer(text)}
    if len({a for a in mentioned if a.startswith('custom:')})>1:
        return None
    from backend.retail import intent as retail_intent
    if retail_intent(text) and text not in ALIASES:
        return "custom:" + text if len(text)<=100 else None
    if text in ALIASES:
        return ALIASES[text]
    # An extractor may accidentally put two stops in one phrase. Do not let a
    # movie keyword or a custom query swallow another explicit activity.
    mentioned={ALIASES[m.group().casefold()] for m in OCCURRENCES.finditer(text)}
    if len(mentioned)>1 or mentioned and re.search(r"\band\b|\bthen\b|\bfollowed by\b",text):
        return None
    if re.search(r"\b(?:movies?|films?|cinema)\b", text):
        return "movie"
    if re.search(r"\bconcert\b", text):
        return "concert"
    if re.search(r"\b(?:something|somewhere|anything|whatever|fun|activities|competitive|indoor)\b", text):
        return None
    text = re.sub(r"[^a-z0-9 '-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Modest grammatical normalization, not a finite list of supported outings.
    text = re.sub(r"\bclasses$", "class", text)
    if len(text)>4 and text.endswith('s') and not text.endswith(('ss','us')):
        text=text[:-1]
    if not re.fullmatch(r"[a-z][a-z0-9 '-]{1,99}", text):
        return None
    return "custom:" + text


# Semantic guard only: if AI drops/reorders a clear catalog occurrence, refuse.
# Never constructs an interpretation or sends a keyword-derived plan.
OCCURRENCES = re.compile(r"\b(?:" + "|".join(re.escape(a) for a in sorted(ALIASES, key=len, reverse=True)) + r")\b", re.I)

class ManualPreferences(ContractModel):
    location: str = ""
    date: str = ""
    people: str = ""
    budget: str = ""
    travel: str = ""
    cost: CostPreference = CostPreference.balanced
    costExplicit: bool = Field(default=False, strict=True)
    transport: Literal["", "driving", "walking"] = ""


LOCATION_QUESTION = "Where would you like to go? Enter a city or location to continue."


ClarificationField = Literal["location", "people", "date", "activities", "time", "endpoint"]


class ClarificationAnswers(ContractModel):
    endpoint: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=80)
    people: str = Field(default="", max_length=80)
    date: str = Field(default="", max_length=100)
    activities: str = Field(default="", max_length=500)
    time: str = Field(default="", max_length=150)


class PendingClarification(ContractModel):
    # Browser memory only. All supplied state is revalidated, never trusted as a plan.
    text: Annotated[Nonblank, Field(max_length=4000)]
    interpretation: Interpretation
    answers: ClarificationAnswers = Field(default_factory=ClarificationAnswers)
    referenceTime: AwareDatetime


class ClarificationQuestion(ContractModel):
    field: ClarificationField
    question: str
    kind: Literal["essential", "ambiguous"] = "essential"
    reason: CalendarReason | None = None
    helpText: str | None = None


class InterpretationInput(ContractModel):
    text: Annotated[Nonblank, Field(max_length=4000)]
    preferences: ManualPreferences = Field(default_factory=ManualPreferences)
    calendarTimezone: str | None = Field(default=None,max_length=100)

    @field_validator("calendarTimezone")
    @classmethod
    def valid_calendar_timezone(cls, value):
        return DestinationContext(originalText="", timezone=value).timezone
    hasCurrentLocation: bool = Field(default=False, strict=True)
    pending: PendingClarification | None = None
    answers: ClarificationAnswers = Field(default_factory=ClarificationAnswers)


class InterpretationContext(ContractModel):
    """Existing resolved preferences retained when execution is unavailable.

    No coordinates, provider resolution, guessed start time or persistence.
    Original outing clock wording remains in Interpretation.time_expressions.
    """
    dateIssues: list[str] = Field(default_factory=list)
    destination: str | None = None
    date: CalendarDate | None = None
    timezone: str | None = None
    timezoneBasis: Literal['destination_calendar', 'browser_reported', 'unknown'] = 'unknown'
    transport: TransportationMode | None = None
    firstTravel: FirstTravel | None = None
    betweenTravel: FirstTravel | None = None
    geography: Geography | None = None
    # Existing travel-only caps; distinct from Journey.total_duration.
    travel: int | None = Field(default=None, strict=True, ge=0, le=1440)
    travelExclusive: bool = Field(default=False, strict=True)
    maxLegTravel: int | None = Field(default=None, strict=True, ge=0, le=1440)
    maxLegTravelExclusive: bool = Field(default=False, strict=True)
    # Explicit departure evidence only; default/earliest planning bounds do not qualify.
    departureMinute: int | None = Field(default=None, strict=True, ge=0, lt=1440)
    departureSource: str | None = Field(default=None, max_length=100)
    departureNow: bool = False
    departureInstant: AwareDatetime | None = None
    originText: str | None = None
    endpointAnswer: str | None = Field(default=None, max_length=200, repr=False)
    endpointStatus: Literal["origin_confirmed", "location_needs_verification"] | None = None
    issues: list[str] = Field(default_factory=list)


class InterpretationResult(ContractModel):
    interpretation: Interpretation
    request: PlanningRequest | None
    notes: list[str]
    issues: list[str]
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    pending: PendingClarification | None = None
    unsupported: list[str] = Field(default_factory=list)
    context: InterpretationContext | None = None
    executionStatus: Literal["advanced_unavailable", "clarification_required"] | None = None
    advancedToken: str | None = Field(default=None, repr=False)


# These bounded source checks validate explicit evidence; they never construct
# an extraction. Unrecognized language remains the provider's responsibility.
MONEY_EVIDENCE = re.compile(
    r"(?:[$€£¥₹]|\b(?:USD|EUR|GBP|CAD|AUD|INR|JPY)\s*|(?=-?\d[\d,]*(?:\.\d+)?\s*(?:dollars?|USD)\b))"
    r"\s*(-?\d[\d,]*(?:\.\d+)?)\s*(?:(?:dollars?|USD)\s*)?"
    r"(per[ -]person|per head|each|a person|a head|total|for (?:the |our )?(?:whole )?group)?", re.I)
LOCATION_ALTERNATIVES = re.compile(r"\bin\s+[a-z]+(?:\s+[a-z]+)?\s+(?:or|and in)\s+[a-z]+", re.I)


def has_minimum_spending(raw):
    # “No more than” is a maximum, not a minimum.
    spending_text = re.sub(r"\b(?:no|not) more than\b", "at most", raw, flags=re.I)
    return bool(re.search(r"\b(?:minimum|at least|no less than|more than)\s*(?:[$€£¥₹]|(?:USD|EUR|GBP)\s*|\d+(?:\.\d+)?\s*(?:dollars|per person|each))", spending_text, re.I))


def source_constraint_issues(raw, ai, manual, answers, ask):
    issues = []
    def issue(message):
        if message not in issues:
            issues.append(message)

    if not (manual.location.strip() or answers.location) and LOCATION_ALTERNATIVES.search(raw):
        issue("More than one location was stated. Choose one city for this outing.")
        ask("location", LOCATION_QUESTION, "ambiguous")

    # Numeric costs are retained for compatibility, never requested as missing
    # details. Real prices/currencies cannot be verified by venue discovery.
    from backend.provider_budget import local_real_enabled
    if not local_real_enabled():
        # A minimum is not the planner's maximum-cap contract. Never reinterpret it.
        minimum_spending = has_minimum_spending(raw)
        if minimum_spending:
            issue("Minimum spending requirements are unsupported and may conflict with your maximum. Edit the request to remove the minimum and state the maximum USD budget per person or for the group. No plan was generated.")
        money = {"budget_per_person": [], "budget_group": []}
        for match in ([] if minimum_spending else MONEY_EVIDENCE.finditer(raw)):
            if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", match[1]):
                issue("The budget amount is unclear. Use an amount such as $60 per person or $1,000 total.")
                continue
            amount = float(match[1].replace(",", ""))
            scope = (match[2] or "").lower()
            prefix = raw[max(0, match.start() - 25):match.start()].lower()
            group = scope == "total" or "group" in scope or bool(re.search(r"(?:group (?:budget|cap)|total budget)\s*$", prefix))
            money["budget_group" if group else "budget_per_person"].append(amount)
            if not scope and not group and not manual.budget.strip():
                issue("Budget scope is unclear. State USD per person or a total group budget, or set Maximum budget.")
        for field, amounts in ([] if minimum_spending else money.items()):
            if field == "budget_per_person" and manual.budget.strip():
                continue
            amount = getattr(ai, field)
            if (amounts and (any(n < 0 for n in amounts) or amount != min(amounts))) or (amount is not None and not amounts):
                issue("The budget amount or its per-person/group meaning was not captured correctly. State one maximum USD amount per person and/or one total group cap.")

    first_preference, first_spans, first_problem = first_intent(raw)
    if first_problem: issue(first_problem)
    between,between_spans,between_problem=between_intent(raw)
    if between_problem:issue(between_problem)
    travel_raw = raw
    for begin,end,_ in sorted(first_spans,reverse=True):
        travel_raw=travel_raw[:begin]+" "*(end-begin)+travel_raw[end:]
    if between and (between.unit=='miles' or between.mode=='flexible'):
        if ai.travel_leg_minutes is not None and ai.travel_leg_minutes!=between.value:
            issue("The extracted between-activity amount conflicts with the stated preference.")
        else:ai.travel_leg_minutes=None
        travel_raw=mask(travel_raw,between_spans)
    if first_preference:
        remaining = travel_evidence(travel_raw)
        for field,scope in [('travel_leg_minutes','leg'),('travel_total_minutes','total')]:
            if getattr(ai,field)==first_preference.value and not any(m['scope']==scope for m in remaining):
                setattr(ai,field,None)
    travel_context = CONTEXT.search(travel_raw)
    if travel_context and re.search(r"\d+\s*(?:seconds?|secs?|meters?|metres?|feet|yards?)\b", raw, re.I):
        issue("That travel unit is unsupported. State a maximum travel time in minutes or hours, total or between stops.")
    if travel_context and re.search(r"\b(?:minimum|at least)\s+\d+\s*(?:minutes?|hours?)", raw, re.I):
        issue("Minimum travel requirements are unsupported. State a maximum travel time instead.")
    travel_matches = travel_evidence(travel_raw)
    if travel_context and not travel_matches and re.search(r"\d[^.;]{0,20}\b(?:minutes?|mins?|hours?|hrs?)\b", travel_raw, re.I):
        issue("The travel amount or its total/between-stops meaning is unclear. Use a number of minutes or hours and name the limit's scope.")
    supported_travel = {"travel_total_minutes": [], "travel_leg_minutes": []}
    for match in travel_matches:
        if match['distance']:
            issue("Travel distance limits are unsupported. State a maximum travel time in minutes, total, between stops or from your starting point.")
            continue
        if match['scope'] == 'first':
            continue
        if not travel_context and match['scope'] == 'total':
            issue("An overall outing-duration limit cannot be treated as travel. State an overall start and end time instead.")
            continue
        field = "travel_leg_minutes" if match['scope'] == 'leg' else "travel_total_minutes"
        if field == "travel_total_minutes" and manual.travel.strip():
            continue
        supported_travel[field].append(match['amount'])
    for field, amounts in supported_travel.items():
        if field == "travel_total_minutes" and manual.travel.strip():
            continue
        value = getattr(ai, field)
        if (amounts and (any(n < 0 for n in amounts) or value != min(amounts))) or (value is not None and not amounts):
            issue("The travel limit or its total/between-stops meaning could not be verified. State a maximum number of minutes total travel or between stops.")
    if re.search(r"\b(?:travel|between stops|between activities)\b", travel_raw, re.I) and re.search(r"\b(?:miles?|kilometers?|km)\b", travel_raw, re.I):
        issue("Travel distance limits are unsupported. State a maximum travel time in minutes, total or between stops.")
    if not (manual.costExplicit or manual.cost != CostPreference.balanced):
        evidence = {"budget": r"\b(?:affordable|cheap|budget.friendly|low.cost)\b", "balanced": r"\bbalanced\b", "experience": r"\b(?:best experience|premium|upscale|luxury|high quality)\b"}
        stated = {mode for mode, pattern in evidence.items() if re.search(pattern, raw, re.I)}
        inferred = ai.cost.value if ai.cost else None
        if len(stated) > 1 or (stated and stated != {inferred}):
            issue("The spending preference is conflicting or was not captured correctly. Choose Budget-friendly, Balanced or Best experience in preferences.")
        elif ai.cost and not re.search({"budget": r"affordable|cheap|budget.friendly|low.cost|on a budget|budget (?:mode|preference|outing)", "balanced": r"balanced|balance", "experience": r"experience|quality|premium|upscale|luxury"}[ai.cost.value], raw, re.I):
            issue("A spending preference could not be verified in your words. State Budget-friendly, Balanced or Best experience, or choose it in preferences.")
    from backend.provider_budget import local_real_enabled
    required_access=bool(re.search(r"\b(?:must|require|need)\b[^.;]{0,50}\bwheelchair(?: accessible| access)?\b",raw,re.I))
    essential=re.search(r"\b(?:must|require|need)\b[^.;]{0,50}\b(?:wheelchair|accessible|vegan|halal|kosher|private room)\b", raw, re.I)
    if essential and not (required_access and local_real_enabled() and not re.search(r"\b(?:vegan|halal|kosher|private room)\b",raw,re.I)):
        issue("The catalog cannot verify your accessibility, dietary or venue requirement. Edit the request to remove it only if it is optional; otherwise this prototype cannot safely plan it.")
    return issues


def advanced_travel_fields(raw, manual):
    """Carry existing bounded travel-only scopes into the advanced handoff."""
    values, issues = {}, []
    evidence = travel_evidence(raw)
    for scope, field in [('total', 'travel'), ('leg', 'maxLegTravel'), ('first', 'first_limit')]:
        matches = [e for e in evidence if e['scope'] == scope]
        if scope == 'total' and manual.travel.strip():
            text = manual.travel.strip()
            if not re.fullmatch(r'\d+', text) or int(text) > 1440:
                issues.append('The total between-stop travel cap must be 0–1440 whole minutes.')
            else:
                values['travel'] = int(text)
                values['travelExclusive'] = False
            continue
        minutes = [e['amount'] for e in matches if not e['distance']]
        if any(not n.is_integer() or not 0 <= n <= 1440 for n in minutes):
            issues.append('Travel-only time caps must be 0–1440 whole minutes.')
            continue
        if minutes:
            values[field] = int(min(minutes))
            if scope != 'first':
                values[field + 'Exclusive'] = exclusive_limit(raw, scope)
        supported_distance = (first_intent(raw)[0] if scope == 'first' else
                              between_intent(raw)[0] if scope == 'leg' else None)
        if any(e['distance'] for e in matches) and supported_distance is None:
            issues.append('This travel-distance scope is unsupported; it was not silently ignored.')
    return values, issues


def interpret_request(value: InterpretationInput, provider: AIProvider | None = None, *,
                      now: datetime | None = None) -> InterpretationResult:
    saved = value.pending if value.pending and value.pending.text == value.text else None
    reference = saved.referenceTime if saved else now or datetime.now(timezone.utc)
    ai = saved.interpretation.model_copy(deep=True) if saved else (provider if provider is not None else create_provider()).interpret(value.text)
    ai = Interpretation.model_validate(ai).model_copy(deep=True)
    answers = saved.answers.model_copy(deep=True) if saved else ClarificationAnswers()
    if saved:
        for key, answer in value.answers.model_dump().items():
            if answer.strip():
                if key == 'date':
                    context = answers.date or saved.text
                    answer = complete_year_answer(context, answer.strip())
                setattr(answers, key, answer.strip())
    raw, manual = value.text, value.preferences
    activity_raw = raw
    activity_answer_issue = None
    if answers.activities:
        # This is an explicit correction of the desired stop list, never a model suggestion.
        activity_raw = answers.activities
        replacements = [phrase.strip() for phrase in re.split(r",|\bthen\b|\band\b", activity_raw, flags=re.I) if phrase.strip()]
        unknown = [phrase for phrase in ai.activities if activity_category(phrase) is None]
        if unknown and any(activity_category(phrase) is not None for phrase in ai.activities):
            if len(replacements) == len(unknown):
                choices = iter(replacements)
                ai.activities = [next(choices) if phrase in unknown else phrase for phrase in ai.activities]
                activity_raw = ", then ".join(ai.activities)
            else:
                activity_answer_issue = "Choose one activity for each unclear stop; your other activities are kept."
                activity_raw = raw
        else:
            ai.activities = replacements
        ai.suggested_activities = []
    questions = []
    unsupported = []

    def ask(field, question, kind="essential", *, reason=None, help_text=None):
        item = ClarificationQuestion(field=field, question=question, kind=kind,
                                     reason=reason, helpText=help_text)
        for index, existing in enumerate(questions):
            if existing.field == field:
                if reason is not None:
                    questions[index] = item
                return
        questions.append(item)

    grounding_issues = [activity_answer_issue] if activity_answer_issue else []
    # Unspecified core facts must not acquire model defaults. Conservative
    # grounding is validation only; it never extracts a replacement value.
    if ai.location is not None and ai.location.casefold() not in raw.casefold():
        ai.location = None
    if ai.location:
        # Retain a more specific source destination when the model shortened it.
        # This validates the same location clause, not invented neighborhood data.
        for match in re.finditer(r"\bin\s+([^.!?]+?)(?=\s+on\b|\s+for\s+\d|,\s*(?:tomorrow|today|on\b)|[.!?]|$)", raw, re.I):
            clause=re.split(r'\s+(?:near|today|tomorrow|this|next|on|from|at|with|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|July|August|September|October|November|December)\b',match[1],flags=re.I)[0].strip(' ,')
            if (len(clause)<=80 and len(clause)>len(ai.location)
                    and re.search(r'\b'+re.escape(ai.location)+r'\b',clause,re.I)
                    and not re.search(r'\b(?:minutes?|miles?|people|prefer|starting|only|no|and|followed)\b|\d',clause,re.I)):
                ai.location=clause
                break
    ai.people = None  # Legacy extension only; never a planning requirement.
    # Removing unsupported cost questions does not authorize model-invented caps.
    if local_real_enabled() and not re.search(r"[$€£¥₹]|\b(?:budget|spend|cost|price|USD|EUR|GBP|CAD|AUD|INR|JPY|dollars?|rupees?)\b",raw,re.I):
        ai.budget_per_person=ai.budget_group=None
        ai.currency=None
    if local_real_enabled():
        from decimal import Decimal
        source_amounts={Decimal(m[1].replace(',', '')) for m in MONEY_EVIDENCE.finditer(raw)}
        for field in ('budget_per_person','budget_group'):
            amount=getattr(ai,field)
            if amount is not None and Decimal(str(amount)) not in source_amounts:
                setattr(ai,field,None)
    other_currency = re.search(r"[€£¥₹]|\b(?:EUR|GBP|CAD|AUD|NZD|HKD|SGD|MXN|INR|JPY|CNY|CHF|SEK|NOK|DKK|ZAR|BRL|KRW|RUB|Canadian|Australian|pesos?|rupees?|yen|yuan)\b", raw, re.I)
    if (not manual.budget.strip() or ai.budget_group is not None) and ai.currency == "USD" and other_currency and not local_real_enabled():
        grounding_issues.append("The request names a non-USD currency. This catalog cannot convert currency.")
    # Existing catalog policy: an unqualified $ amount denotes USD. Restore
    # this explicit source evidence; scope/amount checks below still apply.
    # Never convert an explicitly different currency or invent a budget.
    if (ai.currency is None and (ai.budget_per_person is not None or ai.budget_group is not None)
            and re.search(r"\$\s*\d", raw) and not other_currency):
        ai.currency = "USD"
    ai.preferences = [phrase for phrase in ai.preferences if phrase.casefold() in raw.casefold()]
    if ai.cost is None and any(p.casefold() in {"affordable", "cheap", "low-cost", "budget-friendly"} for p in ai.preferences):
        ai.cost = CostPreference.budget
    ai.date_expressions = [phrase for phrase in ai.date_expressions if phrase.casefold() in raw.casefold()]
    ai.time_expressions = [phrase for phrase in ai.time_expressions if phrase.casefold() in raw.casefold()]
    if ai.journey and ai.location and any(s.kind=='named_place' and s.source.casefold()==ai.location.casefold() for s in ai.journey.stops):
        # A requested establishment does not establish the outing's city/area.
        ai.location = None
    from backend.journey import validate_journey, is_reference_occurrence
    # Follow-up activity corrections must not erase original advanced constraints.
    journey_ai = saved.interpretation.model_copy(deep=True) if saved else ai
    journey_issue, ambiguous_journey = validate_journey(raw, journey_ai)
    if saved:
        ai.journey = journey_ai.journey
    if journey_issue:
        if saved:
            ai.activities = journey_ai.activities
        # Calendar context stays separate from deadlines; a deadline cannot
        # silently become an outing start/end window or an invented start time.
        calendar_raw = raw
        if ai.journey and ai.journey.deadline:
            clause=ai.journey.deadline.source
            protected=[m.span() for m in DATE_WORDING.finditer(clause)]
            protected += [m.span() for m in re.finditer(r'[+-]\d{2}:\d{2}',clause)]
            masked=TIME_WORDING.sub(lambda m: m[0] if any(a<m.end() and m.start()<b for a,b in protected) else ' '*len(m[0]),clause)
            calendar_raw = calendar_raw.replace(clause,masked)
        calendar = resolve_datetime(calendar_raw, ai.date_expressions, [],
            manual.location.strip() or ai.location, manual_date=manual.date.strip(),
            now=reference, calendar_timezone=value.calendarTimezone if ai.location=='near me' else None)
        ai.date_expressions = calendar.date_expressions
        ai.time_expressions = calendar.time_expressions
        destination = manual.location.strip() or ai.location
        first, _, first_problem = first_intent(raw)
        between, _, between_problem = between_intent(raw)
        from backend.travel_mode import resolve_mode
        mode, mode_problems = resolve_mode(raw, ai.transport, manual.transport)
        # Same explicit-origin wording used by the existing client, extended to
        # its already-supported 'start from' form. It is never an address lookup.
        origin = re.search(r'\b(?:start|starting) from\s+([^.,;!?]+?)(?=\s+(?:today|tomorrow|for \d)|[.,;!?]|$)',raw,re.I)
        # Retain existing travel-only scopes even when ordinary execution is gated.
        # Source grammar is the same as the ordinary planner; no new AI extraction.
        travel_fields, travel_issues = advanced_travel_fields(raw, manual)
        first_limit = travel_fields.pop('first_limit', None)
        if first is None and first_limit is not None:
            first = FirstTravel(value=float(first_limit), exclusive=exclusive_limit(raw, 'first'))
        context = InterpretationContext(destination=destination,date=calendar.date,dateIssues=[p.message for p in calendar.problems if p.field=='date'],
            timezone=calendar.timezone,transport=mode,firstTravel=first,
            timezoneBasis='browser_reported' if ai.location=='near me' else 'destination_calendar' if calendar.timezone != 'UTC' else 'unknown',
            betweenTravel=between,geography=geographic_intent(raw,destination),
            originText=origin[1].strip() if origin else first.originText if first else None,
            **travel_fields,
            issues=[p for p in [first_problem,between_problem,*mode_problems,*calendar.issues,*travel_issues] if p])
        from backend.advanced_timing import explicit_departure
        context.departureMinute, context.departureSource = explicit_departure(calendar_raw)
        context.departureNow = bool(re.search(r"\bnow\b", calendar_raw, re.I)) and context.departureMinute is None
        from backend.journey import ambiguous_return, missing_return_confirmation
        home_question = ai.journey and (missing_return_confirmation(raw,ai.journey) or ai.journey.endpoint and (ai.journey.endpoint.kind=='home' or ambiguous_return(ai.journey.endpoint))) and journey_issue.startswith('Where should the outing end?')
        if home_question:
            answer = answers.endpoint.strip()
            origin_answer = answer.casefold() == 'return to my starting point'
            # Syntactic acceptance only: an address/name still needs provider
            # identity verification. It never establishes coordinates or a route.
            valid = origin_answer or (3 <= len(answer) <= 200 and bool(re.search(r'[a-zA-Z]',answer))
                and not re.fullmatch(r'(?:home|my home|here|there|yes|no|unknown|current location)',answer,re.I)
                and not any(ord(c)<32 for c in answer))
            if not valid:
                question = ('That answer does not identify an endpoint. ' if answer else '') + 'Where should the outing end? Enter a home address or named location, or choose Return to my starting point.'
                return InterpretationResult(interpretation=ai,request=None,notes=[],issues=[question],context=context,
                    executionStatus='clarification_required',
                    questions=[ClarificationQuestion(field='endpoint',question=question,helpText='Used only for this request; not saved. A named location still needs place verification.')],
                    pending=PendingClarification(text=value.text,interpretation=ai,answers=answers,referenceTime=reference))
            if ai.journey.endpoint is None:
                from backend.journey import Endpoint
                ai.journey.endpoint=Endpoint(kind='origin' if origin_answer else 'home',source=re.search(r'\bbe back\b',raw,re.I).group())
            context.endpointAnswer=answer
            context.endpointStatus='origin_confirmed' if origin_answer else 'location_needs_verification'
            from backend.journey import LIMITATION
            journey_issue, ambiguous_journey = LIMITATION, False
        return InterpretationResult(interpretation=ai, request=None, notes=[],
            context=context, executionStatus='clarification_required' if ambiguous_journey else 'advanced_unavailable',
            pending=PendingClarification(text=value.text,interpretation=ai,answers=answers,referenceTime=reference) if not ambiguous_journey else None,
            issues=[journey_issue], unsupported=[] if ambiguous_journey else [journey_issue])
    if saved and answers.activities and ai.journey:
        # Original advanced semantics were checked above and cannot be erased.
        # A deliberate simple activity-list correction has its own source text
        # in pending.answers; retain that provenance alongside the original.
        from backend.journey import Journey, RequestedStop, OrderConstraint
        ai.journey = Journey(stops=[RequestedStop(source=p) for p in ai.activities],
            order=[OrderConstraint(before=i,after=i+1,source=answers.activities) for i in range(len(ai.activities)-1)],
            ordering='constrained' if len(ai.activities)>1 else 'unspecified')
    normalize_verbatim_travel(raw, ai)
    # Uncertainties stay blocking unless the corresponding explicit correction resolves them.
    uncertainties = []
    validation_notes = []
    for issue in ai.uncertainties:
        # These exact, grounded clauses are representable by existing controls;
        # they are requirements to retain, not unresolved destination facts.
        if local_real_enabled():
            origin_clause=re.search(r"\bstart from [^.;!?]+",raw,re.I)
            if (origin_clause and issue.casefold()==origin_clause[0].casefold() and ai.location
                    and re.search(r"\bin\s+"+re.escape(ai.location)+r"\b",raw[:origin_clause.start()],re.I)
                    and not re.search(r"\d|minutes?|miles?",issue,re.I)):
                validation_notes.append("Your stated starting place is kept for explicit lookup and confirmation; it is separate from the destination.")
                continue
            if (re.fullmatch(r"wheelchair (?:access|accessible)",issue,re.I)
                    and re.search(r"\b(?:must|require|need)\b[^.;]{0,50}\bwheelchair\b",raw,re.I)):
                validation_notes.append("Required wheelchair access is retained and must be verified for each venue; unknown support is not confirmed access.")
                continue
        if local_real_enabled() and re.search(r"budget|currency|price|cost|spending",issue,re.I) and not re.search(r"travel|minutes|miles|location|date|wheelchair",issue,re.I):
            validation_notes.append("Cost preferences are noted, but prices, currency conversion and budget compliance are not verified.")
            continue
        if re.search(r"people|participants?|party|group|persons", issue, re.I) and not re.search(r"budget|currency|price|cost|spending", issue, re.I):
            continue
        # A bare schema field with null is an absent optional value, not an
        # independent user requirement. Source checks below still reject any
        # explicit cap omitted by the model, including wrong scopes/amounts.
        if issue.strip().casefold() in {"budget_per_person", "budget_group", "travel_total_minutes", "travel_leg_minutes"} and getattr(ai, issue.strip().casefold()) is None:
            continue
        if resolved_travel_label(issue, raw, ai):
            continue
        # The concrete unsupported minimum explains recovery without competing
        # model-dependent guesses about amount or scope. It remains blocking.
        if has_minimum_spending(raw) and re.search(r"budget|currency|price|cost|spending", issue, re.I):
            continue
        # Some providers repeat a supported, already-resolved mode as a bare
        # uncertainty. Only exact grounded labels with matching extraction clear;
        # actual questions/conflicts and unverified venue qualities still block.
        resolved_modes = {"best experience": CostPreference.experience,
                          "budget-friendly": CostPreference.budget,
                          "balanced": CostPreference.balanced}
        label = issue.strip().casefold()
        # Mode is optional or explicitly selected in the UI; a bare absent-field
        # uncertainty must not require the model to invent it. Conflicts are
        # independently checked by resolve_mode below.
        if re.fullmatch(r"(?:transport(?:ation)?(?: mode)?|travel mode)(?: (?:is )?(?:unspecified|unknown|not (?:specified|provided)))?",label):
            continue
        fp, spans, problem = first_intent(raw)
        if fp and not problem and label.strip(' .') in {raw[a:b].strip(' .').casefold() for a,b,_ in spans}:
            continue
        bp,bspans,bproblem=between_intent(raw)
        if bp and not bproblem and label.strip(' .') in {raw[a:b].strip(' .').casefold() for a,b,_ in bspans}:continue
        if re.fullmatch(r'(?:no|exclude|excluding|not in) (?:virginia|maryland|district of columbia)',label) and label in raw.casefold():
            continue
        if label in resolved_modes and ai.cost == resolved_modes[label] and label in raw.casefold():
            continue
        # A model may describe absent optional settings as uncertainty. Absence
        # alone is not a planning requirement; explicit ambiguous caps still block.
        if (re.search(r"budget", issue, re.I) and ai.budget_per_person is None and ai.budget_group is None
                and re.search(r"unknown|unspecified|not (?:provided|specified|stated)|no budget", issue, re.I)):
            if not re.search(r"[$€£]|\b(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b|\bbudget\D{0,15}\d|\d+(?:\.\d+)?\s*(?:each|per person|total)\b|\b(?:under|spend|up to)\s+\d", raw, re.I):
                continue
        if (re.search(r"travel", issue, re.I) and ai.travel_total_minutes is None and ai.travel_leg_minutes is None
                and re.search(r"unknown|unspecified|not (?:provided|specified|stated)|no travel", issue, re.I)):
            if not re.search(r"\b(?:travel|between stops|between activities)\b|\d+\s*(?:minutes?|mins?|hours?)\b", raw, re.I):
                continue
        if ai.cost is None and re.search(r"experience|preference", issue, re.I) and re.search(r"unknown|not (?:provided|specified)|unspecified|missing", issue, re.I):
            continue
        field = None if re.search(r"budget|currency|travel|price|cost", issue, re.I) else next((field for field, pattern in [("people", r"group size|people|party size|number of persons"), ("location", r"location|city"),
                      ("date", r"date|weekend|\byear\b"), ("activities", r"activit|stop|choice"), ("time", r"time|clock")]
                      if re.search(pattern, issue, re.I)), None)
        # The resolver validates/infer years from source wording. A provider's
        # year uncertainty must not force a year question after that succeeds;
        # retain other date uncertainties and all independent semantic guards.
        if field == "date" and re.search(r"\byear\b", issue, re.I):
            continue
        if field and (getattr(answers, field) or (field in {"people", "location", "date"} and getattr(manual, field).strip())):
            continue
        # Provider prose is untrusted diagnostic data. Do not show raw model
        # JSON, schema names or exception text in the website's explanation.
        messages = {
            "people": "The group size is unclear. Confirm how many people are coming.",
            "location": "The location is unclear. Choose one city for this outing.",
            "date": "The outing date is unclear. Choose an exact date to continue.",
            "activities": "The activity choices are unclear. List the stops you want in order, including repeats.",
            "time": "The time window is unclear. State an overall start and end time with AM/PM.",
        }
        if field:
            uncertainties.append(messages[field])
        elif re.search(r"budget|currency|price|cost|experience|preference", issue, re.I):
            uncertainties.append("The budget, currency or spending preference is unclear. State a maximum USD amount per person or for the group, and choose a spending preference if needed.")
        elif re.search(r"travel", issue, re.I):
            uncertainties.append("The travel requirement is unclear. State a maximum time in minutes or hours, total or between stops.")
        else:
            uncertainties.append("Part of your request is unclear or unsupported. Rephrase with explicit activities and constraints; no plan was generated.")
        if field:
            ask(field, {"people": "How many people are coming?", "location": LOCATION_QUESTION,
                        "date": "Which exact date do you mean?", "activities": "Which activities would you like, in order?",
                        "time": "What overall time window do you mean (for example, from 6 PM to 10 PM)?"}[field], "ambiguous")
    from backend.travel_mode import resolve_mode, is_walking_route_phrase
    transport, mode_issues = resolve_mode(raw, ai.transport, manual.transport)
    issues = [*uncertainties, *grounding_issues, *mode_issues, *source_constraint_issues(raw, ai, manual, answers, ask)]
    from backend.retail import intent as retail_intent
    # Validation only: never replace model activities from a keyword fallback.
    # A brand noun alone must not lose its shared-mall/mandatory-format semantics.
    retail_phrases=[retail_intent(p) for p in ai.activities]
    if re.search(r'\b(?:mall with|same mall|only .{0,60}outlets?|no regular stores?)\b',raw,re.I):
        relation=any(p and (p.same_mall or p.destination and p.brands) for p in retail_phrases)
        hard=any(p and p.hard_format for p in retail_phrases)
        if (re.search(r'\b(?:mall with|same mall)\b',raw,re.I) and not relation) or (re.search(r'\bonly .{0,60}outlets?\b|\bno regular stores?\b',raw,re.I) and not hard):
            issues.append('The retail relationship or required store format was not preserved. Restate the full store or mall requirement.')
            ask('activities','Which store or mall requirement should each stop preserve? Include the brand and any required mall or outlet format.','ambiguous')
    notes = ["AI interpretation; itinerary calculations use the Python planner and fictional catalog."] + validation_notes
    if ai.preferences:
        notes.append("Stated preferences: " + ", ".join(ai.preferences) + ". Only supported categories and planning constraints are enforced; venue qualities are unverified.")
    if ai.suggested_activities:
        notes.append("AI suggestions, not requested stops: " + ", ".join(a.value for a in ai.suggested_activities) + ". Name the activities you want to include.")

    activities = []
    dinner_stops = []
    cursor = 0
    spans = []
    repeated_uses = {}
    for phrase in ai.activities:
        found = activity_raw.casefold().find(phrase.casefold(), cursor)
        # Explicit multiplicity can reuse its single textual mention as evidence.
        if found < 0:
            repetition = re.search(r"\b" + re.escape(phrase) + r"\s+(twice|two times|2 times|three times|3 times)\b", activity_raw, re.I)
            if repetition:
                limit = 3 if repetition.group(1) in {"three times", "3 times"} else 2
                if repeated_uses.get(phrase.casefold(), 0) < limit:
                    found = repetition.start()
        repeated_uses[phrase.casefold()] = repeated_uses.get(phrase.casefold(), 0) + 1
        category = activity_category(phrase)
        if found < 0:
            issues.append("AI could not verify an ordered activity in your request. Rephrase with explicit stops.")
        else:
            spans.append((found, found + len(phrase)))
            cursor = max(cursor, found + len(phrase))
        if category is None:
            label = f'“{phrase}”' if found >= 0 else "An activity"
            message = "We couldn't tell which activity you meant. Could you be a little more specific?"
            issues.append(message)
            if re.search(r"something|activity|activities|competitive|indoor|fun|anything", phrase, re.I):
                ask("activities", f'Which activity do you mean by “{phrase}”? We’ll keep your other stops.' if found >= 0 and sum(activity_category(p) is None for p in ai.activities) == 1 else "Which activities replace the unclear stops, in order? We’ll keep your other stops.", "ambiguous")
            elif saved and answers.activities:
                ask("activities", "That activity is unsupported. Choose a supported activity for the unclear stop; your original request is kept.", "ambiguous")
            else:
                ask("activities", message, "ambiguous")
        else:
            if phrase.casefold() == "dinner":
                dinner_stops.append(len(activities))
            activities.append(category)
    # Negative/alternative wording needs clarification; do not count it as a stop.
    exclusion_text = re.sub(r"\b(?:no|not) more than\b", "at most", activity_raw, flags=re.I)
    # Supported geographic exclusions are validated separately, never activity negations.
    exclusion_text = re.sub(r"\b(?:no|exclude|excluding|not in)\s+(?:Virginia|Maryland|District of Columbia)\b", " ", exclusion_text, flags=re.I)
    # Location, date and numeric alternatives belong to their own fields.
    exclusion_text = LOCATION_ALTERNATIVES.sub(" ", exclusion_text)
    exclusion_text = re.sub(rf"(?:{DATE_WORDING.pattern})\s+or\s+(?:{DATE_WORDING.pattern})", " ", exclusion_text, flags=re.I)
    number_word = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    exclusion_text = re.sub(rf"\b{number_word}\s+or\s+{number_word}\b", " ", exclusion_text, flags=re.I)
    if any(retail_intent(p) and retail_intent(p).hard_format for p in ai.activities):
        exclusion_text=re.sub(r'\bno regular stores?\b','',exclusion_text,flags=re.I)
    exclusion_text=re.sub(r"\b(?:not|no|without|instead of|rather than|don't|do not)\s+(?:driving|walking)\b", "", exclusion_text, flags=re.I)
    if re.search(r"\b(?:or|instead|not|no|without|avoid|except)\b|n't\b", exclusion_text, re.I):
        issues.append("Alternatives or exclusions need a clear list of desired stops. Rephrase before planning; no substitution was made.")
    for match in OCCURRENCES.finditer(activity_raw):
        if is_reference_occurrence(activity_raw,ai,match):
            continue
        # 'Play soccer/a movie' uses play as a verb, not a theater stop.
        if match.group().casefold() == 'play' and re.match(r'\s+(?:a\s+)?(?:movie|film|soccer|basketball|football|hockey|baseball)\b',activity_raw[match.end():],re.I):
            continue
        # Transport 'walking' is not necessarily a separate requested activity.
        if (match.group().casefold() == "walking" and ai.transport is not None) or is_walking_route_phrase(activity_raw,match.start(),match.end()):
            continue
        multiplicity = re.match(r"\s+(twice|two times|2 times|three times|3 times)\b", activity_raw[match.end():], re.I)
        if multiplicity:
            expected = 3 if multiplicity.group(1).casefold() in {"three times", "3 times"} else 2
            if sum(start < match.end() and match.start() < end for start, end in spans) != expected:
                issues.append("AI did not preserve the explicitly requested repetition count. Rephrase with each stop listed separately.")
        if not any(start < match.end() and match.start() < end for start, end in spans):
            issues.append("AI may have omitted an explicit activity occurrence. Rephrase with each stop in order; nothing was deduplicated or partially planned.")
            break
    if not activities:
        issues.append("Name at least one supported activity; suggestions need your choice before planning.")
    if len(ai.activities) > 4:
        issues.append("This prototype supports up to four stops. No requested occurrence was removed.")

    activity_issues = [issue for issue in issues if any(word in issue for word in
        ("ordered activity", "Alternatives or exclusions", "repetition count", "omitted an explicit activity", "Name at least one"))]
    if activity_issues:
        ask("activities", "Which activities would you like, in order? List each stop, including repeats.", "ambiguous")

    def chosen(name, inferred):
        selected = getattr(manual, name).strip()
        if selected:
            notes.append(f"Manual {name} overrides the text interpretation.")
            return selected
        return inferred

    location = chosen("location", answers.location or ai.location)
    from backend.location_context import relative_destination, RELATIVE
    if not (manual.location.strip() or answers.location) and relative_destination(raw):
        location = "near me"
    first_preference, first_spans, first_problem = first_intent(raw)
    between,between_spans,between_problem=between_intent(raw)
    first_limits = [m['amount'] for m in travel_evidence(raw) if m['scope'] == 'first' and not m['distance']]
    first_limit = None if first_preference and (first_preference.unit=='miles' or first_preference.mode=='flexible') else min(first_limits, default=None)
    if first_limit is not None and (not first_limit.is_integer() or not 0 <= first_limit <= 1440):
        issues.append("The first-stop travel limit must be a whole number of minutes from 0 to 1440.")
        first_limit = None
    if not first_preference and re.search(r"\bnear me\b|\bradius\b", mask(raw,between_spans), re.I) and re.search(r"\d+(?:\.\d+)?\s*(?:miles?|kilometers?|kilometres?|km|meters?|metres?)\b", mask(raw,between_spans), re.I):
        issues.append("Geographic radius wording is not supported in this form. No radius was silently assumed. If you mean road travel to the first stop, state a first-stop limit in miles instead; otherwise revise the geographic requirement.")
    date_raw = raw
    date_phrases = ai.date_expressions
    if answers.date and not manual.date.strip():
        # Replace only the date wording. Independent original clock bounds remain.
        def keep_daypart(match):
            part = re.search(r"(?:evening|night)$", match.group(), re.I)
            return " evening " if match.group().lower() == "tonight" else f" {part.group()} " if part else " "
        date_raw = DATE_WORDING.sub(keep_daypart, raw) + " " + answers.date
        date_phrases = [answers.date]
        if re.search(r"\bnext weekend\b", raw, re.I) and re.fullmatch(r"saturday|sunday", answers.date, re.I):
            date_raw = DATE_WORDING.sub(keep_daypart, raw) + " next " + answers.date
            date_phrases = ["next " + answers.date]
    time_phrases = ai.time_expressions
    if answers.time:
        # Shield dates from the clock-range grammar (11-07 is not a time here).
        date_tokens = []
        def shield(match):
            date_tokens.append(match.group())
            return f" DATE_TOKEN_{len(date_tokens) - 1} "
        date_raw = DATE_WORDING.sub(shield, date_raw)
        date_raw = TIME_WORDING.sub(" ", date_raw)
        for index, token in enumerate(date_tokens):
            date_raw = date_raw.replace(f"DATE_TOKEN_{index}", token)
        date_raw = re.sub(r"\b(?:morning|afternoon|evening|night|overnight)\b", " ", date_raw, flags=re.I)
        date_raw += " " + answers.time
        time_phrases = [answers.time]
    dates = resolve_datetime(date_raw, date_phrases, time_phrases, location,
                             manual_date=manual.date.strip(), now=reference, calendar_timezone=value.calendarTimezone if location=="near me" else None)
    if location=="near me" and value.calendarTimezone:
        dates.notes.append("Nearby calendar uses the browser-reported IANA timezone, not a timezone verified from GPS. Confirm your local calendar if travelling.")
    if saved and dates.date and not dates.issues:
        # Anchor relative dates to the original request, but recheck elapsed time
        # now so a delayed answer cannot schedule a past outing/start.
        current = resolve_datetime(date_raw, date_phrases, time_phrases, location,
            manual_date=dates.date.isoformat(), now=now, calendar_timezone=value.calendarTimezone if location=="near me" else None)
        dates.start, dates.end = current.start, current.end
        dates.issues.extend(current.issues)
        dates.problems.extend(current.problems)
    calendar_fields = set()
    for problem in dates.problems:
        if problem.reason == 'overnight':
            unsupported.append(problem.message)
        elif problem.field not in calendar_fields:
            ask(problem.field, problem.question, "ambiguous",
                reason=problem.reason, help_text=problem.guidance)
            calendar_fields.add(problem.field)
    ai.date_expressions = dates.date_expressions
    ai.time_expressions = dates.time_expressions
    date = chosen("date", dates.date)
    notes.extend(dates.notes)
    issues.extend(dates.issues)
    if ai.date is not None and not dates.date_expressions and not manual.date.strip():
        issues.append("AI returned a date without date evidence. Choose an exact Date in Set preferences.")
    if (ai.start_time is not None or ai.end_time is not None) and not dates.time_expressions:
        issues.append("AI returned a time without original time wording. State an explicit outing window.")
    source_spans = spans if activity_raw == raw else [(raw.casefold().find(phrase.casefold()), raw.casefold().find(phrase.casefold()) + len(phrase))
        for phrase in (saved.interpretation.activities if saved else ai.activities) if phrase.casefold() in raw.casefold()]
    if not answers.time and len(activities) > 1 and any(re.match(r"\s+(?:at|after|before)\s+(?:\d+|noon|midnight)\b", raw[end:], re.I) for _, end in source_spans):
        issues.append("Stop-specific times need clarification. State one overall outing window for this planner.")
        ask("time", "What overall time window should the outing fit in? Include AM/PM.", "ambiguous")
    budget = chosen("budget", ai.budget_per_person)
    travel = chosen("travel", ai.travel_total_minutes)
    cost = manual.cost if manual.costExplicit or manual.cost != CostPreference.balanced else ai.cost or CostPreference.balanced
    if date is None and (not dates.issues or (not dates.date_expressions and not manual.date.strip())):
        questions = [q for q in questions if q.field != "date"]
        issues.append("What day are you planning to go?")
        ask("date", "What day are you planning to go?", reason="missing_date", help_text=DATE_HELP)
    if location is None:
        ask("location", LOCATION_QUESTION)
        issues.append(LOCATION_QUESTION)
    if (ai.budget_per_person is not None or ai.budget_group is not None) and ai.currency != "USD" and not local_real_enabled():
        if ai.budget_group is not None or not manual.budget.strip():
            message = "Budget currency is unknown or unsupported. This fictional catalog uses USD; no conversion was made."
            issues.append(message)
            unsupported.append(message)
    if transport and not local_real_enabled():
        notes.append(f"Requested transport: {transport.value}. Mock travel is mode-independent; no real route or mode-specific time is verified.")
    for field, val in (("budget", budget), ("travel", travel)):
        if isinstance(val, str):
            if not re.fullmatch(r"\d+" if field != "budget" else r"\d+(?:\.\d{1,2})?", val):
                issues.append(f"Enter a valid nonnegative {'whole number' if field != 'budget' else 'amount'} for {field}.")
    if len(ai.activities) > 4:
        unsupported.append("The planner supports up to four stops; edit the request to choose fewer stops.")
    resolved = None
    if not issues:
        try:
            resolved = PlanningRequest(
                activities=activities, activityIntents={category:phrase for category,phrase in zip(activities,ai.activities)}, location=location, date=date,
                calendarTimezone=dates.timezone, explicitStart=dates.explicit_start, explicitEnd=dates.explicit_end,
                destinationContext=DestinationContext(originalText=RELATIVE.search(raw).group() if location=="near me" and RELATIVE.search(raw) else location,intent="current_relative" if location=="near me" else "explicit",source="browser" if location=="near me" and value.calendarTimezone else "request",timezone=dates.timezone),
                budget=float(budget) if budget is not None else None,
                groupBudget=ai.budget_group, travel=int(travel) if travel is not None else None,
                firstTravel=first_preference, betweenTravel=between, geography=geographic_intent(raw,location), maxLegTravel=ai.travel_leg_minutes, maxFirstLegTravel=int(first_limit) if first_limit is not None else None,
                maxLegTravelExclusive=exclusive_limit(raw, "leg"), travelExclusive=not manual.travel.strip() and exclusive_limit(raw, "total"),
                maxFirstLegTravelExclusive=exclusive_limit(raw, "first"), cost=cost, transport=transport,
                startTime=dates.start, endTime=dates.end,
                requireWheelchairAccess=bool(re.search(r"\b(?:must|require|need)\b[^.;]{0,50}\bwheelchair\b",raw,re.I)),
                dinner=bool(dinner_stops), dinnerStops=dinner_stops)
        except (ValueError, TypeError, ValidationError):
            issues.append("Check USD budget (0–100,000/person), travel (0–1440 minutes), and exact date/time. Scheduled events require an exact date.")
    # Keep the original grounded extraction; follow-up corrections remain separate.
    if local_real_enabled() and (ai.budget_per_person is not None or ai.budget_group is not None or re.search(r"budget|affordable|cheap|[$€£₹]",raw,re.I)):
        notes.append("Your cost intent is kept. Actual venue prices and exact budget compliance are not verified; confirm costs directly.")
    original = saved.interpretation if saved else ai.model_copy(deep=True)
    pending = PendingClarification(text=value.text, interpretation=original, answers=answers, referenceTime=reference) if (resolved is not None or (issues and (questions or saved))) and not unsupported else None
    return InterpretationResult(interpretation=ai, request=resolved, notes=notes,
        issues=list(dict.fromkeys(issues)), questions=questions if pending else [],
        pending=pending, unsupported=unsupported)
