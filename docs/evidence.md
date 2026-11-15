# Evidence register

The repository currently contains implementation and local checks. It does not yet establish hands-on deployment in the owner's AWS account.

| Claim | Required evidence | Status |
|---|---|---|
| Application and recovery logic tested locally | [Local validation](evidence/local-validation.md), repeatable tests | See local report |
| User CLI and configuration safety | [CLI validation](evidence/cli-validation.json), [help output](evidence/cli-help.txt) and `tests/test_cli.py` | Passed locally; no cloud apply |
| Hosted verification | [Successful run](https://github.com/iamnajib71/aws-cloud-deploy/actions/runs/43679091838): source tests, Terraform validation/lint, tfsec, image build and Trivy | Passed; AWS jobs skipped |
| Healthy release to real AWS | Exact successful Deploy workflow URL, redacted endpoint check and Terraform result | Pending |
| Broken release automatically restored | Exact rejected Deploy workflow URL with explicit rollback/readiness result; before/after digests redacted consistently | Pending |
| Protected same-image promotion | Prod environment approval and matching dev/prod digest, with run links | Pending |
| No drift from a clean clone | Redacted `plan -detailed-exitcode` result with exit 0, commit and environment | Pending |
| Image scan acceptance | Trivy HIGH/CRITICAL report for the deployed digest | Pending |
| Monitoring and email delivery | Owner dashboard, alarm and subscription/notification screenshots | Pending |
| Monthly running cost | Owner Cost Explorer screenshot, period, gross usage and net cost | Pending |
| Teardown | Redacted Terraform destroys, service checks, delayed billing review | Pending |
| Demo | Owner-recorded 30–90 second GIF showing deployment and recovery | Pending |

Workflow URLs must identify actual runs, not the workflow landing page. A rejected deployment should remain red even when recovery succeeds. Record the reason clearly so a reviewer can distinguish expected rejection from an unresolved incident.

Screenshots are captured by the owner. Review redaction before staging any image. Never fabricate console screenshots or replace missing evidence with example output.

After live evidence is complete, add profile fact `aws_cloud_deploy` with one headline sentence and one detail sentence backed by those runs; pin the repository and add AWS to LinkedIn/SEEK skills. These steps are deliberately pending. Do not claim live deployment from static Terraform validation alone.
