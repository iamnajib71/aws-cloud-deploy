import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from scripts import deploy, manage

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path("config.local.json")


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Local configuration must be a JSON object.")
    rules = {
        "repository": r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        "region": r"[a-z]{2}(?:-[a-z]+)+-[0-9]+",
        "state_bucket": r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]",
        "alert_email": r"[^\s@]+@[^\s@]+\.[^\s@]+",
    }
    for key, pattern in rules.items():
        value = config.get(key)
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError(f"Invalid {key.replace('_', ' ')} in local configuration.")
    bucket = config["state_bucket"]
    if ".." in bucket or ".-" in bucket or "-." in bucket or re.fullmatch(r"[0-9.]+", bucket):
        raise ValueError("State bucket must be a valid S3 bucket name, not an IP address.")
    return config


def load_config():
    if not CONFIG.exists():
        raise ValueError("No local configuration. Run: python -m cloud_deploy init")
    return validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))


def initialise(args):
    if CONFIG.exists():
        raise ValueError("Local configuration already exists; edit it locally to change settings.")
    fields = {
        "repository": "GitHub repository (owner/name)",
        "region": "AWS region (for example us-east-1)",
        "state_bucket": "Globally unique state bucket name",
        "alert_email": "Budget and alarm email address",
    }
    config = {
        key: getattr(args, key) or input(f"{label}: ").strip() for key, label in fields.items()
    }
    validate_config(config)
    # Exclusive creation prevents accidental replacement of an existing private config.
    descriptor = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(config, output, indent=2)
        output.write("\n")
    print("Created ignored config.local.json. No cloud resources were created.")
    print("Next: python -m cloud_deploy doctor; then follow docs/setup.md for first apply.")
    return 0


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        return result if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def doctor(check_aws=False):
    problems = 0
    for name in ["git", "terraform", "aws", "docker"]:
        executable = os.getenv("TERRAFORM") if name == "terraform" else None
        executable = executable or shutil.which(name)
        if not executable:
            print(f"[missing] {name}: install it and add it to PATH")
            problems += 1
            continue
        if name == "terraform":
            result = probe([executable, "version", "-json"])
            try:
                ready = result and json.loads(result.stdout)["terraform_version"].startswith(
                    "1.13."
                )
            except (KeyError, ValueError):
                ready = False
            hint = "use Terraform 1.13.x"
        elif name == "docker":
            ready = probe([executable, "info", "--format", "{{.ServerVersion}}"])
            hint = "start the Docker engine"
        elif name == "aws":
            result = probe([executable, "--version"])
            ready = result and "aws-cli/2." in result.stdout + result.stderr
            hint = "install AWS CLI v2"
        else:
            ready = probe([executable, "--version"])
            hint = "check the executable"
        print(f"[ok] {name}" if ready else f"[fix] {name}: {hint}")
        problems += int(not bool(ready))
    try:
        config = load_config()
        print("[ok] local configuration (private values hidden)")
    except (ValueError, OSError) as error:
        print(f"[fix] {error}")
        config = None
        problems += 1
    if check_aws and config:
        ready = probe(["aws", "sts", "get-caller-identity", "--region", config["region"]])
        print(
            "[ok] AWS session (identity hidden)"
            if ready
            else "[fix] AWS session: sign in with short-lived credentials"
        )
        problems += int(not bool(ready))
    print("No cloud resources were created. First bootstrap apply remains a manual step.")
    return int(problems > 0)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m cloud_deploy",
        description="Configure, check and tear down the AWS Cloud Deploy starter.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create ignored local configuration; no AWS changes")
    for field in ["repository", "region", "state_bucket", "alert_email"]:
        init.add_argument("--" + field.replace("_", "-"))
    diagnostics = commands.add_parser("doctor", help="check tools and local configuration")
    diagnostics.add_argument(
        "--aws", action="store_true", help="also verify an AWS session read-only"
    )
    health = commands.add_parser("health", help="check a deployed API's /health response")
    health.add_argument("url", help="HTTPS API base URL")
    commands.add_parser("destroy", help="destroy dev, prod and bootstrap; retain state bucket")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return initialise(args)
        if args.command == "doctor":
            return doctor(args.aws)
        if args.command == "health":
            url = urlsplit(args.url)
            if (
                url.scheme != "https"
                or not url.netloc
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError(
                    "Use an HTTPS API base URL without credentials, query or fragment."
                )
            healthy = deploy.smoke(args.url, attempts=3)
            print("Readiness passed." if healthy else "Readiness failed.")
            return int(not healthy)
        manage.destroy(load_config())
        return 0
    except (ValueError, OSError, EOFError, subprocess.SubprocessError) as error:
        # Do not print subprocess commands or config contents: they can contain private values.
        if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError):
            print(f"Error: {error}")
        else:
            print("Command failed. Check tools, local configuration and your private session.")
        return 1


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())
