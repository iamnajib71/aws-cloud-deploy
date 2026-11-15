variable "name" { type = string }
resource "aws_ecr_repository" "app" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}
data "aws_iam_policy_document" "pull" {
  statement {
    actions = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:lambda:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:function:${var.name}-*"]
    }
  }
}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
resource "aws_ecr_repository_policy" "pull" {
  repository = aws_ecr_repository.app.name
  policy     = data.aws_iam_policy_document.pull.json
}
output "url" { value = aws_ecr_repository.app.repository_url }
output "arn" { value = aws_ecr_repository.app.arn }
