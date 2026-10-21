"""AI extraction -> conservative validation/overrides -> resolved planner contract.

Date/time resolution delegates to date_resolution; no itinerary arithmetic lives here.
"""
import re
from datetime import datetime
from typing import Annotated

from pydantic import Field, ValidationError

from backend.date_resolution import resolve_datetime
from backend.ai import AIProvider, Interpretation, create_provider
from backend.models import (ContractModel, CostPreference, Nonblank,
                            OutingRequest)


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


class InterpretationInput(ContractModel):
    text: Annotated[Nonblank, Field(max_length=4000)]
    preferences: ManualPreferences = Field(default_factory=ManualPreferences)


class InterpretationResult(ContractModel):
    interpretation: Interpretation
    request: OutingRequest | None
    notes: list[str]
    issues: list[str]


def interpret_request(value: InterpretationInput, provider: AIProvider | None = None, *,
                      now: datetime | None = None) -> InterpretationResult:
    ai = (provider if provider is not None else create_provider()).interpret(value.text)
    # Validate alternative providers too, rather than trusting a Python annotation.
    ai = Interpretation.model_validate(ai)
    raw, manual = value.text, value.preferences
    grounding_issues = []
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
    issues = [*ai.uncertainties, *grounding_issues]
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
        found = raw.casefold().find(phrase.casefold(), cursor)
        # Explicit multiplicity can reuse its single textual mention as evidence.
        if found < 0:
            repetition = re.search(r"\b" + re.escape(phrase) + r"\s+(twice|two times|2 times|three times|3 times)\b", raw, re.I)
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
            issues.append(f'“{phrase}” is unsupported or needs a specific activity. No partial plan was created.')
        else:
            if phrase.casefold() == "dinner":
                dinner_stops.append(len(activities))
            activities.append(category)
    # Negative/alternative wording needs clarification; do not count it as a stop.
    exclusion_text = re.sub(r"\b(?:no|not) more than\b", "at most", raw, flags=re.I)
    if re.search(r"\b(?:or|instead|not|no|without|avoid|except)\b|n't\b", exclusion_text, re.I):
        issues.append("Alternatives or exclusions need a clear list of desired stops. Rephrase before planning; no substitution was made.")
    for match in OCCURRENCES.finditer(raw):
        # Transport 'walking' is not necessarily a separate requested activity.
        if match.group().casefold() == "walking" and ai.transport is not None:
            continue
        multiplicity = re.match(r"\s+(twice|two times|2 times|three times|3 times)\b", raw[match.end():], re.I)
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

    def chosen(name, inferred):
        selected = getattr(manual, name).strip()
        if selected:
            notes.append(f"Manual {name} overrides the text interpretation.")
            return selected
        return inferred

    if ai.cost is None and any(p.casefold() in {"affordable", "cheap", "low-cost", "budget-friendly"} for p in ai.preferences):
        ai.cost = CostPreference.budget
    location = chosen("location", ai.location)
    people = chosen("people", ai.people)
    dates = resolve_datetime(raw, ai.date_expressions, ai.time_expressions, location,
                             manual_date=manual.date.strip(), now=now)
    ai.date_expressions = dates.date_expressions
    ai.time_expressions = dates.time_expressions
    date = chosen("date", dates.date)
    notes.extend(dates.notes)
    issues.extend(dates.issues)
    if ai.date is not None and not dates.date_expressions and not manual.date.strip():
        issues.append("AI returned a date without date evidence. Choose an exact Date in Set preferences.")
    if (ai.start_time is not None or ai.end_time is not None) and not dates.time_expressions:
        issues.append("AI returned a time without original time wording. State an explicit outing window.")
    if len(activities) > 1 and any(re.match(r"\s+(?:at|after|before)\s+(?:\d+|noon|midnight)\b", raw[end:], re.I) for _, end in spans):
        issues.append("Stop-specific times need clarification. State one overall outing window for this planner.")
    budget = chosen("budget", ai.budget_per_person)
    travel = chosen("travel", ai.travel_total_minutes)
    cost = manual.cost if manual.costExplicit or manual.cost != CostPreference.balanced else ai.cost or CostPreference.balanced
    if location is None:
        issues.append("Location is unknown. Add Baltimore to the request or select it in Set preferences.")
    if people is None:
        issues.append("Group size is unknown. State how many people or set Number of people.")
    if (ai.budget_per_person is not None or ai.budget_group is not None) and ai.currency != "USD":
        if ai.budget_group is not None or not manual.budget.strip():
            issues.append("Budget currency is unknown or unsupported. This fictional catalog uses USD; no conversion was made.")
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
                issues.append(f"Enter a valid nonnegative {'whole number' if field != 'budget' else 'amount'} for {field}.")
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
    return InterpretationResult(interpretation=ai, request=resolved, notes=notes, issues=list(dict.fromkeys(issues)))
