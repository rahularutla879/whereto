"""Merge transient observations without restoring rejected activity associations."""
from backend.places import DiscoveryResult
from backend.venue_quality import assess_candidates
from backend.planning_diagnostics import merge_discovery_audits


def merge_inventory(old,found,outing):
    observations=old.venues+found.venues
    allowed={(s.provider,s.id,a) for v in observations for s in v.sources for a in v.activities}
    merged=assess_candidates([s for v in observations for s in v.sources])
    retained=[];used={}
    for v in merged.venues:
        accepted=[a for a in v.activities if any((s.provider,s.id,a) in allowed for s in v.sources)
                  and used.get(a,0)<min(100,outing.settings.ceiling('candidates_per_activity'))]
        if accepted:
            retained.append(v.model_copy(update={'activities':accepted}))
            for a in accepted:used[a]=used.get(a,0)+1
    return DiscoveryResult(candidates=[],venues=retained,observed={a:old.observed.get(a,set())|found.observed.get(a,set()) for a in old.observed.keys()|found.observed.keys()},audit=merge_discovery_audits(old,found,retained),
        paging={**old.paging,**found.paging},excluded_count=old.excluded_count+found.excluded_count,
        diagnostics={k:old.diagnostics.get(k,0)+found.diagnostics.get(k,0) for k in old.diagnostics.keys()|found.diagnostics.keys()},
        stages={'latest':found.stages,'retainedCounts':{a.value:n for a,n in used.items()}})
