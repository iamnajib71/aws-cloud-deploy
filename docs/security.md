# Security and documented exceptions

## Identity and trust

Local-session mode sets `enable_github_oidc=false`, provisions no GitHub identity provider or delivery roles, and uses temporary owner-session credentials for Terraform. GitHub cloud jobs remain disabled. This is an explicit alternative for managed projects that prohibit identity providers; it is not evidence of OIDC deployment. For OIDC mode, set the exact GitHub `github_oidc_subject_prefix`, including immutable IDs where required.

No access keys belong in repository secrets. The owner bootstrap creates one OIDC provider and separate plan, dev and prod roles. Trust requires `aud = sts.amazonaws.com` and an exact `sub`:

```text
repo:OWNER/REPOSITORY:pull_request
repo:OWNER/REPOSITORY:environment:dev
repo:OWNER/REPOSITORY:environment:prod
```

The JSON policy is generated in `infra/bootstrap/main.tf`; the owner supplies the repository. Environment subjects do not themselves restrict branches. Both environments must restrict deployment to `main`; prod additionally requires owner approval. Self-review is allowed for this solo lab; require an independent reviewer for a team production system. See [GitHub's AWS OIDC guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

The plan role reads dev state and cloud configuration, with only lock writes. State reads are sensitive access. Same-repository PR authors must be trusted; arbitrary PR Terraform can read data available to the role. Fork PRs have no AWS credentials. The plan role has no deployment or image push permission.

Deployment roles can manage the named environment's Lambda, DynamoDB, log groups, alarms, dashboard and SNS resources. `iam:PassRole` is restricted to the exact runtime role and Lambda service. Delivery roles cannot change IAM, trust, budgets, state bucket controls or ECR repository policy. Only dev can push images. Runtime roles can read/write/scan their own table and write their own log streams; they cannot create infrastructure.

Read policies scope Lambda, DynamoDB, log tags, dashboards and topics to their environment. Log/alarm discovery and SNS subscription-attribute reads require wildcard discovery access. API Gateway management uses region-scoped `/apis/*` and `/tags/*` because IDs are AWS-assigned, so its write scope extends to other HTTP APIs in that region. SNS unsubscribe has no resource-level IAM support and is region-restricted; ECR authentication tokens also require a wildcard, while image operations are repository-scoped. These are explicit least-privilege limitations: use a dedicated demo account. Tighten API IDs after first provision for an account with other services. State keys, S3 list prefixes and DynamoDB lock partition keys are restricted per environment. See [SNS service authorisation](https://docs.aws.amazon.com/service-authorization/latest/reference/list_sns.html).

## Scanner exceptions

Only these resource-specific tfsec exceptions are configured. There is no global HIGH suppression and image scans fail on HIGH/CRITICAL, including unfixed findings.

| ID | Resource / scanner rule | Reason and mitigation | Review trigger |
|---|---|---|---|
| SNS-01 | Alarm topic / `aws-sns-enable-topic-encryption` (AVD-AWS-0095, HIGH) | Demo alarm notifications contain operational metric names and no customer payloads. HTTPS protects delivery. The topic policy restricts CloudWatch publishes to the exact alarms. A customer-managed key adds recurring cost; the AWS-managed SNS key cannot be configured with the required CloudWatch service policy. | Any sensitive notifications or deployment beyond a demo account. |
| STATE-01 | State bucket SSE / `aws-s3-encryption-customer-key` (AVD-AWS-0132, HIGH) | SSE-S3 encrypts state at rest without a dedicated key fee. All public access is blocked, TLS is enforced, versioning is on and delivery roles are scoped to their state keys. | Customer data or a policy requiring a separately managed encryption key. |

Lower-severity findings, such as default encryption rather than dedicated keys, short demo log retention, no VPC and no active X-Ray tracing, remain visible in full scanner output. Review them before expanding scope. No HIGH image exception has been approved; any image vulnerability must be fixed before release.

## Data and publication

Never store real personal data in this unauthenticated demo. Bounded scans and asynchronous TTL are convenience limits, not a security or spending boundary. API Gateway has no load balancer or WAF in this minimal design.

State, saved plans, tfvars, local config and private validation logs are ignored. GitHub configuration stores account-bearing ARNs/ECR URL/bucket name as secrets. Credentials actions mask the AWS account. Terraform and Docker push output are kept off public logs. PR comments contain action counts only. The owner must redact account IDs, emails, tokens and account-bearing URLs from screenshots before publication. Review tracked files and run a secret scan before every push.

Dependency and base-image vulnerabilities change. A previous green scan is historical evidence; every new release is scanned again. The base image and runtime dependencies are pinned; OS packages receive current vendor security updates during build. The local Lambda emulator and build-only pip/setuptools are removed from the final image. Review and refresh dependencies when scanning identifies an issue. Build provenance attestations are disabled because Lambda requires a single-platform image manifest; the deployed and promoted artifact is pinned by digest. Source-identical rebuilds can still differ after vendor OS updates.

SNS exception reference: [AWS event sources and encrypted topic key policies](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html).
