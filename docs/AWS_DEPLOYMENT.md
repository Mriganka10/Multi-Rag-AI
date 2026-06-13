# AWS Deployment Guide

This guide captures the AWS deployment path used for the public CA Agentic AI RAG demo.

The original plan considered AWS App Runner, but App Runner was not available for this account/flow. The working deployment uses AWS Elastic Beanstalk in `ap-south-1`.

For a beginner-friendly explanation of every AWS service used, see [AWS_DEPLOYMENT_WALKTHROUGH.md](AWS_DEPLOYMENT_WALKTHROUGH.md).

## Current Demo Architecture

```text
User Browser
    |
    v
Elastic Beanstalk public URL
    |
    v
EC2 instance managed by Elastic Beanstalk
    |
    v
Docker container running FastAPI on port 8000
    |
    +-- OpenAI API for final response generation
    +-- Amazon S3 private bucket for uploaded files
    +-- Amazon RDS PostgreSQL for audit events
```

## Current AWS Resources

| Resource | Value |
| --- | --- |
| AWS Region | `ap-south-1` |
| Elastic Beanstalk application | `ca-agentic-ai-rag` |
| Elastic Beanstalk environment | `ca-agentic-ai-prod` |
| Public URL | `http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/` |
| Health URL | `http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/health` |
| S3 bucket | `ca-agentic-ai-prod-uploads-453732174568-ap-south-1` |
| RDS DB identifier | `ca-agentic-ai-audit-db` |
| RDS database name | `ca_agentic_ai` |
| RDS user | `app_user` |
| EC2 instance | `i-0c35f5212d41a1752` |
| EC2 instance role | `aws-elasticbeanstalk-ec2-role` |
| S3 policy | `MultiRAGAgentS3AccessPolicyMumbai` |

## What Is Implemented In Code

- Basic Auth gate for the UI and APIs when `AUTH_ENABLED=true`.
- Role check before content can be marked as CA-approved learned RAG.
- Tenant-scoped request metadata using `tenant_id`.
- Upload persistence to S3 when `STORAGE_PROVIDER=s3`.
- Server-side encryption for S3 uploads.
- Audit logging to PostgreSQL when `DATABASE_URL` is configured.
- File-based audit fallback for local development.
- Optional Qdrant Cloud retrieval when `RAG_PROVIDER=qdrant`.
- Local TF-IDF RAG fallback for development and tests.

## Required AWS Resources

### 1. S3 Bucket

Create one private S3 bucket for uploaded documents.

Recommended settings:

- Block all public access: enabled.
- Versioning: enabled for recovery.
- Default encryption: SSE-S3 or SSE-KMS.
- Lifecycle rule: delete temporary files such as `tmp/` after a short retention period.

The deployed demo uses:

```text
ca-agentic-ai-prod-uploads-453732174568-ap-south-1
```

### 2. RDS PostgreSQL

Create an Amazon RDS PostgreSQL database for audit records.

Recommended settings:

- Engine: PostgreSQL.
- Database name: `ca_agentic_ai`.
- Public access: no for production.
- Storage encryption: enabled.
- Backups: enabled.
- Security group allows PostgreSQL traffic only from the Elastic Beanstalk EC2 security group.

The application receives the connection through:

```text
DATABASE_URL=postgresql://app_user:<password>@<rds-endpoint>:5432/ca_agentic_ai
```

### 3. Elastic Beanstalk

Create an Elastic Beanstalk application and environment.

Recommended settings:

- Platform: Docker on Amazon Linux.
- Application: `ca-agentic-ai-rag`.
- Environment: `ca-agentic-ai-prod`.
- Port: `8000`.
- Health check path: `/health`.
- Instance type: small demo instance such as `t3.micro`.
- Instance role: `aws-elasticbeanstalk-ec2-role`.

Elastic Beanstalk creates and manages the EC2 instance. You should normally manage the app from Elastic Beanstalk, not by manually changing the EC2 instance.

### 4. IAM Role And Policies

The EC2 instance role needs permission to call AWS services on behalf of the running app.

Attach these policies to `aws-elasticbeanstalk-ec2-role`:

- Standard Elastic Beanstalk web tier policies.
- `AmazonSSMManagedInstanceCore` so Session Manager can connect to the instance.
- Custom S3 access policy for the upload bucket.

Minimum S3 policy:

```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:GetObject"],
  "Resource": "arn:aws:s3:::ca-agentic-ai-prod-uploads-453732174568-ap-south-1/*"
}
```

### 5. OpenAI API Key

