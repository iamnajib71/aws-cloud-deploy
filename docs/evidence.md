# Evidence register

The dev API was deployed to real AWS in `ap-southeast-2` and verified before owner-requested teardown. Endpoint checks below are historical deployment evidence, not a promise of an available service. Deployment and automatic recovery used a temporary local session because this project's managed policy blocks OIDC provider creation. These results are separate from hosted CI verification.

| Claim | Required evidence | Status |
|---|---|---|
| Application and recovery logic tested locally | [Local validation](evidence/local-validation.md), repeatable tests | See local report |
| User CLI and configuration safety | [CLI validation](evidence/cli-validation.json), [help output](evidence/cli-help.txt) and `tests/test_cli.py` | Passed locally; no cloud apply |
| Hosted verification | [Successful run](https://github.com/iamnajib71/aws-cloud-deploy/actions/runs/43839148817): source tests, Terraform validation/lint, tfsec, image build and Trivy | Passed; AWS jobs skipped |
| Healthy release to real AWS via local session | [Health, fictional item persistence and metrics](evidence/live-verification.json) | Passed |
| GitHub OIDC deployment | Exact successful and rejected Deploy workflow URLs | Pending; identity-provider operations blocked in this project |
| Broken image automatically restored via local session | [Rejected candidate and recovered digest](evidence/live-rollback.json), `scripts/deploy.py` | Passed; candidate command exits 1 to report rejection |
| Protected same-image promotion | Prod environment approval and matching dev/prod digest, with run links | Pending |
| No drift from a clean clone | [Post-recovery plan](evidence/clean-clone-plan.json), source commit and exit 0 | Passed |
| Image scan acceptance | [Sanitised Trivy summary for deployed digest](evidence/deployed-image-scan.json) | No HIGH/CRITICAL findings; no image exceptions |
| Monitoring configuration and subscription | [AWS API readback](evidence/monitoring-verification.json) | Dashboard, two alarms and confirmed email subscription verified |
| Alarm email delivery | [Sanitised owner-reported receipt of both actual alarm emails](evidence/alarm-delivery.json) | Confirmed during the live drill |
| Console screenshots | Owner dashboard/alarm screenshots | Pending |
| Monthly running cost | Owner Cost Explorer screenshot, period, gross usage and net cost | Pending |
| Teardown | [Successful destroy and AWS inventory](evidence/teardown.json) | Workload removed; owner also approved state bucket deletion after private backup. Delayed billing review pending |
| Demo | Owner-recorded 30–90 second GIF showing deployment and recovery | Pending |

Machine-readable records are sanitised observations from actual checks, not independent audit attestations. Raw state, plans, registry metadata and Terraform logs remain private. The deployed application image was built from commit `28bcd95ac9f0f1bf08d3878aefcabaf395417855`. The subsequent Windows runner correction was exercised during recovery and does not alter the image contents. Never describe local recovery as a GitHub workflow run.

Workflow URLs must identify actual runs, not the workflow landing page. A rejected deployment should remain red even when recovery succeeds. Record the reason clearly so a reviewer can distinguish expected rejection from an unresolved incident.

Screenshots are captured by the owner. Review redaction before staging any image. Never fabricate console screenshots or replace missing evidence with example output.

After live evidence is complete, add profile fact `aws_cloud_deploy` with one headline sentence and one detail sentence backed by those runs; pin the repository and add AWS to LinkedIn/SEEK skills. These steps are deliberately pending. Do not claim live deployment from static Terraform validation alone.
