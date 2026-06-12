# AWS Production Deployment Guide

This guide describes the recommended AWS path for the CA Agentic AI RAG application.

For the 20 June client demo, use AWS App Runner with the Dockerfile in this repository. For a larger production rollout, move the same container to ECS Fargate behind an Application Load Balancer.

## Target AWS Architecture

```text
User Browser
    |
    v
AWS App Runner HTTPS URL
    |
    v
FastAPI App Container
    |
    +-- OpenAI API
    +-- Qdrant Cloud
    +-- Amazon S3 encrypted uploads
    +-- Amazon RDS PostgreSQL audit log
    +-- AWS Secrets Manager / App Runner secrets
```

## What Is Implemented In Code

- Basic Auth gate for the UI and APIs when `AUTH_ENABLED=true`.
- Role check before content can be marked as CA-approved learned RAG.
- Tenant-scoped request metadata using `tenant_id`.
- Upload persistence to S3 when `STORAGE_PROVIDER=s3`.
- Server-side encryption for S3 uploads, including optional KMS key support.
- Audit logging to PostgreSQL when `DATABASE_URL` is configured.
- File-based audit fallback for local development.
- Optional Qdrant Cloud retrieval when `RAG_PROVIDER=qdrant`.
- Local TF-IDF RAG fallback for development and tests.

## AWS Resources To Create

### 1. S3 Bucket

Create one private S3 bucket for uploaded documents.

Recommended settings:

- Block all public access: enabled.
- Versioning: enabled.
- Default encryption: SSE-S3 or SSE-KMS.
- Bucket name example: `ca-agentic-ai-prod-uploads`.

If using KMS, create a customer-managed KMS key and note the key ARN.

### 2. RDS PostgreSQL

Create an Amazon RDS PostgreSQL database.

Recommended demo settings:

- Engine: PostgreSQL.
- Public access: no, unless you need temporary local testing.
- Storage encryption: enabled.
- Backups: enabled.
- Database name: `ca_agentic_ai`.

Create a database user for the app and build a `DATABASE_URL`:

```text
postgresql://app_user:password@your-rds-endpoint.ap-south-1.rds.amazonaws.com:5432/ca_agentic_ai
```

### 3. Qdrant Cloud

Create a Qdrant Cloud cluster and note:

- Qdrant URL
- Qdrant API key

The app expects collections with this naming convention:

```text
ca_income_tax
ca_gst
ca_accounting_standards
ca_case_laws
ca_notifications
```

You can change the prefix using:

```text
QDRANT_COLLECTION_PREFIX=ca
```

### 4. OpenAI API Key

Store the OpenAI API key only as an AWS secret or App Runner secret-backed environment variable.

Do not commit `.env` or API keys to GitHub.

### 5. App Runner Service

In AWS App Runner:

1. Create service.
2. Source: GitHub repository.
3. Repository: `Mriganka10/Multi-Rag-AI`.
4. Branch: your production branch, for example `feature/prototype_development_v1`.
5. Deployment source: Dockerfile.
6. Port: `8000`.
7. Health check path: `/health`.

The Dockerfile starts the app with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Environment Variables

Set these in App Runner. Use secret-backed variables for passwords and API keys.

```text
APP_NAME=CA Agentic AI RAG
ENVIRONMENT=production
DATA_DIR=data

LLM_PROVIDER=openai
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

AUTH_ENABLED=true
AUTH_USERNAME=<secret-or-config>
AUTH_PASSWORD=<secret>
AUTH_DEFAULT_ROLE=admin

DATABASE_URL=<secret>
AUDIT_ENABLED=true

STORAGE_PROVIDER=s3
S3_BUCKET=ca-agentic-ai-prod-uploads
S3_PREFIX=ca-agentic-ai
S3_KMS_KEY_ID=<optional-kms-key-arn>
AWS_REGION=ap-south-1

RAG_PROVIDER=qdrant
QDRANT_URL=<secret>
QDRANT_API_KEY=<secret>
QDRANT_COLLECTION_PREFIX=ca

RAG_LEARNING_ENABLED=true
RAG_LEARNING_DEFAULT_CONSENT=false
```

## IAM Permissions

The App Runner service role needs access to:

- S3 upload bucket.
- Optional KMS key.
- Secrets used by App Runner.

Minimum S3 permissions:

```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:GetObject"],
  "Resource": "arn:aws:s3:::ca-agentic-ai-prod-uploads/*"
}
```

If using KMS:

```json
{
  "Effect": "Allow",
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
  "Resource": "<your-kms-key-arn>"
}
```

## Deployment Steps

1. Merge the latest UI and production-foundation PR into the deployment branch.
2. Create S3 bucket.
3. Create RDS PostgreSQL database.
4. Create or configure Qdrant Cloud cluster.
5. Store secrets in AWS Secrets Manager or App Runner secret variables.
6. Create App Runner service from GitHub.
7. Configure env vars.
8. Deploy.
9. Open the App Runner URL.
10. Log in using Basic Auth.
11. Test:
    - SCN prompt.
    - Bank statement file upload.
    - ITR file upload.
    - Financial statement prompt.
12. Check RDS audit table:

```sql
select timestamp, event_type, tenant_id, actor, status, metadata
from audit_events
order by id desc
limit 20;
```

13. Check S3 upload prefix:

```text
s3://ca-agentic-ai-prod-uploads/ca-agentic-ai/tenants/<tenant-id>/uploads/
```

## Demo Security Checklist

- `AUTH_ENABLED=true`.
- Strong password set in `AUTH_PASSWORD`.
- `RAG_LEARNING_DEFAULT_CONSENT=false`.
- Only a reviewer/admin can use CA-approved learning.
- S3 bucket is private.
- S3 encryption is enabled.
- RDS encryption is enabled.
- Do not upload real client documents unless the client has approved the demo environment.

## Production Follow-Ups

After the demo:

- Replace Basic Auth with Cognito or enterprise SSO.
- Add real user and role tables in PostgreSQL.
- Add a reviewer workflow UI for learned RAG approval.
- Add full document metadata tables.
- Add background workers for large document processing.
- Add Qdrant ingestion jobs for law, circulars, notifications, and case law.
- Add WAF, custom domain, monitoring, and structured logs.
