# AWS Deployment Walkthrough and Concepts

This document explains the AWS deployment that was created for the CA Agentic AI RAG application, the AWS services involved, and the practical troubleshooting steps used to make the public URL work.

It is written for first-time AWS users who want to understand what each service does and why it was used.

## Final Demo Deployment

The deployed demo uses this shape:

```text
User browser
    |
    v
Elastic Beanstalk public URL
    |
    v
EC2 instance managed by Elastic Beanstalk
    |
    v
Docker container running FastAPI
    |
    +-- OpenAI API
    +-- Private S3 bucket for uploaded files
    +-- Private RDS PostgreSQL database for audit events
```

Main deployed resources:

```text
AWS Region: ap-south-1, Asia Pacific (Mumbai)
Elastic Beanstalk environment: ca-agentic-ai-prod
Elastic Beanstalk application: ca-agentic-ai-rag
Public URL: http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/
S3 bucket: ca-agentic-ai-prod-uploads-453732174568-ap-south-1
RDS DB identifier: ca-agentic-ai-audit-db
RDS database name: ca_agentic_ai
RDS user: app_user
EC2 instance name: ca-agentic-ai-prod
EC2 instance role: aws-elasticbeanstalk-ec2-role
```

Secrets are not documented here. Do not commit passwords, OpenAI API keys, or database connection strings to Git.

## Why Elastic Beanstalk Was Used

The first planned deployment option was AWS App Runner, because the repository already has a `Dockerfile` and `apprunner.yaml`.

During deployment, AWS showed that App Runner was not available for this account as a new App Runner customer. Therefore the public deployment was moved to Elastic Beanstalk.

Elastic Beanstalk is still a managed deployment service. It creates and manages EC2, networking, health checks, deployment versions, nginx proxying, and application lifecycle around the Docker app.

## EC2 vs Elastic Beanstalk

### EC2

EC2 means Elastic Compute Cloud. It is a virtual server.

If using raw EC2 directly, you normally manage:

- Server creation.
- Operating system updates.
- Docker installation.
- Application deployment.
- Restart behavior.
- Logs.
- Security groups.
- Health checks.
- Manual troubleshooting.

In this deployment, an EC2 instance exists, but it was created by Elastic Beanstalk.

### Elastic Beanstalk

Elastic Beanstalk is a deployment manager on top of EC2.

It does not replace EC2. It uses EC2 underneath and manages much of the deployment work for you.

Elastic Beanstalk handled:

- Creating the EC2 instance.
- Deploying the Docker source bundle.
- Building the Docker image.
- Running the FastAPI container.
- Placing nginx in front of the app.
- Exposing the public environment URL.
- Creating environment versions.
- Restarting app servers.
- Reporting environment health.

### Simple Difference

```text
EC2 = the server.
Elastic Beanstalk = the service that creates, configures, deploys to, and monitors the server.
```

For a first demo, Elastic Beanstalk is easier than raw EC2 because it gives a public application URL and deployment workflow with less server administration.

## IAM, Roles, and Policies

IAM means Identity and Access Management. It controls who or what can access AWS resources.

### IAM Policy

A policy is a permission document. It says what actions are allowed on which resources.

