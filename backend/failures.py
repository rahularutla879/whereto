"""Credential-free error categories and correlation evidence; never log inputs."""
import logging
from uuid import uuid4

MESSAGES = {
    'database_not_configured': 'Saving is not configured on the server. Start the backend with its saved-plan database configuration.',
    'database_runtime_role_required': 'Saving requires the restricted saved-plan database login. Check backend/.env.persistence; the administrator login cannot save plans.',
    'database_connection_failed': 'The saved-plan database could not be reached. Check the connection and retry; your itinerary is kept.',
    'database_authentication_failed': 'The saved-plan database login was rejected. Check the existing restricted login configuration; no plan was saved.',
    'database_access_denied': 'Saved-plan database access was denied. Check the restricted role and applied migrations.',
    'save_validation_failed': 'This save request is incomplete or invalid. Generate again before saving.',
    'save_reference_expired': 'This generated save reference expired or changed. Generate again before saving.',
    'save_transaction_failed': 'The database could not complete this save. No partial plan was saved. Retry with the same selection.',
    'saved_link_unavailable': 'This saved link is invalid, expired or unavailable. Check the link; an older remembered link may refer to another plan.',
    'llm_interpretation_failed': 'The local language interpreter could not read this request. Check Ollama and retry; no plan was generated.',
    'no_relevant_venues': 'No activity-relevant venues were found in the checked results. Search more places or refine the area; no substitute activity was added.',
    'insufficient_routing': 'Venues were found, but required routes could not be verified. Retry later or check the starting point; no travel estimate was invented.',
    'provider_quota_rejected': 'Google rejected this search or route request because a quota was reached. Check provider usage and retry later; no automatic retry was made.',
    'venue_refresh_limit': 'Venue refresh is temporarily limited. Your saved plan is kept; try again later. No automatic retry was made.',
    'venue_refresh_disabled': 'Venue refresh is disabled. Start the authorized local development profile; your saved plan is kept.',
    'provider_service_error': 'The venue or routing service could not complete this request. Check its availability and try again later.',
    'internal_application_error': 'An application error prevented this operation. Your current itinerary is kept. Use the reference ID to investigate; changing your activities is not required.',
    'local_request_required': 'This development planner accepts local requests only. Open the app on localhost or 127.0.0.1.',
}


def correlation():
    return uuid4().hex[:16]


def evidence(code, operation, reference=None, exception=None):
    reference = reference or correlation()
    # Exception messages, SQL, provider objects, bodies and tokens are excluded.
    logging.getLogger('whereto.failures').warning('failure reference=%s code=%s operation=%s exception_type=%s',
        reference, code, operation, type(exception).__name__ if exception else 'none')
    return reference


def provider_code(error):
    code = getattr(error, 'code', '')
    if code == 'quota': return 'provider_quota_rejected'
    if code in ('provider','authentication','permission','timeout','invalid_response'): return 'provider_service_error'
    return code or 'provider_service_error'
