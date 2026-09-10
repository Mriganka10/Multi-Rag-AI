# Security and Compliance Notes

## Principle

This platform assists Chartered Accountants. It must not replace professional judgment, file returns autonomously, submit replies autonomously, or finalize legal positions without approval.

## Human-in-the-Loop Requirements

Human review is mandatory for:

- SCN replies
- Assessment responses
- ITR filing
- GST return filing
- Tax position memos
- Case-law interpretation
- High-value anomaly conclusions
- Any communication to a government authority

The internal task result includes `requires_human_review` for this reason. The public analysis API returns human-readable text, so the response wording must continue to include CA review caveats.

## Sensitive Data

The system may process:

- PAN, Aadhaar, GSTIN, CIN, TAN
- Bank account numbers
- Salary and income details
- Tax payments and TDS
- Invoices and ledgers
- Client financial statements
- Government notices

Production systems must treat all uploaded data as confidential.

## Recommended Production Controls

### Authentication and Authorization

- Enable email OTP sign-in for the AWS demo using `AUTH_ENABLED=true`.
- Configure email credentials through AWS-managed secrets exposed only to the ECS task role.
- Set `AUTH_COOKIE_SECURE=true` in public HTTPS deployments.
- For a broader production rollout, prefer SES-backed OTP, Cognito, or enterprise SSO with managed user lifecycle controls.
- Use role checks for sensitive workflows such as CA-approved RAG learning.
- Restrict client data by firm, team, and engagement.
- Separate admin, CA reviewer, preparer, and read-only roles.

### Data Protection

- Encrypt data at rest.
- Use TLS in transit.
- Store secrets in a managed secret vault.
- Never commit `.env` files or API keys to Git.
- Store uploaded documents in a private S3 bucket when `STORAGE_PROVIDER=s3`.
- Use S3 default encryption or KMS encryption through `S3_KMS_KEY_ID`.
- Avoid logging document contents or personally identifiable data.
- Apply retention rules for uploaded documents and generated outputs.

### Audit Trail

Track:

- Who uploaded documents.
- Who logged in successfully or failed login.
- Which agent processed the task.
- Which sources were retrieved.
- What draft was generated.
- Who reviewed or approved the final output.
- When an output was exported or submitted.

The current implementation writes audit events to PostgreSQL when `DATABASE_URL` is configured. Without a database, it writes local JSONL audit records under `data/audit`.

In the AWS demo, audit records are stored in Amazon RDS PostgreSQL:

```text
DB identifier: ca-agentic-ai-audit-db
Database name: ca_agentic_ai
Region: ap-south-1
```

Inspect the private RDS database only from an approved administrative ECS task or bastion in the
VPC. Use the application database role, audit the session, and do not print decrypted connection
strings into logs.

Useful query:

```sql
select timestamp, event_type, tenant_id, actor, status, metadata
from audit_events
order by id desc
limit 20;
```

Current audit scope is enough to prove that application events are reaching PostgreSQL. A production release should add explicit `login_success`, `login_failed`, `document_uploaded`, `analysis_started`, `analysis_completed`, and `analysis_failed` events so owner activity tracking is complete.

### Prompt and RAG Safety

- Do not let uploaded documents override system policy.
- Keep retrieved source citations visible.
- Separate client-provided text from legal knowledge.
- Treat generated drafts as drafts, not verified truth.
- Add explicit uncertainty where data is incomplete.
- Keep learned RAG content opt-in per tenant or engagement.
- Load only CA-approved learned content into retrieval.
- CA-approved learned content requires an authenticated `admin` or `reviewer` role when authentication is enabled.
- Qdrant Cloud retrieval can be enabled with `RAG_PROVIDER=qdrant`; local TF-IDF remains the fallback for development.

### Government Portal Integrations

Portal integrations should be added only after:

- Strong authentication is implemented.
- CA approval workflow is implemented.
- Submission preview is available.
- Immutable audit log is available.
- Rollback and error handling are designed.

## Legal Disclaimer

The POC is for software demonstration and internal review. It is not legal, tax, audit, or accounting advice. All outputs must be reviewed by a qualified professional before use.
