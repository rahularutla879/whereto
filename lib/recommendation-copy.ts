// Describe returned options only; never select, reorder or rescore itineraries.
export type RecommendationFacts = {
  score: number | null;
  quality: number | null; // Python's existing normalized venue-quality component.
  cost: number | null;
  travel: number | null;
  venues: { id: string; name: string }[];
};
type Metric = "score" | "quality" | "cost" | "travel";
const close = (a: number | null, b: number | null) => a !== null && b !== null && Math.abs(a - b) < 1e-9;
const known = (n: number | null): n is number => n !== null && Number.isFinite(n) && n >= 0;
const dollars = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);

export function recommendationCopy(plans: RecommendationFacts[], preference: string) {
  function winners(metric: Metric, maximize: boolean, allowAllTied = false) {
    const values = plans.map(plan => plan[metric]);
    // An unknown rival could be better; don't invent a comparative claim.
    if (values.length < 2 || !values.every(known)) return [];
    const best = maximize ? Math.max(...values) : Math.min(...values);
    if (!allowAllTied && values.every(value => close(value, best))) return [];
    return values.flatMap((value, i) => close(value, best) ? [i] : []);
  }
  const top = winners("score", true, true);
  const cheapest = winners("cost", false);
  const quickest = winners("travel", false);
  const quality = winners("quality", true);
  const mode = ({ budget: "Budget-friendly", balanced: "Balanced", experience: "Best Experience" } as Record<string, string>)[preference];

  const explanations = plans.map((plan, i) => {
    const sameValue = plans.findIndex((other, j) => j < i &&
      close(plan.cost, other.cost) && close(plan.travel, other.travel) && close(plan.quality, other.quality));
    if (sameValue >= 0) {
      const other = plans[sameValue];
      const sameSet = plan.venues.map(v => v.id).sort().join("|") === other.venues.map(v => v.id).sort().join("|");
      const changed = plan.venues.findIndex((v, n) => v.id !== other.venues[n]?.id);
      const comparison = `Same cost, travel and sample quality as Option ${sameValue + 1}`;
      if (sameSet && changed >= 0) {
        const difference = changed === 0 ? `starts at ${plan.venues[0].name}` : `visits ${plan.venues[changed].name} at stop ${changed + 1}`;
        return { label: "DIFFERENT STOP ORDER", description: `${comparison}; ${difference}.` };
      }
      const differentVenue = plan.venues.find(v => !other.venues.some(o => o.id === v.id));
      if (differentVenue) return { label: "DIFFERENT VENUES", description: `${comparison}; includes ${differentVenue.name}.` };
      if (sameSet && changed < 0) return { label: "ANOTHER OPTION", description: `Same venues, cost, travel and sample quality as Option ${sameValue + 1}.` };
    }

    // Explain an actual difference in venues, rather than a stock benefit.
    const uniqueVenue = plan.venues.find(v => plans.every((other, j) => j === i || !other.venues.some(o => o.id === v.id)));
    const venueDetail = uniqueVenue ? `Includes ${uniqueVenue.name}.` : plan.venues[0] ? `Starts at ${plan.venues[0].name}.` : "";
    if (top.includes(i)) {
      const tied = top.length > 1;
      const match = mode ? `fit for ${mode}` : "match";
      const reason = quality.includes(i) ? ", with the highest sample venue quality here" : " among these plans";
      return { label: tied ? "JOINT TOP MATCH" : "TOP MATCH", description: `${tied ? "Joint best" : "Best"} ${match}${reason}. ${venueDetail}`.trim() };
    }
    if (cheapest.includes(i)) return {
      label: cheapest.length > 1 ? "JOINT LOWEST COST" : "LOWEST COST",
      description: `${dollars(plan.cost!)} per person, ${cheapest.length > 1 ? "tied for the lowest cost" : "the lowest cost"} of these plans. ${venueDetail}`.trim(),
    };
    if (quickest.includes(i)) return {
      label: quickest.length > 1 ? "JOINT SHORTEST TRAVEL" : "SHORTEST TRAVEL",
      description: `${plan.travel} minutes between stops, ${quickest.length > 1 ? "tied for the shortest travel" : "the shortest travel"} of these plans. ${venueDetail}`.trim(),
    };
    if (quality.includes(i)) return {
      label: quality.length > 1 ? "JOINT TOP SAMPLE VENUES" : "TOP SAMPLE VENUES",
      description: `${quality.length > 1 ? "Joint highest" : "Highest"} sample venue quality of these plans. ${venueDetail}`.trim(),
    };
    const facts = [known(plan.cost) ? `${dollars(plan.cost)} per person` : "", known(plan.travel) ? `${plan.travel} minutes between stops` : ""].filter(Boolean).join(" and ");
    return { label: plans.length === 1 ? "YOUR ITINERARY" : "ALTERNATIVE PLAN",
      description: [venueDetail, facts ? `${facts}.` : ""].filter(Boolean).join(" ") || "An option for the activities you requested." };
  });
  return explanations.map((explanation, i) => {
    // Headline and badge share the same evidence-backed classification. Keep
    // the existing detailed explanation intact underneath the short title.
    const titles: Record<string, string> = {
      "TOP MATCH": "Best Match for You",
      "JOINT TOP MATCH": "Joint Best Match",
      "LOWEST COST": "Lowest Cost per Person",
      "JOINT LOWEST COST": "Lowest Cost (Tie)",
      "SHORTEST TRAVEL": "Shortest Travel Time",
      "JOINT SHORTEST TRAVEL": "Shortest Travel (Tie)",
      "TOP SAMPLE VENUES": "Top Sample Venue Quality",
      "JOINT TOP SAMPLE VENUES": "Top Sample Quality (Tie)",
      "DIFFERENT STOP ORDER": "Same Places, New Order",
      "DIFFERENT VENUES": "Same Value, New Places",
      "ANOTHER OPTION": "Same Plan, Same Value",
      "YOUR ITINERARY": "Your Itinerary",
    };
    let title = titles[explanation.label] ?? "Alternative Itinerary";
    const plan = plans[i];
    if (explanation.label === "JOINT TOP MATCH") {
      // Equal overall scores can still have different prices/travel. State
      // those facts without implying one tied recommendation is uniquely best.
      if (known(plan.cost) && top.some(j => known(plans[j].cost) && !close(plans[j].cost, plan.cost))) {
        title = `Joint Best at ${dollars(plan.cost)}`;
      } else if (known(plan.travel) && top.some(j => known(plans[j].travel) && !close(plans[j].travel, plan.travel))) {
        title = `Joint Best, ${plan.travel}-Min Travel`;
      }
    } else if (explanation.label === "ALTERNATIVE PLAN" && known(plan.cost)) {
      title = `Outing at ${dollars(plan.cost)}`;
    }
    return { ...explanation, title };
  });

}
