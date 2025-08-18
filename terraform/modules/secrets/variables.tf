variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "secrets" {
  description = "Map of secret values"
  type = object({
    anthropic_api_key  = string
    langsmith_api_key  = string
    chicago_data_token = string
  })
  sensitive = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}