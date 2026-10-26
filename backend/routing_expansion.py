"""Select new directed evidence in bounded stages, without relaxing constraints."""
from backend.routes import plan_matrices
from backend.venue_geography import distance_m


def select_stage(request, known, outing, facts):
    pairs, matrices = plan_matrices(request)
    missing = {key: pair for key, pair in pairs.items() if key not in known}
    capacity = outing.routing_capacity()
    limit = min(64, capacity['elements'], capacity['minuteElements'])
    attempts = capacity['attempts']
    if not missing or not limit or not attempts:
        return [], capacity, len(missing)
    pending_request = request.model_copy(update={'required_pairs': list(missing)})
    _, matrices = plan_matrices(pending_request)
    if len(missing) <= limit and len(matrices) <= attempts:
        return list(missing), capacity, 0

    def proximity(a, b):
        x = a.coordinates or (facts[a.id].coordinates if a.id in facts else None)
        y = b.coordinates or (facts[b.id].coordinates if b.id in facts else None)
        return distance_m(x, y) if x and y else float('inf')

    # Spend evidence on previously under-covered origins, interleaving activity
    # transitions so a single transition cannot swallow the entire stage.
    rows = []
    for origins, destinations in matrices:
        origins = sorted(origins, key=lambda p: (sum(a == p.id for a, _ in known), p.id))
        rows.append([(a, sorted(destinations, key=lambda b: (proximity(a, b), b.id))) for a in origins])
    chosen = []
    for i in range(max((len(r) for r in rows), default=0)):
        for group in rows:
            if i >= len(group):
                continue
            a, destinations = group[i]
            available = limit - len(chosen)
            if not available:
                break
            addition = [(a.id, b.id) for b in destinations[:available]]
            trial = chosen + addition
            _, rectangles = plan_matrices(request.model_copy(update={'required_pairs': trial}))
            if len(rectangles) <= attempts:
                chosen = trial
    return chosen, capacity, len(missing) - len(chosen)
