# Command reference

Run commands from your clone with Python 3.11 or newer. The CLI uses the standard library; installing application dependencies is only needed to develop or test the sample API.

```sh
python -m cloud_deploy --help
python -m cloud_deploy init
python -m cloud_deploy doctor
python -m cloud_deploy doctor --aws
python -m cloud_deploy health https://YOUR-API-URL
python -m cloud_deploy destroy
```

| Command | Does | Creates cloud resources? |
|---|---|---|
| `init` | Prompts for repository, region, bucket name and alert email; creates ignored `config.local.json`. Refuses to overwrite it. | No |
| `doctor` | Checks Git, Terraform version, AWS CLI v2, Docker engine and configuration. Reports what to fix. | No |
| `doctor --aws` | Also verifies your current AWS session without printing identity values. | No; read-only AWS request |
| `health URL` | Checks for HTTP 200 and `{"status":"ok"}` at the API's `/health` endpoint. | No; sends requests to the URL |
| `destroy` | Removes dev, prod and bootstrap in dependency order. Stops on cleanup failure. | No; deletes resources |

`init` also accepts `--repository`, `--region`, `--state-bucket`, `--alert-email` and optional `--profile` for non-interactive use. Prefer the prompts to avoid putting private values in shell history. Configuration is validated before it is written. Edit the ignored file to change it; there is no silent overwrite option.

Exit code 0 means the command passed. Exit code 1 means readiness, prerequisites or an operation failed; usage errors return 2. `doctor` does not apply Terraform or validate AWS permissions for every resource. A healthy STS session does not prove deployment permission.

`destroy` operates on the configured account and state bucket. Stop pending delivery jobs first. It retains the state bucket and its contents; use the [runbook](runbook.md#destroy-and-verify) to verify cleanup and residual charges. There is no automated initial bootstrap command: the owner must run the first applies personally.

## Troubleshooting

| Message / symptom | Action |
|---|---|
| Tool missing | Install the prerequisite and reopen your terminal so PATH is refreshed. |
| Terraform version mismatch | Use Terraform 1.13.x, matching the repository constraint. |
| Docker found but not ready | Start Docker Desktop or the Docker daemon. |
| No local configuration | Run `python -m cloud_deploy init` from the clone. |
| Configuration already exists | Edit `config.local.json`; existing values were preserved. |
| AWS session fails | Sign in with your short-lived owner/deployment session, then repeat `doctor --aws`. |
| Health fails | Check the API base URL, deployment status, Lambda logs and DynamoDB access. See the incident runbook. |
| Hosted cloud jobs skipped | Complete owner bootstrap and GitHub configuration, then set `BOOTSTRAP_READY=true`. |

For a custom Terraform executable, set `TERRAFORM` to its path. The CLI and existing lifecycle scripts honour that setting.
