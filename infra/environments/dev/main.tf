terraform {
  required_version = ">= 1.6.0"
}

module "clearpath_dev" {
  source = "../../"

  environment = "dev"
  aws_region  = "us-east-1"

  # Set these after running `terraform apply` on ECR module first,
  # then building and pushing images (see Makefile targets)
  sharing_server_image = var.sharing_server_image
  mcp_server_image     = var.mcp_server_image

  # Leave empty to use HTTP only (no ACM certificate required for dev)
  certificate_arn = ""
}

variable "sharing_server_image" {
  type = string
}

variable "mcp_server_image" {
  type = string
}

output "mcp_server_url" {
  value = module.clearpath_dev.mcp_server_url
}

output "data_lake_bucket" {
  value = module.clearpath_dev.data_lake_bucket
}
