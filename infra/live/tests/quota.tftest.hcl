mock_provider "aws" {
  mock_data "aws_caller_identity" {
    # Synthetic ID used only by the mocked provider, never a real project identity.
    defaults = { account_id = "000000${"000000"}" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

variables {
  region      = "ap-southeast-2"
  environment = "dev"
  alert_email = "alerts@example.invalid"
  image_uri   = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}

run "shared_concurrency_supports_small_quotas" {
  command = plan
  assert {
    condition     = var.reserved_concurrent_executions == -1
    error_message = "The starter must not require a reservation on a new project's small concurrency quota."
  }
}
