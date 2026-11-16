terraform {
  required_version = "~> 1.13.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
  backend "s3" {
    use_lockfile = true
  }
}
variable "region" { type = string }
variable "reserved_concurrent_executions" {
  type    = number
  default = -1
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Choose dev or prod."
  }
}
variable "image_uri" {
  type      = string
  sensitive = true
  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.image_uri))
    error_message = "Deploy an immutable ECR digest."
  }
}
variable "alert_email" {
  type      = string
  sensitive = true
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "aws-cloud-deploy", Environment = var.environment, Owner = "Nazmul Hassan", ManagedBy = "Terraform" } }
}
data "aws_caller_identity" "current" {}
locals { name = "aws-cloud-deploy-${var.environment}" }
module "app" {
  source                         = "../modules/app"
  name                           = local.name
  image_uri                      = var.image_uri
  runtime_role_arn               = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.name}-runtime"
  reserved_concurrent_executions = var.reserved_concurrent_executions
}
module "observability" {
  source = "../modules/observability"
  name   = local.name
  api_id = module.app.api_id
  email  = var.alert_email
}
output "endpoint" { value = module.app.endpoint }
output "image_uri" {
  value     = module.app.image_uri
  sensitive = true
}
