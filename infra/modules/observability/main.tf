variable "name" { type = string }
variable "api_id" { type = string }
variable "email" {
  type      = string
  sensitive = true
}
data "aws_region" "current" {}
# Non-sensitive alarm notifications only; see docs/security.md, exception SNS-01.
#tfsec:ignore:aws-sns-enable-topic-encryption
resource "aws_sns_topic" "alarms" {
  name = "${var.name}-alarms"
}
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.email
}
data "aws_iam_policy_document" "alarms" {
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alarms.arn]
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_metric_alarm.errors.arn, aws_cloudwatch_metric_alarm.latency.arn]
    }
  }
}
resource "aws_sns_topic_policy" "alarms" {
  arn    = aws_sns_topic.alarms.arn
  policy = data.aws_iam_policy_document.alarms.json
}
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.name}-5xx-rate"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  evaluation_periods  = 2
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  metric_query {
    id          = "rate"
    expression  = "IF(requests>0,100*errors/requests,0)"
    label       = "5xx percent"
    return_data = true
  }
  metric_query {
    id = "errors"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "5xx"
      period      = 60
      stat        = "Sum"
      dimensions  = { ApiId = var.api_id }
    }
  }
  metric_query {
    id = "requests"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { ApiId = var.api_id }
    }
  }
}
resource "aws_cloudwatch_metric_alarm" "latency" {
  alarm_name                            = "${var.name}-latency"
  comparison_operator                   = "GreaterThanThreshold"
  threshold                             = 1500
  evaluation_periods                    = 2
  namespace                             = "AWS/ApiGateway"
  metric_name                           = "Latency"
  extended_statistic                    = "p95"
  period                                = 60
  dimensions                            = { ApiId = var.api_id }
  treat_missing_data                    = "notBreaching"
  evaluate_low_sample_count_percentiles = "evaluate"
  alarm_actions                         = [aws_sns_topic.alarms.arn]
}
resource "aws_cloudwatch_dashboard" "api" {
  dashboard_name = var.name
  dashboard_body = jsonencode({ widgets = [for panel in [
    { title = "Requests", metric = "Count", stat = "Sum" },
    { title = "Server errors", metric = "5xx", stat = "Sum" },
    { title = "p95 latency (ms)", metric = "Latency", stat = "p95" }
    ] : { type = "metric", width = 8, height = 6, properties = {
      title   = panel.title, region = data.aws_region.current.region, period = 60,
      metrics = [["AWS/ApiGateway", panel.metric, "ApiId", var.api_id, { stat = panel.stat }]]
  } }] })
}
