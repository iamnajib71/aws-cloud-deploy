# Deploy with a temporary session on the new AWS Free experience

The new AWS experience's managed policy blocks IAM identity-provider operations on both Free and Paid simplified projects. The default GitHub OIDC bootstrap cannot run there. A plan upgrade alone does not remove that restriction. Advanced activation is a separate, irreversible choice; this starter does not perform it.

Local-session mode keeps the same Lambda container, HTTP API, DynamoDB table, monitoring, budget and remote state. GitHub verification remains enabled, while GitHub cloud planning, deployment and production promotion remain disabled. This mode does **not** satisfy the automated OIDC delivery acceptance checks.

## Configuration

Add these settings to your ignored `config.local.json`, alongside the required repository, region, state bucket and alert email:

```json
{
  "enable_github_oidc": false,
  "reserved_concurrent_executions": -1,
  "aws_profile": "YOUR-TEMPORARY-SESSION-PROFILE"
}
```

Use the project region shown in AWS Settings. Do not copy another project's region or identifiers. Pass `TF_VAR_enable_github_oidc=false` when applying `infra/bootstrap`. The plan must contain no OIDC provider or GitHub delivery-role resources. It retains Lambda runtime roles, ECR, the lock table and budget alerts.

The live root defaults to shared Lambda concurrency (`-1`) because a new project's small quota may not support a reservation. API Gateway throttling remains enabled. Set a positive `reserved_concurrent_executions` only after verifying the available unreserved quota. Neither throttling nor a budget email is a hard spending cap.

## Temporary authentication and remote state

Use a browser-authenticated profile. Older Terraform S3 backends may need a separate shared-config profile with `credential_process` pointing to the AWS CLI's `configure export-credentials --profile YOUR-LOGIN-PROFILE --format process`. The backend then requests temporary credentials without putting keys into a tfvars file or repository.

On Windows, use the executable's full path, quoted only when the path needs it. Keep this in the private AWS shared configuration file. Never print the exported credential response or copy it to evidence files.

For Docker pushes, use the official Amazon ECR credential helper with the temporary profile. Keep registry configuration in a private Docker config directory. Avoid recording registry credentials in shell history or public logs.

## Release sequence

1. Review and apply the state bucket; migrate its state into the encrypted remote backend.
2. Review and apply bootstrap with OIDC disabled. Confirm both budget thresholds.
3. Build and scan a single-platform Lambda container. Push an immutable tag to ECR and resolve its digest.
4. Initialise the dev backend with S3 and DynamoDB locking, set the digest as `TF_VAR_image_uri`, and run `python scripts/deploy.py` with the same Terraform/profile environment.
5. Test readiness and fictional item storage. Run `terraform plan -detailed-exitcode` with the same inputs to check for drift.
6. Confirm the SNS email subscription. Keep screenshots owner-captured and redact private identifiers.

Keep `BOOTSTRAP_READY` unset in GitHub for this mode. A local deployment is not a GitHub OIDC deploy. Local readiness rollback uses the same Terraform recovery script, but its result must be recorded separately from a workflow run.

## Cost and teardown

Free-plan credits and allowances are finite. A credit-funded demo is not permanently free hosting. Retained state, ECR storage, traffic and monitoring can incur usage charges. See [cost guidance](cost.md).

`python -m cloud_deploy destroy` removes dev, prod if present, and bootstrap using the mode recorded in local configuration. It retains the state bucket. The `make destroy` alias remains available.

References: [managed project policies](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html), [credential-process output](https://docs.aws.amazon.com/cli/latest/reference/configure/export-credentials.html), [advanced activation consequences](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html).
