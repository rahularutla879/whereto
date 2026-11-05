"""Credential-free error categories and correlation evidence; never log inputs."""
import logging
from uuid import uuid4

MESSAGES = {
    'service_busy': 'Planning is busy right now. Your request and preferences are kept; please try again shortly.',
    'request_in_progress': 'This request is already being processed. Wait for it to finish before trying again.',
    'request_burst_limited': 'Too many requests arrived at once. Your preferences are kept; please try again shortly.',
    'request_too_large': 'This request is too large. Shorten it and try again.',
    'request_body_timeout': 'The request did not finish arriving. Please try again.',

    'llm_unavailable': "We're having trouble planning your outing right now. Please try again.",
    'llm_timeout': "Planning took longer than expected. Your request is kept; please try again.",
    'llm_invalid_response': "We couldn't finish understanding that request. Please try again or edit the wording.",
    'database_not_configured': 'Saving is temporarily unavailable. Your itinerary is kept.',
    'database_runtime_role_required': 'Saving is temporarily unavailable. Your itinerary is kept.',
    'database_connection_failed': 'We could not reach your saved plans. Please try again; your itinerary is kept.',
    'database_authentication_failed': 'Saving is temporarily unavailable. No plan was saved.',
    'database_access_denied': 'Saving is temporarily unavailable. Your itinerary is kept.',
    'save_validation_failed': 'This save request is incomplete or invalid. Generate again before saving.',
    'save_reference_expired': 'This generated save reference expired or changed. Generate again before saving.',
    'save_transaction_failed': 'The database could not complete this save. No partial plan was saved. Retry with the same selection.',
    'saved_link_unavailable': 'This saved link is invalid, expired or unavailable. Check the link; an older remembered link may refer to another plan.',
    'llm_interpretation_failed': "We couldn't finish understanding that request. Please try again or edit the wording.",
    'no_relevant_venues': 'No activity-relevant venues were found in the checked results. Search more places or refine the area; no substitute activity was added.',
    'insufficient_routing': 'Venues were found, but required routes could not be verified. Retry later or check the starting point; no travel estimate was invented.',
    'provider_quota_rejected': 'Search and routing capacity is temporarily unavailable. Your preferences are kept; please try again later.',
    'provider_local_rate_limit': 'The shared search or routing allowance is temporarily full. Your request and preferences are kept. Wait before selecting Retry; refreshing the page does not reset this limit.',
    'provider_local_admission': 'The shared search or routing allowance is currently full. Your preferences are kept. Please try again later.',
    'venue_refresh_limit': 'Venue refresh is temporarily limited. Your saved plan is kept; try again later. No automatic retry was made.',
    'venue_refresh_disabled': 'Current venue updates are unavailable. Your saved plan is kept.',
    'provider_service_error': 'The venue or routing service could not complete this request. Check its availability and try again later.',
    'internal_application_error': 'We could not complete this step. Your current itinerary is kept. Please try again.',
    'local_request_required': 'This development planner accepts local requests only. Open the app on localhost or 127.0.0.1.',
}


def correlation():
    return uuid4().hex[:16]


def evidence(code, operation, reference=None, exception=None):
    from backend.operations import request_id, event, OPERATIONS
    reference = reference or request_id.get() or correlation()
    event('failure', operation if operation in OPERATIONS else 'http', reason=code)
    code = code if code in MESSAGES else 'other'
    operation = operation if operation in OPERATIONS else 'http'
    # Exception messages, SQL, provider objects, bodies and tokens are excluded.
    logging.getLogger('whereto.failures').warning('failure reference=%s code=%s operation=%s exception_type=%s',
        reference, code, operation, type(exception).__name__ if exception else 'none')
    return reference


def provider_code(error):
    from backend.provider_budget import ProviderLimitError
    if isinstance(error, ProviderLimitError):
        return 'provider_local_rate_limit' if error.reason in ('local_minute','local_shared_minute','concurrent_request') else 'provider_local_admission'
    code = getattr(error, 'code', '')
    if code == 'busy': return 'service_busy'
    if code == 'application_limit': return 'provider_local_admission'
    if code == 'quota': return 'provider_quota_rejected'
    if code in ('provider','authentication','permission','timeout','invalid_response','disabled'): return 'provider_service_error'
    return code or 'provider_service_error'


def provider_status(error):
    code = provider_code(error)
    if code in ('provider_quota_rejected', 'provider_local_rate_limit'): return 429
    if code in ('provider_service_error', 'provider_local_admission', 'service_busy'): return 503
    return 422
