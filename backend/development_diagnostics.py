"""Small sanitized last-response snapshot, only served behind a local dev gate."""
_snapshot={}
KEYS={'discoveredCounts','shortlistedCounts','evaluatedCombinations','eligibleCombinations','uncheckedCombinations',
      'firstStopVerification','discoveryTargets','rankingAudit','routeOutcomeCounts','placesSearchRequests',
      'placesDetailsRequests','reservedMatrixElements','estimatedOutingGrossUsd','estimatedDayGrossUsd',
      'estimatedUsageWarning','cloudQuotaRemaining','beam','localCoverage'}
def record(result):
    global _snapshot
    if hasattr(result,'diagnostics'):
        _snapshot={key:value for key,value in result.diagnostics.items() if key in KEYS}
def snapshot():return _snapshot.copy()
