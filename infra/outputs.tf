output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer — connect Claude Desktop MCP to this"
  value       = module.alb.dns_name
}

output "mcp_server_url" {
  description = "MCP SSE endpoint URL"
  value       = "http://${module.alb.dns_name}/sse"
}

output "data_lake_bucket" {
  description = "S3 data lake bucket name"
  value       = module.s3.bucket_name
}

output "ecr_sharing_server_url" {
  description = "ECR repository URL for the sharing server image"
  value       = module.ecr.sharing_server_url
}

output "ecr_mcp_server_url" {
  description = "ECR repository URL for the MCP server image"
  value       = module.ecr.mcp_server_url
}

output "ecr_web_app_url" {
  description = "ECR repository URL for the web app image"
  value       = module.ecr.web_app_url
}

output "web_app_url" {
  description = "ClearPath web chat UI URL"
  value       = "http://${module.alb.dns_name}/"
}
