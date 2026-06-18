variable "name_prefix" {
  type = string
}

variable "data_lake_bucket_arn" {
  type = string
}

variable "anthropic_api_key_ssm_arn" {
  type        = string
  description = "ARN of the SSM parameter holding the Anthropic API key"
}
