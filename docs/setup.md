# Owner setup and first release

## Owner-only prerequisites

For the new AWS Free experience, check [local-session deployment](free-project.md) first. Its managed policy blocks GitHub OIDC provider operations, so the standard automated bootstrap below requires an AWS environment that permits them.

The owner must create the AWS account, enable root MFA, choose/create the budget email and personally run the initial Terraform applies. Do not use the root identity for routine work. Use a short-lived administrative session, such as IAM Identity Center. Do not create repository access keys.

Install Terraform matching the version constraint, AWS CLI v2, Docker, Python and optionally Make. Start Docker. Choose one region and keep it consistent. Lambda uses shared concurrency by default so a small new-project quota does not block deployment. An optional reservation requires sufficient unreserved capacity. Confirm spending/free-tier eligibility in the billing console.

Use an isolated demo account: the HTTP API permission scope and account-wide budget are unsuitable for an account holding unrelated production services. Check for an existing GitHub OIDC provider before bootstrap. If one already exists, import it into the bootstrap only when this project owns its lifecycle; otherwise adapt the provider reference and do not destroy a shared provider.

## Local private configuration

Recommended: run `python -m cloud_deploy init`, then `python -m cloud_deploy doctor`. The CLI creates the file below without creating cloud resources. Use `doctor --aws` to verify your session without displaying its identity.

Alternatively, create `config.local.json` (ignored). Substitute your real values locally; never commit them:

```json
{
  "region": "us-east-1",
  "state_bucket": "YOUR-GLOBALLY-UNIQUE-PRIVATE-BUCKET",
  "repository": "YOUR-OWNER/YOUR-REPOSITORY",
  "alert_email": "YOUR-NOTIFICATION-EMAIL"
}
```

Use the same values as Terraform environment variables, rather than committing a tfvars file:

```sh
export TF_VAR_region=us-east-1
export TF_VAR_bucket_name=YOUR-GLOBALLY-UNIQUE-PRIVATE-BUCKET
export TF_VAR_state_bucket="$TF_VAR_bucket_name"
export TF_VAR_repository=YOUR-OWNER/YOUR-REPOSITORY
export TF_VAR_alert_email=YOUR-NOTIFICATION-EMAIL
```

PowerShell equivalent is `$env:TF_VAR_region = 'us-east-1'` and similarly for the other variables. Run AWS CLI identity verification privately. Do not paste its account output into public files.

## First apply: owner runs these commands

```sh
terraform -chdir=infra/state init
terraform -chdir=infra/state plan
terraform -chdir=infra/state apply
terraform -chdir=infra/bootstrap init \
  -backend-config="bucket=$TF_VAR_state_bucket" \
  -backend-config="region=$TF_VAR_region" \
  -backend-config="key=bootstrap/terraform.tfstate"
terraform -chdir=infra/bootstrap plan
terraform -chdir=infra/bootstrap apply
```

Migrate the retained bucket's initially local state to that same bucket, using S3 native locking. Add a local-only `infra/state/backend_override.tf` containing:

```hcl
terraform {
  backend "s3" { use_lockfile = true }
}
```

Then run `terraform -chdir=infra/state init -migrate-state` with bucket/region arguments and `-backend-config=key=state/terraform.tfstate`. Securely retain any local recovery copies outside version control. This is not done by the delivery workflows.

Confirm budget notifications in AWS and confirm each SNS subscription email after an environment is deployed. Unconfirmed subscriptions do not deliver alarms.

## Publish and protect the repository

Create your public repository from the template and push the source using your own Git identity. Never publish private output or state. Suggested About description: `Deploy small APIs to AWS with Terraform, OIDC delivery and readiness-based rollback.` Suggested topics: `aws`, `terraform`, `github-actions`, `oidc`, `lambda`, `dynamodb`, `cloudwatch`, `serverless`.

Set repository variable `AWS_REGION`. Set repository secrets `STATE_BUCKET`, `ALERT_EMAIL`, `ECR_URL`, `AWS_PLAN_ROLE_ARN`. Obtain ECR URL and role ARNs privately with `terraform output -raw ecr_url` and `terraform output -json delivery_roles` in `infra/bootstrap`. Leave `BOOTSTRAP_READY` unset until setup is complete: source verification runs, while AWS release jobs stay skipped. Set `BOOTSTRAP_READY=true` only after configuring trust, secrets and environment protection, then dispatch Deploy from main.

Create GitHub environments `dev` and `prod`. Each gets its corresponding `AWS_DEPLOY_ROLE_ARN` environment secret. Restrict deployment branches to `main` for both. Configure a required owner reviewer for `prod` **before running a release**. This solo lab allows owner self-review so its owner can demonstrate manual approval; a team deployment should require an independent reviewer. The workflow's environment field alone does not enforce manual approval. Verify your repository/plan supports these protection rules.

Require Verify checks for `main` and review same-repository PRs before running their workflows. Fork PRs run static verification only, with no AWS plan or comment credentials. Never switch to `pull_request_target` to execute PR code with cloud access. Require reviewed approval for outside collaborators' workflow runs.

## OIDC subject compatibility

Before planning an OIDC-enabled bootstrap, inspect your repository's exact subject prefix with `gh api repos/YOUR-OWNER/YOUR-REPOSITORY/actions/oidc/customization/sub`. Set `TF_VAR_github_oidc_subject_prefix` to its `sub_claim_prefix` value, without adding a branch or environment suffix. New GitHub repositories include immutable owner/repository IDs in that prefix; an older name-only example may not match their tokens.

## Deploy and verify

Merge a healthy change to main. The deploy workflow verifies, builds/scans an image, pushes an immutable commit-SHA tag, resolves the digest, applies dev, checks readiness, and requires a no-drift plan. Approve prod only after reviewing dev. Production receives that exact digest.

The plan job on subsequent same-repository PRs reads the current dev image from state; it deliberately requires an initial successful dev deployment. Before `BOOTSTRAP_READY=true`, cloud planning and release jobs are skipped while source verification runs. Once ready, same-repository PRs must produce a plan. It comments action counts, never raw plan values. Full plans/state stay off public artifacts. A clean clone must use the same backend, environment, notification email and deployed image digest to reproduce an empty plan.

Follow [the rollback drill](runbook.md#deliberately-broken-release) after the baseline release. Capture and redact the owner screenshots yourself, then fill the [evidence register](evidence.md). Profile promotion is gated by that evidence.
