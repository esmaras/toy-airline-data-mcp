data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Task execution role — used by ECS agent to pull images and write logs
resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Sharing server task role — needs S3 read access to generate presigned URLs
resource "aws_iam_role" "sharing_server_task" {
  name               = "${var.name_prefix}-sharing-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "sharing_s3_read" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      var.data_lake_bucket_arn,
      "${var.data_lake_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "sharing_s3_read" {
  name   = "${var.name_prefix}-sharing-s3-read"
  policy = data.aws_iam_policy_document.sharing_s3_read.json
}

resource "aws_iam_role_policy_attachment" "sharing_s3_read" {
  role       = aws_iam_role.sharing_server_task.name
  policy_arn = aws_iam_policy.sharing_s3_read.arn
}

# MCP server task role — no S3 access needed (only talks to sharing server over HTTP)
resource "aws_iam_role" "mcp_server_task" {
  name               = "${var.name_prefix}-mcp-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

# Web app task role — no S3 or SSM access needed (talks to sharing server + Anthropic API)
resource "aws_iam_role" "web_app_task" {
  name               = "${var.name_prefix}-web-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

# Allow the task execution role to fetch the Anthropic API key from SSM
data "aws_iam_policy_document" "execution_ssm_secrets" {
  statement {
    actions   = ["ssm:GetParameters", "ssm:GetParameter"]
    resources = [var.anthropic_api_key_ssm_arn]
  }
}

resource "aws_iam_policy" "execution_ssm_secrets" {
  name   = "${var.name_prefix}-execution-ssm-secrets"
  policy = data.aws_iam_policy_document.execution_ssm_secrets.json
}

resource "aws_iam_role_policy_attachment" "execution_ssm_secrets" {
  role       = aws_iam_role.task_execution.name
  policy_arn = aws_iam_policy.execution_ssm_secrets.arn
}
