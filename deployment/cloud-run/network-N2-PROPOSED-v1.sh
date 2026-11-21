#!/bin/sh
set -eu
# REVIEW ONLY. Separate owner authorization AND fresh cloud preflight required.
# Stop on error; no automatic retry/resume. Do not replay completed commands.
# N2 requires N1 completion; reserved IPv4 starts recurring charges.
export CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API=false
export CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK=true
cd /Users/rahularutla/Documents/whereto
/Users/rahularutla/Documents/whereto/backend/.venv/bin/python -m deployment.network_storage /Users/rahularutla/.whereto-production-frontend-v1/state --check
/opt/homebrew/bin/gcloud compute addresses create whereto-staging-egress --region=us-east4 --project=where-to-512422
/opt/homebrew/bin/gcloud compute routers create whereto-staging --network=whereto-staging --region=us-east4 --project=where-to-512422
/opt/homebrew/bin/gcloud compute routers nats create whereto-staging --router=whereto-staging --region=us-east4 --nat-all-subnet-ip-ranges --nat-external-ip-pool=whereto-staging-egress --project=where-to-512422
