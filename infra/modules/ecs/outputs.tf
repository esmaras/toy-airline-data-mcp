output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "sharing_server_service_name" {
  value = aws_ecs_service.sharing_server.name
}

output "mcp_server_service_name" {
  value = aws_ecs_service.mcp_server.name
}

output "web_app_service_name" {
  value = aws_ecs_service.web_app.name
}
