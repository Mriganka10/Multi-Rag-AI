# AWS Production Deployment

Last updated: 10 September 2026.

`ledgermind.co.in` remains the live public URL. CloudFront terminates HTTPS and sends a private routing header to the shared Application Load Balancer, which forwards to Multi-RAG's isolated ECS web service and target group.

The application shares the ALB, ARM ECS capacity, and physical RDS instance to reduce fixed idle cost. It retains its own ECS service/task role, secrets, logical PostgreSQL database and role, and private S3 namespace. It has no always-on worker because its current request flow is interactive.

Production configuration includes `ENVIRONMENT=production`, the application-specific `DATABASE_URL`, private S3 configuration, secure auth/session settings, email delivery, and model credentials. Values belong in AWS secrets/configuration stores, never Git.

The task role requires `ses:GetEmailIdentity`, `ses:CreateEmailIdentity`,
`ses:DeleteEmailIdentity`, `ses:SendEmail`, and `ses:SendRawEmail`. Delete is required because this
application replaces pending/failed SES identities when a user requests a fresh link.

Build an immutable ARM-compatible image, register a new task-definition revision, apply only compatible schema changes, update the ECS service, and wait for healthy targets. Verify `/health`, registration/login, text analysis, file upload, all supported domain workflows, RAG context, and downloads at the unchanged domain. Monitor ALB 5xx, ECS restarts, RDS, S3, authentication, and model failures.

Rollback uses the preceding task definition. The former Elastic Beanstalk environment is paused for the agreed 7–14 day rollback observation window and is not active production.

The former Multi-RAG RDS instance still exists during that window and continues to incur charges.
Snapshot and retire it only after final data/restore validation and explicit owner approval.

See [deployment walkthrough](AWS_DEPLOYMENT_WALKTHROUGH.md) and [code walkthrough](CODE_WALKTHROUGH.md).
