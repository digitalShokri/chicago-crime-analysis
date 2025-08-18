# Secrets Manager Module - Secure API Key Storage

# Anthropic API Key
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "${var.name_prefix}/anthropic-api-key"
  description = "Anthropic API key for Claude LLM"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-anthropic-api-key"
  })
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  count = var.secrets.anthropic_api_key != "" ? 1 : 0
  
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.secrets.anthropic_api_key
}

# LangSmith API Key
resource "aws_secretsmanager_secret" "langsmith_api_key" {
  name        = "${var.name_prefix}/langsmith-api-key"
  description = "LangSmith API key for LLM observability"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-langsmith-api-key"
  })
}

resource "aws_secretsmanager_secret_version" "langsmith_api_key" {
  count = var.secrets.langsmith_api_key != "" ? 1 : 0
  
  secret_id     = aws_secretsmanager_secret.langsmith_api_key.id
  secret_string = var.secrets.langsmith_api_key
}

# Chicago Data Portal Token
resource "aws_secretsmanager_secret" "chicago_data_token" {
  name        = "${var.name_prefix}/chicago-data-token"
  description = "Chicago Data Portal API token"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-chicago-data-token"
  })
}

resource "aws_secretsmanager_secret_version" "chicago_data_token" {
  count = var.secrets.chicago_data_token != "" ? 1 : 0
  
  secret_id     = aws_secretsmanager_secret.chicago_data_token.id
  secret_string = var.secrets.chicago_data_token
}

# IAM Policy for ECS tasks to access secrets
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.name_prefix}-secrets-access"
  description = "Policy for ECS tasks to access secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.anthropic_api_key.arn,
          aws_secretsmanager_secret.langsmith_api_key.arn,
          aws_secretsmanager_secret.chicago_data_token.arn
        ]
      }
    ]
  })

  tags = var.tags
}