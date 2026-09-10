# AWS Deployment Walkthrough

Last updated: 10 September 2026.

```text
ledgermind.co.in -> CloudFront -> shared ALB -> isolated Multi-RAG ECS web
                                                   |
                                    dedicated database/role + private S3
```

CloudFront preserves the purchased domain and certificate. Its private origin header selects the correct ALB target group. ECS runs the existing container as an independent service on shared ARM capacity, removing the cost of a dedicated always-on Elastic Beanstalk host. The application does not currently need a queue worker.

The shared physical RDS instance contains a separate logical database and role for this application. There is no cross-application schema access. Large documents and artifacts remain in private S3 rather than inflating PostgreSQL storage.

No business feature code or API contract changed in the September migration. Release acceptance covers health, authentication, text/file analysis, OCR, SCN, bank statement, financial analysis, RAG, model output, and artifacts. Roll back the ECS task definition if checks fail. The paused Elastic Beanstalk environment is temporary rollback history only.
