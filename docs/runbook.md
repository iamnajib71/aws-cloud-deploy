# Operations runbook

## Deploy

Complete [owner setup](setup.md), confirm the budget and SNS subscriptions, then merge a reviewed change to main. Check Verify, dev release, readiness and no-drift steps. Review the immutable image digest before approving the protected production environment. Production cannot run after a failed dev job.

Public runner logs suppress raw Terraform output and account information. Terraform output is written to `artifacts/private/terraform.log` on the ephemeral runner. For investigation reproduce the failed command in the owner's private terminal; do not upload raw plans, state, logs or account-bearing output as public artifacts.

`/health` reads DynamoDB through the runtime role; `/items` supports bounded demonstration storage; `/metrics` exposes in-process Prometheus values. Use fictional item data only.

## Deliberately broken release

1. Obtain a successful healthy dev release first. Record its workflow URL and image digest privately.
2. Create a PR changing only `ENV RELEASE_HEALTH=healthy` to `ENV RELEASE_HEALTH=broken` in the Dockerfile. This bakes a failing `/health` into that candidate image. Source tests still check both healthy and failing behaviour.
3. Let PR tests, infrastructure checks, image scan and plan finish. Review and merge the drill PR to main.
4. Observe the release apply followed by failing health checks. The script re-applies the previous image digest and checks health again. The workflow remains red to report the rejected candidate; the log must explicitly say the previous image was restored and readiness verified.
5. Confirm `/health` returns HTTP 200 and `{"status":"ok"}` after rollback. Confirm the Terraform state's image matches the earlier healthy digest, using a private terminal.
6. Revert the Dockerfile change in a reviewed PR and merge it. Do not approve the broken image for prod. Link the baseline run, rejected run and recovery evidence in the register.

Breaking a health function directly may be caught by source tests before deployment, which is desirable. The image configuration drill deliberately tests the post-deployment path while preserving unit-test coverage.

## Manual rollback

With an owner or appropriate environment session, run `python scripts/manage.py init --environment dev` (or `prod`). Set `TF_VAR_region`, `TF_VAR_environment`, `TF_VAR_alert_email` and `TF_VAR_image_uri` to the known-good ECR digest. Use the same `TF_DATA_DIR` selected by the lifecycle command; because it is set in a child process, set it in your shell before subsequent Terraform commands (see below).

```sh
export TF_DATA_DIR="$(pwd)/.terraform/dev"
terraform -chdir=infra/live plan
terraform -chdir=infra/live apply
```

PowerShell: `$env:TF_DATA_DIR = (Join-Path (Get-Location) '.terraform/dev')`. Confirm health and run another plan. Never mutate Lambda directly as normal recovery: it causes state drift. If infrastructure changes broke the service, revert the infrastructure commit as well; image rollback cannot restore removed data or previous schema.

## Alarm response

For 5xx alarms, inspect the HTTP API 5xx percentage, Lambda errors and structured logs. Check recent image releases, DynamoDB errors and IAM denials. Restore the known-good digest if a release caused the incident. Check the rollback log and test the endpoint.

For p95 latency alarms, compare integration latency, cold starts, throttles and DynamoDB timing. The configured percentile evaluates low sample counts, so a slow cold start can trigger a demo alarm. Missing traffic is treated as not breaching; it is not an availability check.

For budget notifications, inspect the account's billing breakdown immediately, stop demo traffic, and destroy the project if it is no longer needed. Budget notices can arrive after costs accrue and are not a hard stop. If requests are abusive, remove the HTTP API or destroy the environment; do not wait for an alert to enforce a cap.

Test alarm delivery by generating controlled demo traffic or by briefly setting an alarm to ALARM through the owner session; capture the email and restore its state. A forced alarm-state test proves notification wiring, not threshold correctness. Never claim both from one screenshot.

## Destroy and verify

Freeze merges and cancel/wait for all queued deploy and approval jobs. Disable the deployment workflow temporarily so an approved waiting job cannot recreate infrastructure during cleanup. From an owner session and with `config.local.json` present:

```sh
make destroy
```

This destroys prod, dev, then shared bootstrap (including images, roles, OIDC provider, budget and lock table). It retains `infra/state`: the bucket, privacy/encryption/versioning/lifecycle controls and state objects. It intentionally does not destroy a shared provider imported from another project; do not bootstrap such a provider without adapting ownership first.

Check Terraform state lists and each used AWS region for remaining Lambda functions, APIs, application/lock tables, ECR images/repositories, log groups, dashboards, alarms, SNS topics and IAM roles. Check Budgets and OIDC separately because they are global/account services. Tag filters alone cannot prove everything is gone. Confirm there are no queued jobs that can recreate the stack.

The retained S3 objects and historical DynamoDB recovery data, delayed usage charges and billing rounding can still produce charges. Recheck billing after the reporting delay. This command removes the running footprint; it cannot honestly guarantee a $0 invoice while retaining a non-empty state bucket.

For strict zero retained storage, the owner must first export any required recovery state securely, deliberately remove the bucket's `prevent_destroy`, empty **all object versions and delete markers**, and destroy `infra/state` from a separate safe local backend. This is outside `make destroy` and should not be automated accidentally.
