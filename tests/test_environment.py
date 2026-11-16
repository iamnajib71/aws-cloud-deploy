from scripts.environment import terraform_environment


def test_windows_variable_spelling_and_credentials_are_preserved(monkeypatch):
    monkeypatch.setenv("TF_VAR_IMAGE_URI", "example@sha256:digest")
    monkeypatch.setenv("TF_VAR_REGION", "ap-southeast-2")
    monkeypatch.setenv("AWS_PROFILE", "test-session")
    env = terraform_environment()
    assert env["TF_VAR_image_uri"] == "example@sha256:digest"
    assert env["TF_VAR_region"] == "ap-southeast-2"
    assert "TF_VAR_IMAGE_URI" not in env
    assert env["AWS_PROFILE"] == "test-session"
