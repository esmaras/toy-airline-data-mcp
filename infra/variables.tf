variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, prod)"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project name used in resource naming"
  type        = string
  default     = "clearpath"
}

variable "sharing_server_image" {
  description = "Full ECR image URI for the sharing server (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/clearpath/sharing-server:latest)"
  type        = string
}

variable "mcp_server_image" {
  description = "Full ECR image URI for the MCP server"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS on the ALB. Leave empty to use HTTP only (dev shortcut)."
  type        = string
  default     = ""
}

variable "web_app_image" {
  description = "Full ECR image URI for the Next.js web app"
  type        = string
  default     = ""
}

variable "anthropic_api_key_ssm_arn" {
  description = "ARN of the SSM SecureString parameter holding the Anthropic API key (e.g. arn:aws:ssm:us-east-1:ACCOUNT:parameter/clearpath/dev/anthropic_api_key)"
  type        = string
}
