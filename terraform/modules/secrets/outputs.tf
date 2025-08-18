output "secret_arns" {
  description = "ARNs of all secrets"
  value = [
    aws_secretsmanager_secret.anthropic_api_key.arn,
    aws_secretsmanager_secret.langsmith_api_key.arn,
    aws_secretsmanager_secret.chicago_data_token.arn
  ]
}

output "secret_names" {
  description = "Names of all secrets"
  value = [
    aws_secretsmanager_secret.anthropic_api_key.name,
    aws_secretsmanager_secret.langsmith_api_key.name,
    aws_secretsmanager_secret.chicago_data_token.name
  ]
}

output "secrets_access_policy_arn" {
  description = "ARN of the IAM policy for accessing secrets"
  value       = aws_iam_policy.secrets_access.arn
}