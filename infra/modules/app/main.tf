variable "name" { type = string }
variable "image_uri" { type = string }
variable "runtime_role_arn" { type = string }
resource "aws_dynamodb_table" "items" {
  name         = "${var.name}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
}
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 3
}
resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/apigateway/${var.name}"
  retention_in_days = 3
}
resource "aws_lambda_function" "api" {
  function_name                  = var.name
  role                           = var.runtime_role_arn
  package_type                   = "Image"
  image_uri                      = var.image_uri
  architectures                  = ["x86_64"]
  memory_size                    = 128
  timeout                        = 10
  reserved_concurrent_executions = 2
  environment { variables = { TABLE_NAME = aws_dynamodb_table.items.name } }
  logging_config {
    log_format = "JSON"
  }
  tracing_config { mode = "PassThrough" }
  depends_on = [aws_cloudwatch_log_group.lambda]
}
resource "aws_apigatewayv2_api" "api" {
  name          = var.name
  protocol_type = "HTTP"
}
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 12000
}
resource "aws_apigatewayv2_route" "routes" {
  for_each  = toset(["GET /health", "GET /items", "POST /items", "GET /metrics"])
  api_id    = aws_apigatewayv2_api.api.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit   = 2
    throttling_rate_limit    = 1
    detailed_metrics_enabled = false
  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access.arn
    format = jsonencode({ requestId = "$context.requestId", status = "$context.status",
    route = "$context.routeKey", latency = "$context.responseLatency" })
  }
}
resource "aws_lambda_permission" "gateway" {
  statement_id  = "AllowHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
output "endpoint" { value = aws_apigatewayv2_stage.default.invoke_url }
output "api_id" { value = aws_apigatewayv2_api.api.id }
output "image_uri" {
  value     = aws_lambda_function.api.image_uri
  sensitive = true
}
