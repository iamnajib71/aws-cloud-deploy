# Use this starter for your API

1. Select **Use this template → Create a new repository** on GitHub. Clone your own repository so workflows and OIDC trust belong to your namespace.
2. Run `python -m cloud_deploy init`. Enter **your** repository name, chosen region, unique bucket name and notification email. Run `doctor` to check prerequisites.
3. Keep the example API for the first healthy deployment. Complete [owner setup](setup.md), then verify baseline health before customising application behaviour.
4. Replace or extend `app/main.py`. The image must expose a Lambda-compatible handler and `/health` must return HTTP 200 with `{"status":"ok"}` when the service is ready. Keep the Docker `CMD` in sync if you rename the handler.
5. Update tests, pin runtime dependencies in `requirements-lock.txt`, and run source tests plus the image scan. `requirements.txt` records direct dependencies; the lock records the full runtime resolution. Review both when updating packages.
6. Merge changes for dev. Approve prod only after checking dev; production receives the same digest. Run the rollback drill before relying on the recovery path.

## What is configurable today?

| Setting | Where |
|---|---|
| Repository / OIDC subject | Local configuration and bootstrap `repository` variable |
| AWS region / state bucket / email | Local configuration, Terraform variables and GitHub configuration |
| Application and health readiness | `app/`, `tests/`, `Dockerfile` |
| Runtime size, concurrency, throttle and data TTL | `infra/modules/app/` and `app/main.py` |
| Alarm thresholds and dashboard | `infra/modules/observability/` |

Resource names currently use the fixed `aws-cloud-deploy` prefix. Use one installation per isolated AWS account/region; multi-project namespacing is not supported yet. The example endpoints are public and unauthenticated. Add an authorisation design before storing real user data.

Evidence links in a newly generated copy point to upstream verification. Replace them with your own runs before claiming that your copy is deployed. Repository secrets, environment protection and AWS resources are not copied by GitHub templates; configure them for your own repository.
