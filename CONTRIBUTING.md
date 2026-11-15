# Contributing

Useful contributions make a fresh clone easier to configure, verify, deploy or remove. Bug reports, documentation fixes and reproducible improvements are welcome.

Before opening a change:

```sh
python -m pip install -r requirements-dev.txt
python -m ruff check app cloud_deploy scripts tests
python -m pytest -q
terraform fmt -check -recursive infra
```

For infrastructure changes, also run Terraform validation, TFLint and tfsec as shown in the verification workflow. Container changes must pass Trivy with no HIGH/CRITICAL findings unless a specific exception has been reviewed and documented. Tests should exercise behaviour, especially failure and cleanup paths.

Use a small branch and explain the user problem, changed behaviour and checks performed. Do not include AWS identities, credentials, state, saved plans, real customer data or unredacted console output. Fork PRs run verification without cloud credentials. Maintainers must review same-repository changes before allowing a cloud plan.

Initial AWS account setup and the first bootstrap apply remain owner-controlled. Contributions do not require an AWS account to run the Python tests or CLI configuration checks.
