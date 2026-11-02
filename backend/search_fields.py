"""Explicit local field gates and one consistent Enterprise accounting decision."""
import os
from backend.provider_budget import local_real_enabled
HOURS_FIELDS='places.currentOpeningHours,places.regularOpeningHours,places.timeZone'
RATING_FIELDS='places.rating,places.userRatingCount'
def hours_enabled():return local_real_enabled() and os.environ.get('WHERETO_HOURS_DEV')=='1'
def ratings_enabled():return local_real_enabled() and os.environ.get('WHERETO_RATINGS_DEV')=='1'
def enterprise_search():return hours_enabled() or ratings_enabled()
def search_mask(base):
 return base+(','+RATING_FIELDS if ratings_enabled() else '')+(','+HOURS_FIELDS if hours_enabled() else '')
