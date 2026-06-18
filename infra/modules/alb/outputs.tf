output "dns_name" {
  value = aws_lb.main.dns_name
}

output "mcp_target_group_arn" {
  value = aws_lb_target_group.mcp.arn
}

output "web_target_group_arn" {
  value = aws_lb_target_group.web_app.arn
}
