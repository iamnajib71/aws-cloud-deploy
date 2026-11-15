from types import SimpleNamespace

import pytest

from scripts import deploy


@pytest.mark.parametrize("applied,healthy", [(True, False), (False, False)])
def test_failed_candidate_restores_previous(monkeypatch, applied, healthy):
    calls = []
    monkeypatch.setenv("TF_VAR_image_uri", "candidate")
    monkeypatch.setattr(
        deploy, "output", lambda name: "previous" if name == "image_uri" else "https://api"
    )
    responses = iter([healthy, True] if applied else [True])
    monkeypatch.setattr(deploy, "smoke", lambda _: next(responses))

    def terraform(*args, **kwargs):
        calls.append(deploy.os.environ["TF_VAR_image_uri"])
        return SimpleNamespace(returncode=0 if len(calls) > 1 or applied else 1)

    monkeypatch.setattr(deploy, "terraform", terraform)
    assert deploy.deploy() == 1
    assert calls == ["candidate", "previous"]


def test_success_does_not_rollback(monkeypatch):
    monkeypatch.setenv("TF_VAR_image_uri", "candidate")
    monkeypatch.setattr(deploy, "output", lambda _: "https://api")
    monkeypatch.setattr(deploy, "terraform", lambda *a, **k: SimpleNamespace(returncode=0))
    monkeypatch.setattr(deploy, "smoke", lambda _: True)
    assert deploy.deploy() == 0
    assert deploy.os.environ["TF_VAR_image_uri"] == "candidate"


def test_first_deploy_has_no_rollback(monkeypatch, capsys):
    monkeypatch.setenv("TF_VAR_image_uri", "candidate")
    monkeypatch.setattr(deploy, "output", lambda _: None)
    monkeypatch.setattr(deploy, "terraform", lambda *a, **k: SimpleNamespace(returncode=1))
    assert deploy.deploy() == 1
    assert "no previous image" in capsys.readouterr().out


def test_failed_rollback_is_an_incident(monkeypatch):
    monkeypatch.setenv("TF_VAR_image_uri", "candidate")
    monkeypatch.setattr(deploy, "output", lambda _: "previous")
    monkeypatch.setattr(deploy, "terraform", lambda *a, **k: SimpleNamespace(returncode=0))
    monkeypatch.setattr(deploy, "smoke", lambda _: False)
    with pytest.raises(RuntimeError, match="Rollback readiness failed"):
        deploy.deploy()


@pytest.mark.parametrize(
    "body,expected",
    [
        (b'{"status":"ok"}', True),
        (b"[]", False),
        (b"not-json", False),
        (b'{"status":"bad"}', False),
    ],
)
def test_smoke_requires_valid_readiness_json(monkeypatch, body, expected):
    from io import BytesIO

    class Reply(BytesIO):
        status = 200

    monkeypatch.setattr(deploy.urllib.request, "urlopen", lambda *a, **k: Reply(body))
    assert deploy.smoke("https://example.invalid", attempts=1) is expected
