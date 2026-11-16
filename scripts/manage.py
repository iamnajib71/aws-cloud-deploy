"""Owner-side lifecycle commands. Never applies the owner bootstrap automatically."""

import argparse
import json
import os
import subprocess
from pathlib import Path

if __package__:
    from scripts.environment import terraform_environment
else:
    from environment import terraform_environment


def run(root, *args, capture=False):
    command = [os.getenv("TERRAFORM", "terraform"), f"-chdir=infra/{root}", *args]
    return subprocess.run(
        command, check=True, text=True, capture_output=capture, env=terraform_environment()
    )


def configure(config, root, environment=None):
    if config.get("aws_profile"):
        os.environ["AWS_PROFILE"] = config["aws_profile"]
    os.environ["TF_VAR_region"] = config["region"]
    os.environ["TF_VAR_alert_email"] = config["alert_email"]
    os.environ["TF_VAR_repository"] = config["repository"]
    os.environ["TF_VAR_state_bucket"] = config["state_bucket"]
    os.environ["TF_VAR_enable_github_oidc"] = str(config.get("enable_github_oidc", True)).lower()
    if config.get("github_oidc_subject_prefix"):
        os.environ["TF_VAR_github_oidc_subject_prefix"] = config["github_oidc_subject_prefix"]
    os.environ["TF_VAR_reserved_concurrent_executions"] = str(
        config.get("reserved_concurrent_executions", -1)
    )
    key = environment or "bootstrap"
    data_dir = Path(f".terraform/{key}").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TF_DATA_DIR"] = str(data_dir)
    args = [
        "init",
        "-input=false",
        f"-backend-config=bucket={config['state_bucket']}",
        f"-backend-config=region={config['region']}",
        f"-backend-config=key={key}/terraform.tfstate",
    ]
    if environment:
        os.environ["TF_VAR_environment"] = environment
        args.append("-backend-config=dynamodb_table=aws-cloud-deploy-locks")
    run(root, *args)


def destroy(config):
    # Destroy prod and dev before shared ECR, runtime roles and the lock table.
    for environment in ["prod", "dev"]:
        configure(config, "live", environment)
        values = json.loads(run("live", "output", "-json", capture=True).stdout)
        resources = run("live", "state", "list", capture=True).stdout.strip()
        if resources:
            # An interrupted first apply can have resources before outputs exist.
            os.environ["TF_VAR_image_uri"] = values.get("image_uri", {}).get(
                "value", "unused@sha256:" + "0" * 64
            )
            run("live", "destroy", "-auto-approve", "-input=false")
    configure(config, "bootstrap")
    run("bootstrap", "destroy", "-auto-approve", "-input=false")
    print("Workload and bootstrap destroyed. State bucket and its objects remain.")
    print("Verify regional resources and delayed billing using docs/runbook.md.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "destroy"])
    parser.add_argument("--environment", choices=["dev", "prod"], default="dev")
    args = parser.parse_args()
    config = json.loads(Path("config.local.json").read_text(encoding="utf-8"))
    if args.command == "destroy":
        destroy(config)
    else:
        configure(config, "live", args.environment)


if __name__ == "__main__":
    main()
