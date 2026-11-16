mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "test-project" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

variables {
  region       = "ap-southeast-2"
  state_bucket = "example-deployment-state"
  repository   = "example/api"
  alert_email  = "alerts@example.invalid"
}

run "local_session_excludes_federation" {
  command = plan
  variables { enable_github_oidc = false }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0 && length(aws_iam_role.github) == 0
    error_message = "Local-session mode must not create an identity provider or GitHub delivery roles."
  }
  assert {
    condition     = length(module.runtime) == 2 && length(aws_budgets_budget.monthly.notification) == 2
    error_message = "Runtime roles and both budget alerts must remain in local-session mode."
  }
}

run "oidc_mode_preserves_identity_controls" {
  command = plan
  variables {
    enable_github_oidc         = true
    github_oidc_subject_prefix = "repo:example@42/api@84"
  }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 1 && length(aws_iam_role.github) == 3
    error_message = "OIDC mode must create one provider and separate plan/dev/prod roles."
  }
  assert {
    condition     = local.subject_prefix == "repo:example@42/api@84"
    error_message = "Immutable GitHub subject prefixes must be preserved exactly."
  }
}
