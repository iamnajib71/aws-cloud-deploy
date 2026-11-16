"""Apply a digest, test readiness, and restore the previous digest on failure."""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if __package__:
    from scripts.environment import terraform_environment
else:
    from environment import terraform_environment


def terraform(*args, check=True):
    result = subprocess.run(
        [os.getenv("TERRAFORM", "terraform"), "-chdir=infra/live", *args],
        capture_output=True,
        text=True,
        check=False,
        env=terraform_environment(),
    )
    private = Path("artifacts/private")
    private.mkdir(parents=True, exist_ok=True)
    with (private / "terraform.log").open("a", encoding="utf-8") as log:
        log.write(result.stdout + result.stderr)
    if check and result.returncode:
        raise RuntimeError("Terraform failed; inspect the private runner log")
    return result


def output(name):
    result = terraform("output", "-raw", name, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def smoke(endpoint, attempts=12):
    if not endpoint or not endpoint.startswith("https://"):
        return False
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(endpoint.rstrip("/") + "/health", timeout=15) as response:
                body = json.load(response)
                if response.status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                    return True
        except (OSError, ValueError, urllib.error.URLError):
            pass
        if attempt + 1 < attempts:
            time.sleep(5)
    return False


def deploy():
    previous = output("image_uri")
    candidate = os.environ["TF_VAR_image_uri"]
    applied = terraform("apply", "-auto-approve", "-input=false", check=False).returncode == 0
    if applied and smoke(output("endpoint")):
        print("Deployment passed readiness checks.")
        return 0
    if previous and previous != candidate:
        os.environ["TF_VAR_image_uri"] = previous
        terraform("apply", "-auto-approve", "-input=false")
        if not smoke(output("endpoint")):
            raise RuntimeError("Rollback readiness failed; follow the incident runbook")
        print("Candidate failed. Previous image restored and readiness verified.")
    elif previous:
        print("Current image failed readiness; no distinct previous image is available.")
    else:
        print("First deployment failed; no previous image exists. Fix or destroy this environment.")
    return 1


if __name__ == "__main__":
    sys.exit(deploy())
