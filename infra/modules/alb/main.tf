resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.public_subnet_ids

  # Increased for SSE long-lived connections (default 60s drops SSE)
  idle_timeout = 3600

  tags = { Name = "${var.name_prefix}-alb" }
}

resource "aws_lb_target_group" "mcp" {
  name        = "${var.name_prefix}-mcp-tg"
  port        = 8081
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/sse"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    # SSE endpoint returns 200 on initial connect
    matcher = "200"
  }

  tags = { Name = "${var.name_prefix}-mcp-tg" }
}

resource "aws_lb_target_group" "web_app" {
  name        = "${var.name_prefix}-web-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.name_prefix}-web-tg" }
}

# HTTP listener — default action forwards to web app; listener rules handle MCP paths
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = var.certificate_arn != "" ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.certificate_arn == "" ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.web_app.arn
    }
  }
}

# Priority 10: MCP SSE paths go to MCP server
resource "aws_lb_listener_rule" "mcp_paths" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp.arn
  }

  condition {
    path_pattern {
      values = ["/sse", "/messages", "/messages/*"]
    }
  }
}

# HTTPS listener (only created when a certificate ARN is provided)
resource "aws_lb_listener" "https" {
  count             = var.certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp.arn
  }
}
