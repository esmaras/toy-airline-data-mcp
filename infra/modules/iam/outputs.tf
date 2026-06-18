output "task_execution_role_arn" {
  value = aws_iam_role.task_execution.arn
}

output "sharing_server_task_role_arn" {
  value = aws_iam_role.sharing_server_task.arn
}

output "mcp_server_task_role_arn" {
  value = aws_iam_role.mcp_server_task.arn
}

output "web_app_task_role_arn" {
  value = aws_iam_role.web_app_task.arn
}
