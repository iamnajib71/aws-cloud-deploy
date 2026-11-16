import json
from types import SimpleNamespace

import pytest

from cloud_deploy import __main__ as cli


@pytest.fixture
def config():
    return {
        "repository": "example/api",
        "region": "us-east-1",
        "state_bucket": "example-api-state",
        "alert_email": "demo@example.invalid",
    }


def test_init_creates_config_without_touching_cloud(tmp_path, monkeypatch, config, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: pytest.fail("No cloud commands"))
    args = [part for key, value in config.items() for part in ["--" + key.replace("_", "-"), value]]
    assert cli.main(["init", *args]) == 0
    assert json.loads(cli.CONFIG.read_text()) == config
    assert config["alert_email"] not in capsys.readouterr().out
    assert cli.main(["init", *args]) == 1
    assert json.loads(cli.CONFIG.read_text()) == config


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "missing-owner"),
        ("region", "unknown"),
        ("state_bucket", "127.0.0.1"),
        ("state_bucket", "invalid..name"),
        ("alert_email", "bad"),
    ],
)
def test_invalid_configuration_is_rejected(config, field, value):
    config[field] = value
    with pytest.raises(ValueError):
        cli.validate_config(config)


def test_doctor_hides_identity_and_skips_aws_by_default(monkeypatch, config, capsys):
    calls = []
    monkeypatch.setattr(cli.shutil, "which", lambda name: name)
    monkeypatch.setattr(cli, "load_config", lambda: config)

    def probe(args):
        calls.append(args)
        return SimpleNamespace(
            stdout=json.dumps({"terraform_version": "1.13.5"})
            if args[0] == "terraform"
            else "aws-cli/2.0 private-identity",
            stderr="",
        )

    monkeypatch.delenv("TERRAFORM", raising=False)
    monkeypatch.setattr(cli, "probe", probe)
    assert cli.main(["doctor"]) == 0
    assert not any("sts" in call for call in calls)
    assert cli.main(["doctor", "--aws"]) == 0
    assert any("sts" in call for call in calls)
    assert "private-identity" not in capsys.readouterr().out


def test_doctor_reports_missing_tools(monkeypatch, capsys):
    monkeypatch.delenv("TERRAFORM", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)
    monkeypatch.setattr(cli, "load_config", lambda: (_ for _ in ()).throw(ValueError("No config")))
    assert cli.main(["doctor"]) == 1
    assert "[missing] terraform" in capsys.readouterr().out


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid",
        "https://user:secret@example.invalid",
        "https://example.invalid?x=1",
    ],
)
def test_health_rejects_unsafe_url(url):
    assert cli.main(["health", url]) == 1


def test_health_propagates_failure(monkeypatch):
    monkeypatch.setattr(cli.deploy, "smoke", lambda *a, **k: False)
    assert cli.main(["health", "https://example.invalid"]) == 1


def test_destroy_requires_valid_config_before_any_cloud_call(monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: (_ for _ in ()).throw(ValueError("No config")))
    monkeypatch.setattr(cli.manage, "destroy", lambda _: pytest.fail("Must validate first"))
    assert cli.main(["destroy"]) == 1


def test_configuration_must_be_an_object():
    with pytest.raises(ValueError, match="JSON object"):
        cli.validate_config([])


def test_doctor_uses_configured_profile(monkeypatch, config):
    config["aws_profile"] = "temporary-project"
    calls = []
    monkeypatch.setattr(cli.shutil, "which", lambda name: name)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.delenv("TERRAFORM", raising=False)

    def probe(command):
        calls.append(command)
        return SimpleNamespace(
            stdout='{"terraform_version":"1.13.5"}' if command[0] == "terraform" else "aws-cli/2.0",
            stderr="",
        )

    monkeypatch.setattr(cli, "probe", probe)
    assert cli.main(["doctor", "--aws"]) == 0
    identity = next(command for command in calls if "sts" in command)
    assert identity[-2:] == ["--profile", "temporary-project"]


@pytest.mark.parametrize("field,value", [("aws_profile", 1), ("enable_github_oidc", "false")])
def test_local_deployment_config_types_are_validated(config, field, value):
    config[field] = value
    with pytest.raises(ValueError):
        cli.validate_config(config)
