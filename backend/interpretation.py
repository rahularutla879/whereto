"""AI extraction -> conservative validation/overrides -> resolved planner contract.

Date/time resolution delegates to date_resolution; no itinerary arithmetic lives here.
"""
import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, ValidationError

from backend.date_resolution import DATE_WORDING, TIME_WORDING, resolve_datetime
from backend.planner import supports_location
from backend.ai import AIProvider, Interpretation, create_provider
from backend.models import (ContractModel, CostPreference, Nonblank,
                            OutingRequest, EVENT_ACTIVITIES)


# Exact phrase normalization, not a fallback text interpreter. Unknown phrases
# are rejected in full; 'skydiving and dinner' cannot become a dinner-only plan.
ALIASES = {
    "bowling": "bowling", "bowl": "bowling",
    "drinks": "drinks", "drink": "drinks", "cocktails": "drinks", "cocktail": "drinks",
    "beer": "drinks", "beers": "drinks", "wine": "drinks", "mocktails": "drinks", "bar": "drinks",
    "movie": "movie", "movies": "movie", "cinema": "movie", "film": "movie",
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
    "hiking": "hiking", "hike": "hiking", "trail": "hiking", "picnic": "picnic",
    "skating": "skating", "ice skating": "skating", "roller skating": "skating",
    "baseball": "baseball", "baseball game": "baseball", "basketball": "basketball", "basketball game": "basketball",
    "football": "football", "football game": "football", "soccer": "soccer", "soccer game": "soccer", "soccer match": "soccer",
    "hockey": "hockey", "hockey game": "hockey", "sports event": "sports", "sporting event": "sports", "sports game": "sports",
    "concert": "concert", "live music": "concert", "gig": "concert",
    "theater": "theater", "theatre": "theater", "play": "theater", "musical": "musical", "musical theater": "musical",
    "ballet": "ballet", "opera": "opera", "comedy": "comedy", "comedy show": "comedy", "stand-up": "comedy",
}
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


ClarificationField = Literal["location", "people", "date", "activities", "time"]


class ClarificationAnswers(ContractModel):
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


class InterpretationInput(ContractModel):
    text: Annotated[Nonblank, Field(max_length=4000)]
    preferences: ManualPreferences = Field(default_factory=ManualPreferences)
    pending: PendingClarification | None = None
    answers: ClarificationAnswers = Field(default_factory=ClarificationAnswers)


class InterpretationResult(ContractModel):
    interpretation: Interpretation
    request: OutingRequest | None
    notes: list[str]
    issues: list[str]
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    pending: PendingClarification | None = None
    unsupported: list[str] = Field(default_factory=list)


