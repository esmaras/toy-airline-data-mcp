output "sharing_server_url" {
  value = aws_ecr_repository.sharing_server.repository_url
}

output "mcp_server_url" {
  value = aws_ecr_repository.mcp_server.repository_url
}

output "web_app_url" {
  value = aws_ecr_repository.web_app.repository_url
}
