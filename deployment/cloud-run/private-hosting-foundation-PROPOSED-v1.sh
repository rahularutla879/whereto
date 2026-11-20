#!/bin/sh
set -eu
# REVIEW ONLY: owner must separately authorize this exact batch before execution.
# No services, networking, secret versions, testers or provider grants. Stop on error; do not rerun blindly.
cd /Users/rahularutla/Documents/whereto
/Users/rahularutla/Documents/whereto/backend/.venv/bin/python -m deployment.hosting_batch /Users/rahularutla/.whereto-production-frontend-v1/state --check
gcloud services enable run.googleapis.com iap.googleapis.com secretmanager.googleapis.com --project=where-to-512422
gcloud beta services identity create --service=run.googleapis.com --project=where-to-512422
gcloud beta services identity create --service=iap.googleapis.com --project=where-to-512422
gcloud iam service-accounts create whereto-frontend '--display-name=WhereTo frontend' --project=where-to-512422
gcloud iam service-accounts create whereto-backend '--display-name=WhereTo backend' --project=where-to-512422
gcloud iam service-accounts create whereto-factory '--display-name=WhereTo factory' --project=where-to-512422
gcloud iam service-accounts create whereto-counter '--display-name=WhereTo counter' --project=where-to-512422
gcloud iam service-accounts create whereto-dispatcher '--display-name=WhereTo dispatcher' --project=where-to-512422
gcloud iam service-accounts create whereto-recovery '--display-name=WhereTo recovery' --project=where-to-512422
gcloud artifacts repositories add-iam-policy-binding whereto-private --location=us-east4 --member=serviceAccount:service-895186533714@serverless-robot-prod.iam.gserviceaccount.com --role=roles/artifactregistry.reader --project=where-to-512422
gcloud secrets create whereto-frontend-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets create whereto-backend-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets create whereto-factory-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets create whereto-counter-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets create whereto-dispatcher-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets create whereto-recovery-runtime --replication-policy=user-managed --locations=us-east4 --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-frontend-runtime --member=serviceAccount:whereto-frontend@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-backend-runtime --member=serviceAccount:whereto-backend@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-factory-runtime --member=serviceAccount:whereto-factory@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-counter-runtime --member=serviceAccount:whereto-counter@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-dispatcher-runtime --member=serviceAccount:whereto-dispatcher@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
gcloud secrets add-iam-policy-binding whereto-recovery-runtime --member=serviceAccount:whereto-recovery@where-to-512422.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --project=where-to-512422
