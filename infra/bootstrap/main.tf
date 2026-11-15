terraform {
  required_version = "~> 1.13.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
  backend "s3" { use_lockfile = true }
}
variable "region" { type = string }
variable "state_bucket" { type = string }
variable "repository" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.repository))
    error_message = "Use owner/repository."
  }
}
variable "alert_email" {
  type      = string
  sensitive = true
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "aws-cloud-deploy", Environment = "shared", Owner = "Nazmul Hassan", ManagedBy = "Terraform" } }
}
data "aws_caller_identity" "current" {}
locals {
  name    = "aws-cloud-deploy"
  account = data.aws_caller_identity.current.account_id
}
resource "aws_dynamodb_table" "lock" {
  name         = "${local.name}-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
}
module "ecr" {
  source = "../modules/ecr"
  name   = local.name
}
module "runtime" {
  for_each  = toset(["dev", "prod"])
  source    = "../modules/iam"
  name      = "${local.name}-${each.key}"
  table_arn = "arn:aws:dynamodb:${var.region}:${local.account}:table/${local.name}-${each.key}-items"
  log_arn   = "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.name}-${each.key}"
}
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
data "aws_iam_policy_document" "trust" {
  for_each = toset(["plan", "dev", "prod"])
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [each.key == "plan" ? "repo:${var.repository}:pull_request" : "repo:${var.repository}:environment:${each.key}"]
    }
  }
}
resource "aws_iam_role" "github" {
  for_each             = data.aws_iam_policy_document.trust
  name                 = "${local.name}-${each.key}-delivery"
  assume_role_policy   = each.value.json
  max_session_duration = 3600
}
data "aws_iam_policy_document" "state" {
  for_each = toset(["plan", "dev", "prod"])
  statement {
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.state_bucket}"]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = each.key == "plan" ? ["dev/*", "env:/"] : ["${each.key}/*", "env:/"]
    }
  }
  statement {
    actions   = each.key == "plan" ? ["s3:GetObject"] : ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::${var.state_bucket}/${each.key == "plan" ? "dev" : each.key}/terraform.tfstate"]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.state_bucket}/${each.key == "plan" ? "dev" : each.key}/terraform.tfstate.tflock"]
  }
  statement {
    actions   = ["dynamodb:DescribeTable"]
    resources = [aws_dynamodb_table.lock.arn]
  }
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.lock.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["${var.state_bucket}/${each.key == "plan" ? "dev" : each.key}/terraform.tfstate*"]
    }
  }
}
resource "aws_iam_role_policy" "state" {
  for_each = data.aws_iam_policy_document.state
  name     = "remote-state"
  role     = aws_iam_role.github[each.key].id
  policy   = each.value.json
}
data "aws_iam_policy_document" "read" {
  for_each = { plan = "dev", dev = "dev", prod = "prod" }
  statement {
    actions = ["logs:DescribeLogGroups", "cloudwatch:DescribeAlarms", "sns:GetSubscriptionAttributes"]
    # Provider discovery calls need resource wildcard access.
    resources = ["*"]
  }
  statement {
    actions = ["lambda:GetFunction", "lambda:GetFunctionConfiguration", "lambda:GetPolicy", "lambda:ListTags",
    "lambda:GetFunctionConcurrency", "lambda:GetRuntimeManagementConfig", "lambda:GetFunctionCodeSigningConfig", "lambda:ListVersionsByFunction"]
    resources = ["arn:aws:lambda:${var.region}:${local.account}:function:${local.name}-${each.value}"]
  }
  statement {
    actions   = ["dynamodb:DescribeTable", "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeTimeToLive", "dynamodb:ListTagsOfResource"]
    resources = ["arn:aws:dynamodb:${var.region}:${local.account}:table/${local.name}-${each.value}-items"]
  }
  statement {
    actions = ["logs:ListTagsForResource", "logs:ListTagsLogGroup"]
    resources = ["arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.name}-${each.value}*",
    "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/apigateway/${local.name}-${each.value}*"]
  }
  statement {
    actions = ["cloudwatch:GetDashboard", "cloudwatch:ListTagsForResource"]
    resources = ["arn:aws:cloudwatch::${local.account}:dashboard/${local.name}-${each.value}",
    "arn:aws:cloudwatch:${var.region}:${local.account}:alarm:${local.name}-${each.value}-*"]
  }
  statement {
    actions = ["sns:GetTopicAttributes", "sns:ListTagsForResource", "sns:ListSubscriptionsByTopic"]
    resources = ["arn:aws:sns:${var.region}:${local.account}:${local.name}-${each.value}-alarms",
    "arn:aws:sns:${var.region}:${local.account}:${local.name}-${each.value}-alarms:*"]
  }
  statement {
    actions   = ["apigateway:GET"]
    resources = ["arn:aws:apigateway:${var.region}::/apis", "arn:aws:apigateway:${var.region}::/apis/*", "arn:aws:apigateway:${var.region}::/tags/*"]
  }
}
resource "aws_iam_role_policy" "read" {
  for_each = aws_iam_role.github
  name     = "terraform-read"
  role     = each.value.id
  policy   = data.aws_iam_policy_document.read[each.key].json
}
data "aws_iam_policy_document" "deploy" {
  for_each = toset(["dev", "prod"])
  statement {
    actions = ["lambda:CreateFunction", "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration", "lambda:DeleteFunction",
    "lambda:AddPermission", "lambda:RemovePermission", "lambda:PutFunctionConcurrency", "lambda:DeleteFunctionConcurrency", "lambda:TagResource", "lambda:UntagResource"]
    resources = ["arn:aws:lambda:${var.region}:${local.account}:function:${local.name}-${each.key}"]
  }
  statement {
    actions   = ["iam:PassRole"]
    resources = [module.runtime[each.key].arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }
  statement {
    actions = ["dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:UpdateTable", "dynamodb:UpdateTimeToLive",
    "dynamodb:UpdateContinuousBackups", "dynamodb:TagResource", "dynamodb:UntagResource"]
    resources = ["arn:aws:dynamodb:${var.region}:${local.account}:table/${local.name}-${each.key}-items"]
  }
  statement {
    actions = ["logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy", "logs:TagResource", "logs:UntagResource"]
    resources = ["arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.name}-${each.key}*",
    "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/apigateway/${local.name}-${each.key}*"]
  }
  statement {
    actions   = ["cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:TagResource", "cloudwatch:UntagResource"]
    resources = ["arn:aws:cloudwatch:${var.region}:${local.account}:alarm:${local.name}-${each.key}-*"]
  }
  statement {
    actions   = ["cloudwatch:PutDashboard", "cloudwatch:DeleteDashboards"]
    resources = ["arn:aws:cloudwatch::${local.account}:dashboard/${local.name}-${each.key}"]
  }
  statement {
    actions   = ["sns:CreateTopic", "sns:DeleteTopic", "sns:SetTopicAttributes", "sns:Subscribe", "sns:TagResource", "sns:UntagResource"]
    resources = ["arn:aws:sns:${var.region}:${local.account}:${local.name}-${each.key}-alarms", "arn:aws:sns:${var.region}:${local.account}:${local.name}-${each.key}-alarms:*"]
  }
  statement {
    # SNS subscription APIs do not support resource-level IAM scoping.
    actions   = ["sns:Unsubscribe"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.region]
    }
  }
  statement {
    actions   = ["apigateway:POST", "apigateway:PATCH", "apigateway:DELETE", "apigateway:PUT"]
    resources = ["arn:aws:apigateway:${var.region}::/apis", "arn:aws:apigateway:${var.region}::/apis/*", "arn:aws:apigateway:${var.region}::/tags/*"]
    # HTTP API IDs are assigned by AWS. See docs/security.md for this boundary.
  }
  statement {
    actions   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability", "ecr:DescribeImages", "ecr:GetRepositoryPolicy"]
    resources = [module.ecr.arn]
  }
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
}
resource "aws_iam_role_policy" "deploy" {
  for_each = data.aws_iam_policy_document.deploy
  name     = "deploy"
  role     = aws_iam_role.github[each.key].id
  policy   = each.value.json
}
data "aws_iam_policy_document" "push" {
  statement {
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:DescribeImages"]
    resources = [module.ecr.arn]
  }
}
resource "aws_iam_role_policy" "push" {
  name   = "push-image"
  role   = aws_iam_role.github["dev"].id
  policy = data.aws_iam_policy_document.push.json
}
resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  # Account-wide guard includes untaggable request charges and retained state.
  dynamic "notification" {
    for_each = [1, 5]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }
}
output "ecr_url" {
  value     = module.ecr.url
  sensitive = true
}
output "delivery_roles" {
  value     = { for key, role in aws_iam_role.github : key => role.arn }
  sensitive = true
}
