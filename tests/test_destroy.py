import subprocess
from types import SimpleNamespace

import pytest

from scripts import manage


def test_destroy_handles_partial_first_apply_before_deleting_shared(monkeypatch):
    order = []
    monkeypatch.setattr(manage, "configure", lambda config, root, environment=None: None)

    def run(root, *args, **kwargs):
        if args[0] == "output":
            return SimpleNamespace(stdout="{}")
        if args[0] == "state":
            return SimpleNamespace(stdout="module.app.aws_lambda_function.api\n")
        order.append(root)
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(manage, "run", run)
    manage.destroy({})
    assert order == ["live", "live", "bootstrap"]
    assert manage.os.environ["TF_VAR_image_uri"].endswith("0" * 64)


def test_destroy_stops_before_shared_if_workload_cleanup_fails(monkeypatch):
    monkeypatch.setattr(manage, "configure", lambda *a, **k: None)
    shared = []

    def run(root, *args, **kwargs):
        shared.append(root)
        if args[0] == "output":
            return SimpleNamespace(stdout="{}")
        if args[0] == "state":
            return SimpleNamespace(stdout="partial-resource")
        raise subprocess.CalledProcessError(1, "terraform destroy")

    monkeypatch.setattr(manage, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        manage.destroy({})
    assert "bootstrap" not in shared


@pytest.mark.parametrize("message,skip", [("No state file was found!", True),
                                         ("AccessDenied: state is inaccessible", False)])
def test_destroy_skips_missing_state_but_preserves_access_errors(monkeypatch, message, skip):
    monkeypatch.setattr(manage, "configure", lambda *a, **k: None)
    destroyed = []

    def run(root, *args, **kwargs):
        if args[0] == "output":
            return SimpleNamespace(stdout="{}")
        if args[0] == "state":
            raise subprocess.CalledProcessError(1, "terraform state list", stderr=message)
        destroyed.append(root)
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(manage, "run", run)
    if skip:
        manage.destroy({})
        assert destroyed == ["bootstrap"]
    else:
        with pytest.raises(subprocess.CalledProcessError):
            manage.destroy({})
        assert destroyed == []