Example:

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::example-bucket/*"
}
```

This means the holder can read and write objects in that bucket.

### IAM Role

A role is an identity that an AWS service can assume.

The application does not use your personal AWS login to access S3. Instead, the EC2 instance receives an IAM role. The application running on that instance gets temporary AWS credentials from the role.

For this deployment:

```text
Role: aws-elasticbeanstalk-ec2-role
Used by: EC2 instance created by Elastic Beanstalk
Purpose: allow the running application to access AWS services such as S3 and SSM
```

### Policies Attached to the EC2 Role

The role needs policies such as:

```text
AWSElasticBeanstalkWebTier
AWSElasticBeanstalkMulticontainerDocker
MultiRAGAgentS3AccessPolicyMumbai
AmazonSSMManagedInstanceCore
```

What these mean:

- `AWSElasticBeanstalkWebTier`: standard Elastic Beanstalk web environment permissions.
- `AWSElasticBeanstalkMulticontainerDocker`: Docker-related Elastic Beanstalk permissions.
- `MultiRAGAgentS3AccessPolicyMumbai`: custom policy allowing the app to read/write the private S3 upload bucket.
- `AmazonSSMManagedInstanceCore`: allows AWS Systems Manager Session Manager to connect to the EC2 instance without SSH keys.

## S3 Bucket

S3 is object storage. It stores uploaded client documents and generated artifacts.

The deployed bucket is:

```text
ca-agentic-ai-prod-uploads-453732174568-ap-south-1
```

Important settings:

- Block public access: enabled.
- Versioning: enabled.
- Default encryption: enabled.
- Lifecycle rule for temporary files: delete `tmp/` objects after 7 days.

The app writes uploaded files under a configured prefix:

```text
ca-agentic-ai/
```

S3 should remain private. Users should access the app URL, not the bucket directly.

## RDS PostgreSQL

RDS is AWS-managed relational database hosting.

For this deployment:

```text
DB identifier: ca-agentic-ai-audit-db
Engine: PostgreSQL
DB name: ca_agentic_ai
User: app_user
Public access: disabled
```

The database is private. It is not intended to be queried directly from the public internet.

The application writes audit events to:

```sql
audit_events
```

Useful query:

```sql
select timestamp, event_type, tenant_id, actor, status, metadata
from audit_events
order by id desc
limit 20;
```

## Why RDS Query Editor Did Not Work

AWS RDS Query Editor does not support every RDS PostgreSQL instance.

The Query Editor commonly supports Aurora Serverless databases with the Data API enabled. This deployment uses a normal RDS PostgreSQL instance, so the console can show a message like:

```text
No databases that support query editor
```

That does not mean the DB is missing. It means the console query editor is not the right query tool for this DB type.

Use `psql` from a machine that can reach the private RDS endpoint.

## How to Query Audit Records

Because the database is private, the easiest AWS path is to connect from the Elastic Beanstalk EC2 instance.

### Step 1: Open the EC2 Instance

Go to:

```text
EC2 -> Instances -> ca-agentic-ai-prod
```

Select the instance and click:

```text
Connect
```

### Step 2: Use SSM Session Manager

Choose:

```text
SSM Session Manager
```

This works only if:

- The instance role has `AmazonSSMManagedInstanceCore`.
- The SSM agent is online.
- The instance has outbound connectivity to Systems Manager.

If it shows offline, attach `AmazonSSMManagedInstanceCore` to `aws-elasticbeanstalk-ec2-role`, reboot the EC2 instance, and wait a few minutes.

### Step 3: Install PostgreSQL Client

Inside the Session Manager terminal:

```bash
sudo dnf install -y postgresql15
```

### Step 4: Connect to PostgreSQL

Use the password created during deployment:

```bash
psql "postgresql://app_user:YOUR_DB_PASSWORD@ca-agentic-ai-audit-db.c7yu6kk6ytyl.ap-south-1.rds.amazonaws.com:5432/ca_agentic_ai"
```

Then query:

```sql
select timestamp, event_type, tenant_id, actor, status, metadata
from audit_events
order by id desc
limit 20;
```

## Security Groups

A security group is a network firewall for AWS resources.

This deployment used:

```text
App security group: ca-agentic-ai-eb-sg
RDS security group: ca-agentic-ai-rds-sg
```

The app security group allows public HTTP traffic to the web application.

The RDS security group allows PostgreSQL port `5432` only from the app security group. This means the database is not publicly open.

Conceptually:

```text
Internet -> Elastic Beanstalk/EC2 on HTTP
EC2 app security group -> RDS security group on port 5432
Internet -> RDS is blocked
```

## Deployment Steps Actually Performed

The deployed environment was created in this order.

### 1. Region Selection

The deployment was done in:

```text
ap-south-1, Asia Pacific (Mumbai)
```

This matters because AWS resources are regional. Looking in `us-east-1` or `eu-north-1` will not show the Mumbai resources.

### 2. S3 Bucket

Created a private encrypted S3 bucket:

```text
ca-agentic-ai-prod-uploads-453732174568-ap-south-1
```

Configured:

- Public access blocked.
- Encryption enabled.
- Versioning enabled.
- Lifecycle cleanup for temporary files.

### 3. IAM Policies and Roles

Created or verified:

```text
MultiRAGAgentS3AccessPolicyMumbai
aws-elasticbeanstalk-service-role
aws-elasticbeanstalk-ec2-role
```

Attached S3 access to the EC2 role so the application can upload/read documents.

Later attached:

```text
AmazonSSMManagedInstanceCore
```

so Session Manager could connect to the EC2 instance.

### 4. Security Groups

Created app and DB security groups:

```text
ca-agentic-ai-eb-sg
ca-agentic-ai-rds-sg
```

Allowed:

- Public HTTP to the app.
- PostgreSQL access from the app security group to the DB security group.

### 5. RDS PostgreSQL

Created private encrypted PostgreSQL:

```text
ca-agentic-ai-audit-db
```

The database endpoint is used in `DATABASE_URL`.

### 6. Elastic Beanstalk Application

Created:

```text
Application: ca-agentic-ai-rag
Environment: ca-agentic-ai-prod
Platform: 64bit Amazon Linux 2023 running Docker
```

Uploaded a zipped source bundle from the GitHub branch:

```text
feature/prototype_development_v1
```

Elastic Beanstalk built and ran the repository `Dockerfile`.

### 7. Environment Variables

Configured app runtime variables such as:

```text
APP_NAME=CA Agentic AI RAG
ENVIRONMENT=production
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
AUTH_ENABLED=true
AUTH_SESSION_COOKIE_NAME=ca_agent_session
AUTH_DEFAULT_ROLE=admin
DATABASE_URL=<PostgreSQL connection string>
AUDIT_ENABLED=true
STORAGE_PROVIDER=s3
S3_BUCKET=ca-agentic-ai-prod-uploads-453732174568-ap-south-1
S3_PREFIX=ca-agentic-ai
AWS_REGION=ap-south-1
RAG_PROVIDER=local
RAG_LEARNING_ENABLED=true
RAG_LEARNING_DEFAULT_CONSENT=false
```

Secret values such as `OPENAI_API_KEY`, SMTP credentials, and the database password were entered during deployment and should remain secret.

## Issues Found and Fixed

### App Runner Not Available

AWS App Runner showed an account availability notice and did not provide a create service button. The deployment was moved to Elastic Beanstalk.

### RDS PostgreSQL Version

The first RDS command pinned PostgreSQL version `16.3`, which was not available in the selected region at that time. The version pin was removed so AWS could choose a supported PostgreSQL version.

### Docker Build Failed Because `.gitkeep` Files Were Missing

The Dockerfile originally referenced:

```text
data/uploads/.gitkeep
data/outputs/.gitkeep
data/audit/.gitkeep
```

Those files were not present in the source bundle, causing Docker build failure.

The deployed Dockerfile was patched to create the folders instead:

```dockerfile
RUN mkdir -p ./data/uploads ./data/outputs ./data/audit
```

### Uploads Failed With `413 Request Entity Too Large`

PDF uploads initially failed with:

```text
413 Request Entity Too Large
nginx/1.30.2
```

The FastAPI app was not receiving the request. Elastic Beanstalk's nginx proxy rejected the request first.

The deployed source bundle was patched with:

```text
.platform/nginx/conf.d/client_max_body_size.conf
```

containing:

```nginx
client_max_body_size 25M;
```

After redeployment, the environment reached:

```text
Status: Ready
Health: Green
/health: HTTP 200 OK
```

## Rebooting and Restarting

There are two different operations.

### Restart App Server

Elastic Beanstalk:

```text
Elastic Beanstalk -> Environment -> Actions -> Restart app server(s)
```

This restarts the application process/container behavior managed by Elastic Beanstalk.

Use this when:

- The application is stuck.
- Environment variables changed.
- You want EB to restart the app without rebooting the whole virtual machine.

### Reboot EC2 Instance

EC2:

```text
EC2 -> Instances -> select instance -> Instance state -> Reboot instance
```

This reboots the virtual server.

Use this when:

- The SSM agent needs to pick up new IAM permissions.
- The OS-level agent or service appears stuck.
- The instance is healthy but AWS management connectivity is not refreshed.

After reboot, wait until:

```text
Instance state: Running
Status checks: 3/3 passed
```

## How Email OTP Sign-In Behaves

The app uses email OTP sign-in for the public demo.

When a user enters an email address, the backend creates an OTP challenge and sends the code through the configured SMTP provider. After verification, the browser receives an HttpOnly session cookie. The signed-in email becomes the tenant boundary for uploads, learned RAG content, and audit events.

To test a fresh sign-in:

- Use Incognito mode.
- Use a different browser.
- Click sign out from the application header.
- Clear site cookies.

For broader production use, connect OTP delivery to Amazon SES, Cognito, or enterprise SSO.

## What Is Audited Today

The current implementation writes audit events to PostgreSQL when:

```text
DATABASE_URL is configured
AUDIT_ENABLED=true
```

The table is:

```text
audit_events
```

The current POC primarily records application audit events around task processing and learning flows. It should be extended to record explicit user activity events such as:

- `login_success`
- `login_failed`
- `document_uploaded`
- `analysis_started`
- `analysis_completed`
- `analysis_failed`

## What Still Needs Improvement

Before a production client rollout:

- Move email OTP to SES, Cognito, or enterprise SSO.
- Store secrets in AWS Secrets Manager or SSM Parameter Store.
- Add explicit activity logging for login, upload, and analysis lifecycle events.
- Add HTTPS custom domain using ACM and CloudFront or an Application Load Balancer.
- Move from local TF-IDF RAG to Qdrant/OpenAI embeddings.
- Add background workers for large files.
- Add document metadata tables in PostgreSQL.
- Add structured CloudWatch logging and alerts.
- Add a repeatable Infrastructure as Code deployment using Terraform, CDK, or CloudFormation.