Set the OpenAI API key as an environment property or managed secret. Do not commit `.env` files or API keys to GitHub.

## Environment Variables

Set these in Elastic Beanstalk environment properties.

```text
APP_NAME=CA Agentic AI RAG
ENVIRONMENT=production
DATA_DIR=data

LLM_PROVIDER=openai
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

AUTH_ENABLED=true
AUTH_USERNAME=clientdemo
AUTH_PASSWORD=<secret>
AUTH_DEFAULT_ROLE=admin

DATABASE_URL=<secret>
AUDIT_ENABLED=true

STORAGE_PROVIDER=s3
S3_BUCKET=ca-agentic-ai-prod-uploads-453732174568-ap-south-1
S3_PREFIX=ca-agentic-ai
AWS_REGION=ap-south-1

RAG_PROVIDER=local
RAG_LEARNING_ENABLED=true
RAG_LEARNING_DEFAULT_CONSENT=false
```

For the first public demo, `RAG_PROVIDER=local` is acceptable. Move to Qdrant after the basic deployment is stable.

## Deployment Steps

1. Prepare the deployment branch.
2. Create the private S3 upload bucket.
3. Create the RDS PostgreSQL database.
4. Create or update IAM role permissions.
5. Create the Elastic Beanstalk application and environment.
6. Configure Elastic Beanstalk environment variables.
7. Deploy the Docker application bundle.
8. Open the health URL.
9. Open the public client URL and log in.
10. Upload a document and run analysis.
11. Confirm uploaded files appear in S3.
12. Confirm audit records appear in PostgreSQL.

## Fixes Applied During Deployment

### App Runner Unavailable

App Runner was not available in the first selected region/account flow, so the deployment moved to Elastic Beanstalk.

### PostgreSQL Version Error

The requested RDS PostgreSQL version `16.3` was not available in the selected region. The deployment used an available PostgreSQL engine version instead.

### Docker Build Missing `.gitkeep` Files

The Dockerfile tried to copy empty placeholder files that were not present in the deployment bundle:

```text
data/uploads/.gitkeep
data/outputs/.gitkeep
data/audit/.gitkeep
```

The fix was to create those directories during image build instead:

```dockerfile
RUN mkdir -p ./data/uploads ./data/outputs ./data/audit
```

### Large Upload Error

Uploading two PDFs caused:

```text
413 Request Entity Too Large
nginx/1.30.2
```

The fix was to add an Elastic Beanstalk nginx config:

```text
.platform/nginx/conf.d/client_max_body_size.conf
```

with:

```nginx
client_max_body_size 25M;
```

## Verifying The Deployment

Health check:

```bash
curl http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/health
```

Expected response:

```json
{"status":"ok","environment":"production"}
```

Audit query:

```sql
select timestamp, event_type, tenant_id, actor, status, metadata
from audit_events
order by id desc
limit 20;
```

S3 upload prefix:

```text
s3://ca-agentic-ai-prod-uploads-453732174568-ap-south-1/ca-agentic-ai/tenants/<tenant-id>/uploads/
```

## Querying PostgreSQL

AWS RDS Query Editor does not support this normal RDS PostgreSQL instance. It mainly supports Aurora Serverless/Data API style databases.

Use EC2 Session Manager to connect to the Elastic Beanstalk EC2 instance, then run `psql` from there. This works because the EC2 instance is inside the same AWS network path as RDS.

If Session Manager is offline:

1. Confirm `AmazonSSMManagedInstanceCore` is attached to `aws-elasticbeanstalk-ec2-role`.
2. Reboot the EC2 instance.
3. Wait until SSM shows `Ping status: Online`.
4. Connect using Session Manager.

## Demo Security Checklist

- `AUTH_ENABLED=true`.
- Strong `AUTH_PASSWORD`.
- S3 bucket is private.
- S3 encryption is enabled.
- RDS encryption is enabled.
- RDS is not publicly open.
- RDS security group allows inbound PostgreSQL only from the app security group.
- Do not upload real client documents unless the client has approved the demo environment.

## Production Follow-Ups

After the demo:

- Replace Basic Auth with Cognito or enterprise SSO.
- Add real user, role, and session tables in PostgreSQL.
- Add explicit login success and login failure audit events.
- Add full document metadata tables.
- Add a reviewer workflow UI for learned RAG approval.
- Add background workers for large document processing.
- Add Qdrant ingestion jobs for law, circulars, notifications, and case law.
- Add HTTPS custom domain, AWS Certificate Manager, WAF, CloudWatch alarms, and structured logs.
