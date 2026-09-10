# Code Walkthrough

Last updated: 10 September 2026. This walkthrough describes the code currently deployed at `https://ledgermind.co.in`.

## Runtime entry points and request flow

1. `app/main.py` creates the FastAPI application, mounts the browser UI, and initializes runtime services.
2. `app/api/routes.py` authenticates users, accepts text or file analysis requests, validates uploads, and returns reports and artifacts.
3. `app/agents/orchestrator.py` selects OCR, bank statement, SCN, financial analysis, or ITR preparation behavior while retaining mandatory human review boundaries.
4. Domain agents under `app/agents/` produce deterministic structured analysis.
5. `app/rag/multi_rag.py` retrieves domain and tenant context; `app/rag/learning.py` manages approved learning material.
6. `app/llm/service.py` turns the structured analysis and retrieved context into the configured model response.
7. `app/artifacts/service.py` creates downloadable outputs; `app/core/storage.py` uses private S3 in production.
8. `app/core/auth.py`, `app/core/audit.py`, and `app/core/config.py` provide access control, traceability, and environment configuration.

## September 2026 deployment change

No application feature code or public contract changed in this migration. The container now runs as an independent ECS web service behind the shared Application Load Balancer and CloudFront while keeping `https://ledgermind.co.in`. It uses its own ECS service, target group, task role, secrets, S3 prefix, and logical PostgreSQL database. It does not currently require an always-on worker.

The repository's business functions, human-review policy, APIs, and RAG behavior are unchanged. The change is an infrastructure consolidation that removes the cost of a dedicated always-on Elastic Beanstalk/EC2/RDS stack while preserving application isolation.

## Verification

Run `ruff check .` and `pytest`. The release passed 27 tests, followed by production health and end-to-end smoke checks.
