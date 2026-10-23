"""Explicit local development command. Never imported by normal app startup."""
import argparse
import json
import sys

from pydantic import ValidationError

from backend.models import ActivityType
from backend.places import (Coordinates, DiscoveryError, DiscoveryRequest, PlacesDiscovery,
                            SearchArea, require_development_discovery)
from backend.provider_budget import ProviderBudget, ProviderLimitError


def main() -> int:
    parser = argparse.ArgumentParser(description="One authorized development-only Google venue search; no retries or pagination.")
    parser.add_argument("--activity", required=True, choices=[a.value for a in ActivityType])
    parser.add_argument("--destination")
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--radius-m", type=float)
    args = parser.parse_args()
    try:
        require_development_discovery()
        coordinates = None
        if args.latitude is not None or args.longitude is not None:
            coordinates = Coordinates(latitude=args.latitude, longitude=args.longitude)
        current = SearchArea(coordinates=coordinates, radius_m=args.radius_m) if coordinates else None
        if args.radius_m is not None and coordinates is None:
            raise ValueError("Radius needs explicit coordinates.")
        request = DiscoveryRequest(activity=args.activity,
                                   destination=SearchArea(name=args.destination) if args.destination else None,
                                   current_location=current)
        result = PlacesDiscovery(ProviderBudget().outing()).discover(request)
        # Diagnostic counts only: no user coordinates or provider content stored/logged.
        print(json.dumps({"provider": result.provider, "candidate_count": len(result.candidates),
                          "excluded_count": result.excluded_count, "notice": result.notice}))
        return 0
    except (DiscoveryError, ProviderLimitError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (ValidationError, ValueError):
        print("Invalid activity/location. Supply a destination or valid coordinates and a radius greater than 0 and at most 50000 meters.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
