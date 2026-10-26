"""Whole-sequence geographic heuristic, never a driving/walking estimate."""
from math import inf
from backend.venue_geography import distance_m


def shortlist(pools, facts, width, start=None):
    def gap(a, b):
        x, y = facts[a.id].coordinates, facts[b.id].coordinates
        return distance_m(x, y) if x is not None and y is not None else inf
    forward = [{} for _ in pools]
    backward = [{} for _ in pools]
    for v in pools[0]:
        point = start.point.coordinates if start else None
        destination = facts[v.id].coordinates
        forward[0][v.id] = distance_m(point, destination) if point and destination else 0
    for i in range(1, len(pools)):
        for v in pools[i]:
            forward[i][v.id] = min((forward[i-1][p.id] + gap(p, v) for p in pools[i-1] if p.id != v.id), default=inf)
    backward[-1] = {v.id: 0 for v in pools[-1]}
    for i in range(len(pools)-2, -1, -1):
        for v in pools[i]:
            backward[i][v.id] = min((backward[i+1][n.id] + gap(v, n) for n in pools[i+1] if n.id != v.id), default=inf)
    return [sorted(pool, key=lambda v: (v.relevanceStrength != 'strong', forward[i][v.id]+backward[i][v.id], v.id))[:width]
            for i, pool in enumerate(pools)]


def expansion_width(settings, stop_count):
    # Bounded computation as well as provider work: at most 20² / 12³ / 10⁴
    # ordered combinations. Routing uses only selectively admitted new pairs.
    return min(settings.candidates_per_activity, {1: settings.candidates_per_activity,
               2: settings.candidates_per_activity, 3: 12, 4: 10}[stop_count])
