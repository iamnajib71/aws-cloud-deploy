# Local validation

Recorded on 15 November 2026. Machine-readable results: [local-checks.json](local-checks.json).

The live deployment update passes 36 Python tests and 3 Terraform mock tests. It also corrects Windows environment-variable spelling for Terraform. [Live deployment and recovery evidence](../evidence.md) is recorded separately.

The subsequent CLI usability update passes 32 tests, including the original API/recovery checks. Its separate [validation record](cli-validation.json) and actual [CLI help output](cli-help.txt) cover configuration, prerequisite diagnostics and endpoint validation. The earlier results below describe the initial implementation.

The same verification gates also passed on a [GitHub-hosted runner](https://github.com/iamnajib71/aws-cloud-deploy/actions/runs/43679091838). Dev and prod release jobs were skipped because owner bootstrap was not marked ready. This is verification evidence, not a cloud deployment.

| Check | Recorded result |
|---|---|
| API, HTTP API event adapter, readiness/recovery and teardown tests | 18 passed; 1 test-client dependency deprecation warning |
| Ruff | Passed |
| Terraform format and validation | Passed for state, bootstrap and live |
| TFLint | Passed |
| tfsec HIGH/CRITICAL gate | No unexcepted findings; the 2 resource-specific exceptions are in [security](../security.md) |
| Workflow syntax (actionlint) | Passed |
| Local Linux image build | Passed with a single-platform manifest |
| Trivy image HIGH/CRITICAL gate | No findings after vendor package updates and removal of unused build tooling/emulator |
| Runtime Python dependency audit | No findings across 19 resolved dependencies |

Tooling: Terraform 1.13.5, AWS provider 6.73.0, TFLint 0.59.1, tfsec 1.28.14, actionlint 1.7.7 and Trivy 0.76.2. Provider lock files include Windows and Linux checksums.

Reproduce with the commands in the workflows, or locally:

```sh
python -m ruff check app scripts tests
python -m pytest -q
terraform fmt -check -recursive infra
# Repeat for state, bootstrap and live:
terraform -chdir=infra/live init -backend=false -lockfile=readonly
terraform -chdir=infra/live validate
tflint --init
tflint --recursive
tfsec infra --minimum-severity HIGH
actionlint
docker build --platform linux/amd64 --provenance=false -t aws-cloud-deploy:local .
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 aws-cloud-deploy:local
python -m pip_audit -r requirements-lock.txt
```

Windows sandbox restrictions prevented local plugin sockets and async event loops. The successful checks used the required local process/loopback access. This is a validation environment issue, not evidence of AWS connectivity.

The initial vendor base image scan found vulnerable system RPMs, the local emulator and packages bundled inside pip. The Dockerfile applies vendor security updates and removes the emulator and build-only installer. No image finding was suppressed.

These results do **not** prove AWS IAM permissions, successful Terraform apply, live alarm delivery, no drift from a live account, automatic cloud rollback, measured cost or zero residual charges. See their current individual status in the [evidence register](../evidence.md).
