resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "sharing_server" {
  name              = "/ecs/${var.name_prefix}-sharing-server"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "mcp_server" {
  name              = "/ecs/${var.name_prefix}-mcp-server"
  retention_in_days = 14
}

# Cloud Map namespace for internal service discovery
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.name_prefix}.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "sharing_server" {
  name = "sharing-server"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# Sharing server task definition
resource "aws_ecs_task_definition" "sharing_server" {
  family                   = "${var.name_prefix}-sharing-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.sharing_server_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "sharing-server"
      image = var.sharing_server_image

      portMappings = [
        { containerPort = 8080, protocol = "tcp" }
      ]

      environment = [
        { name = "DELTA_TABLES_S3_PREFIX", value = "s3://${var.data_lake_bucket}/delta/southwest_airline" },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sharing_server.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import httpx; httpx.get('http://localhost:8080/shares', timeout=3)\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }

      essential = true
    }
  ])
}

# MCP server task definition
resource "aws_ecs_task_definition" "mcp_server" {
  family                   = "${var.name_prefix}-mcp-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.mcp_server_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "mcp-server"
      image = var.mcp_server_image

      portMappings = [
        { containerPort = 8081, protocol = "tcp" }
      ]

      environment = [
        { name = "SHARING_SERVER_URL", value = "http://sharing-server.${aws_service_discovery_private_dns_namespace.main.name}:8080" },
        { name = "PYTHONPATH", value = "/app" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.mcp_server.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])
}

# Sharing server ECS service
resource "aws_ecs_service" "sharing_server" {
  name            = "${var.name_prefix}-sharing-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.sharing_server.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.sharing_server_sg_id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.sharing_server.arn
  }

  lifecycle {
    # Allow image updates without Terraform treating it as drift
    ignore_changes = [task_definition]
  }
}

# MCP server ECS service
resource "aws_ecs_service" "mcp_server" {
  name            = "${var.name_prefix}-mcp-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp_server.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.mcp_server_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.mcp_target_group_arn
    container_name   = "mcp-server"
    container_port   = 8081
  }

  depends_on = [aws_ecs_service.sharing_server]

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# Web app ECS service
resource "aws_cloudwatch_log_group" "web_app" {
  name              = "/ecs/${var.name_prefix}-web-app"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "web_app" {
  family                   = "${var.name_prefix}-web-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.web_app_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "web-app"
      image = var.web_app_image

      portMappings = [
        { containerPort = 3000, protocol = "tcp" }
      ]

      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "SHARING_SERVER_URL",
          value = "http://sharing-server.${aws_service_discovery_private_dns_namespace.main.name}:8080" },
      ]

      secrets = [
        { name = "ANTHROPIC_API_KEY", valueFrom = var.anthropic_api_key_ssm_arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.web_app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget -q -O- http://localhost:3000/api/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }

      essential = true
    }
  ])
}

resource "aws_ecs_service" "web_app" {
  name            = "${var.name_prefix}-web-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web_app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.web_app_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.web_target_group_arn
    container_name   = "web-app"
    container_port   = 3000
  }

  depends_on = [aws_ecs_service.sharing_server]

  lifecycle {
    ignore_changes = [task_definition]
  }
}