def interpret_request(value: InterpretationInput, provider: AIProvider | None = None, *,
                      now: datetime | None = None) -> InterpretationResult:
    saved = value.pending if value.pending and value.pending.text == value.text else None
    reference = saved.referenceTime if saved else now or datetime.now(timezone.utc)
    ai = saved.interpretation.model_copy(deep=True) if saved else (provider if provider is not None else create_provider()).interpret(value.text)
    ai = Interpretation.model_validate(ai)
    answers = saved.answers.model_copy(deep=True) if saved else ClarificationAnswers()
    if saved:
        for key, answer in value.answers.model_dump().items():
            if answer.strip():
                setattr(answers, key, answer.strip())
    raw, manual = value.text, value.preferences
    activity_raw = raw
    activity_answer_issue = None
    if answers.activities:
        # This is an explicit correction of the desired stop list, never a model suggestion.
        activity_raw = answers.activities
        replacements = [phrase.strip() for phrase in re.split(r",|\bthen\b|\band\b", activity_raw, flags=re.I) if phrase.strip()]
        unknown = [phrase for phrase in ai.activities if phrase.casefold() not in ALIASES]
        if unknown and any(phrase.casefold() in ALIASES for phrase in ai.activities):
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

    def ask(field, question, kind="essential"):
        if not any(q.field == field for q in questions):
            questions.append(ClarificationQuestion(field=field, question=question, kind=kind))

    grounding_issues = [activity_answer_issue] if activity_answer_issue else []
    # Unspecified core facts must not acquire model defaults. Conservative
    # grounding is validation only; it never extracts a replacement value.
    if ai.location is not None and ai.location.casefold() not in raw.casefold():
        ai.location = None
    if ai.people is not None:
        words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
        number = rf"(?:{ai.people}" + ("|" + words[ai.people] if ai.people < len(words) else "") + ")"
        evidence = re.search(rf"\b{number}\s+(?:people|friends|persons|colleagues|of us)\b|\b(?:group|party) of {number}\b|\bwe(?:'re| are) {number}\b", raw, re.I)
        if not evidence and not (ai.people == 2 and re.search(r"\bcouple\b", raw, re.I)):
            ai.people = None
    if (not manual.budget.strip() or ai.budget_group is not None) and ai.currency == "USD" and re.search(r"€|£|\b(?:EUR|GBP|euros?|pounds?)\b", raw, re.I):
        grounding_issues.append("The request names a non-USD currency. This catalog cannot convert currency.")
    for field in ("budget_per_person", "budget_group"):
        amount = getattr(ai, field)
        if amount is not None and (not re.search(r"[$€£]|\b(?:budget|USD|EUR|GBP|dollars?|euros?|pounds?|bucks|spend|each|per person|total)\b", raw, re.I) or not any(float(n) == amount for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", raw))):
            setattr(ai, field, None)
            if field == "budget_group" or not manual.budget.strip():
                grounding_issues.append("AI returned a budget without numeric evidence. State the amount and currency explicitly.")
    ai.preferences = [phrase for phrase in ai.preferences if phrase.casefold() in raw.casefold()]
    ai.date_expressions = [phrase for phrase in ai.date_expressions if phrase.casefold() in raw.casefold()]
    ai.time_expressions = [phrase for phrase in ai.time_expressions if phrase.casefold() in raw.casefold()]
    # Uncertainties stay blocking unless the corresponding explicit correction resolves them.
    uncertainties = []
    for issue in ai.uncertainties:
        # A model may describe absent optional settings as uncertainty. Absence
        # alone is not a planning requirement; explicit ambiguous caps still block.
        if re.search(r"budget", issue, re.I) and ai.budget_per_person is None and ai.budget_group is None:
            if not re.search(r"[$€£]|\b(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b|\bbudget\D{0,15}\d|\d+(?:\.\d+)?\s*(?:each|per person|total)\b|\b(?:under|spend|up to)\s+\d", raw, re.I):
                continue
        if re.search(r"travel", issue, re.I) and ai.travel_total_minutes is None and ai.travel_leg_minutes is None:
            if not re.search(r"\b(?:travel|between stops|between activities)\b|\d+\s*(?:minutes?|mins?|hours?)\b", raw, re.I):
                continue
        if re.search(r"experience|preference", issue, re.I) and re.search(r"unknown|not (?:provided|specified)|unspecified|missing", issue, re.I):
            continue
        field = None if re.search(r"budget|currency|travel|price|cost", issue, re.I) else next((field for field, pattern in [("people", r"group size|people|party size|number of persons"), ("location", r"location|city"),
                      ("date", r"date|weekend"), ("activities", r"activit|stop|choice"), ("time", r"time|clock")]
                      if re.search(pattern, issue, re.I)), None)
        if field and (getattr(answers, field) or (field in {"people", "location", "date"} and getattr(manual, field).strip())):
            continue
        uncertainties.append(issue)
        if field:
            ask(field, {"people": "How many people are coming?", "location": "Which city is the outing in?",
                        "date": "Which exact date do you mean?", "activities": "Which activities would you like, in order?",
                        "time": "What overall time window do you mean (for example, from 6 PM to 10 PM)?"}[field], "ambiguous")
    issues = [*uncertainties, *grounding_issues]
    notes = ["AI interpretation; itinerary calculations use the Python planner and fictional catalog."]
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
        category = ALIASES.get(phrase.casefold())
        if found < 0:
            issues.append(f'AI could not ground the ordered activity “{phrase}” in your request. Rephrase with explicit stops.')
        else:
            spans.append((found, found + len(phrase)))
            cursor = max(cursor, found + len(phrase))
        if category is None:
            message = f'“{phrase}” is unsupported or needs a specific activity. No partial plan was created.'
            issues.append(message)
            if re.search(r"something|activity|activities|competitive|indoor|fun|anything", phrase, re.I):
                ask("activities", f'Which activity do you mean by “{phrase}”? We’ll keep your other stops.' if sum(p.casefold() not in ALIASES for p in ai.activities) == 1 else "Which activities replace the unclear stops, in order? We’ll keep your other stops.", "ambiguous")
            elif saved and answers.activities:
                ask("activities", "That activity is unsupported. Choose a supported activity for the unclear stop; your original request is kept.", "ambiguous")
            else:
                unsupported.append(message)
        else:
            if phrase.casefold() == "dinner":
                dinner_stops.append(len(activities))
            activities.append(category)
    # Negative/alternative wording needs clarification; do not count it as a stop.
    exclusion_text = re.sub(r"\b(?:no|not) more than\b", "at most", activity_raw, flags=re.I)
    # Date and numeric alternatives belong to their own clarification fields.
    exclusion_text = re.sub(rf"(?:{DATE_WORDING.pattern})\s+or\s+(?:{DATE_WORDING.pattern})", " ", exclusion_text, flags=re.I)
    number_word = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    exclusion_text = re.sub(rf"\b{number_word}\s+or\s+{number_word}\b", " ", exclusion_text, flags=re.I)
    if re.search(r"\b(?:or|instead|not|no|without|avoid|except)\b|n't\b", exclusion_text, re.I):
        issues.append("Alternatives or exclusions need a clear list of desired stops. Rephrase before planning; no substitution was made.")
    for match in OCCURRENCES.finditer(activity_raw):
        # Transport 'walking' is not necessarily a separate requested activity.
        if match.group().casefold() == "walking" and ai.transport is not None:
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

    if ai.cost is None and any(p.casefold() in {"affordable", "cheap", "low-cost", "budget-friendly"} for p in ai.preferences):
        ai.cost = CostPreference.budget
    location = chosen("location", answers.location or ai.location)
    people_answer = answers.people
    if people_answer:
        words = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
        word_match = re.fullmatch(r"(" + "|".join(words) + r")(?:\s+(?:people|persons?|friends))?", people_answer, re.I)
        if word_match:
            people_answer = str(words.index(word_match[1].lower()))
        match = re.fullmatch(r"(\d+)(?:\s+(?:people|persons?|friends))?", people_answer, re.I)
        people_answer = match[1] if match else people_answer
    people = chosen("people", people_answer or ai.people)
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
                             manual_date=manual.date.strip(), now=reference)
    if saved and dates.date and not dates.issues:
        # Anchor relative dates to the original request, but recheck elapsed time
        # now so a delayed answer cannot schedule a past outing/start.
        current = resolve_datetime(date_raw, date_phrases, time_phrases, location,
            manual_date=dates.date.isoformat(), now=now)
        dates.start, dates.end = current.start, current.end
        dates.issues.extend(current.issues)
    if dates.issues:
        if any(issue.startswith("Date wording") or "selected date" in issue or "Past-date" in issue for issue in dates.issues):
            ask("date", "Which date should we use? Choose Saturday or Sunday for a weekend, or enter YYYY-MM-DD.", "ambiguous")
        if any(not (issue.startswith("Date wording") or "selected date" in issue or "Past-date" in issue) for issue in dates.issues):
            if any("Overnight" in issue for issue in dates.issues):
                unsupported.extend(issue for issue in dates.issues if "Overnight" in issue)
            else:
                ask("time", "What overall time window should we use? Include AM/PM, for example from 6 PM to 10 PM.", "ambiguous")
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
    if any(activity in EVENT_ACTIVITIES for activity in activities) and date is None and not dates.issues:
        issues.append("Scheduled events require an exact date.")
        ask("date", "What date is the event outing? Enter YYYY-MM-DD or a specific day.")
    if location and not supports_location(location.strip()):
        message = "This fictional catalog supports Baltimore only. Edit the location to plan there; no city was substituted."
        issues.append(message)
        if saved and answers.location and not manual.location.strip():
            ask("location", "That city is outside this fictional catalog. Which supported city should we use?", "ambiguous")
        else:
            unsupported.append(message)
    if location is None:
        ask("location", "Which city is the outing in?")
        issues.append("Location is unknown. Add Baltimore to the request or select it in Set preferences.")
    if people is None:
        ask("people", "How many people are coming? (1–100)")
        issues.append("Group size is unknown. State how many people or set Number of people.")
    if (ai.budget_per_person is not None or ai.budget_group is not None) and ai.currency != "USD":
        if ai.budget_group is not None or not manual.budget.strip():
            message = "Budget currency is unknown or unsupported. This fictional catalog uses USD; no conversion was made."
            issues.append(message)
            unsupported.append(message)
    money_mentions = re.findall(r"(?:[$€£]|\b(?:USD|EUR|GBP)\s*)\s*(\d+(?:\.\d+)?)", raw, re.I)
    if money_mentions and not manual.budget.strip():
        extracted_amounts = {ai.budget_per_person, ai.budget_group}
        if any(float(amount) not in extracted_amounts for amount in money_mentions):
            issues.append("AI did not preserve every explicit budget amount. State one per-person cap and/or one group cap.")
        if not re.search(r"\b(?:per person|each|a person|total|group budget|for (?:the |our )?(?:whole )?group)\b", raw, re.I):
            issues.append("Budget scope is unclear. State USD per person or a total group budget, or set Maximum budget.")
    if re.search(r"\b(?:travel|between stops|between activities)\b", raw, re.I) and re.search(r"\d+\s*(?:minutes?|mins?|hours?)\b", raw, re.I):
        if ai.travel_total_minutes is None and ai.travel_leg_minutes is None and not manual.travel.strip():
            issues.append("AI did not capture the stated travel limit. Set Maximum travel time or state a total/per-leg cap clearly.")
    if ai.transport:
        notes.append(f"Requested transport: {ai.transport.value}. Mock travel is mode-independent; no real route or mode-specific time is verified.")
    for field, val in (("people", people), ("budget", budget), ("travel", travel)):
        if isinstance(val, str):
            if not re.fullmatch(r"\d+" if field != "budget" else r"\d+(?:\.\d{1,2})?", val):
                if field == "people":
                    ask("people", "How many people are coming? Enter a whole number from 1 to 100.")
                issues.append(f"Enter a valid nonnegative {'whole number' if field != 'budget' else 'amount'} for {field}.")
    if people is not None and str(people).isdigit() and not 1 <= int(people) <= 100:
        issues.append("Group size must be from 1 to 100.")
        ask("people", "How many people are coming? Enter a whole number from 1 to 100.")
    if len(ai.activities) > 4:
        unsupported.append("The planner supports up to four stops; edit the request to choose fewer stops.")
    resolved = None
    if not issues:
        try:
            resolved = OutingRequest(
                activities=activities, location=location, people=int(people), date=date,
                budget=float(budget) if budget is not None else None,
                groupBudget=ai.budget_group, travel=int(travel) if travel is not None else None,
                maxLegTravel=ai.travel_leg_minutes, cost=cost, transport=ai.transport,
                startTime=dates.start, endTime=dates.end,
                dinner=bool(dinner_stops), dinnerStops=dinner_stops)
        except (ValueError, TypeError, ValidationError):
            issues.append("Check group size (1–100), USD budget (0–100,000/person), travel (0–1440 minutes), and exact date/time. Scheduled events require an exact date.")
    # Keep the original grounded extraction; follow-up corrections remain separate.
    original = saved.interpretation if saved else ai.model_copy(deep=True)
    pending = PendingClarification(text=value.text, interpretation=original, answers=answers, referenceTime=reference) if (resolved is not None or (issues and questions)) and not unsupported else None
    return InterpretationResult(interpretation=ai, request=resolved, notes=notes,
        issues=list(dict.fromkeys(issues)), questions=questions if pending else [],
        pending=pending, unsupported=unsupported)
