# Read and parse the .env file for environment variables
locals {
  github_consumer_env_file_content = file("${path.module}/.env.git-consumer")
  github_consumer_env_lines        = [
    for line in split("\n", local.github_consumer_env_file_content) : trim(line, " ")
    if length(trim(line, " ")) > 0 && !startswith(trim(line, " "), "#")
  ]
  github_consumer_env_vars = {
    for line in local.github_consumer_env_lines :
    regex("^(.*?)=(.*)$", line)[0] => trim(regex("^(.*?)=(.*)$", line)[1], "\"")
    if can(regex("^([^=]+)=(.*)$", line))
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "github_consumer" {
  name = "github-consumer"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "github_consumer" {
  family                   = "github-consumer"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = "256"
  memory                  = "512"
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "github-consumer"
      image     = "${aws_ecr_repository.github_consumer.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]

      environment = [
        for key, value in local.github_consumer_env_vars : {
          name  = key
          value = value
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/github-consumer"
          "awslogs-region"        = "us-west-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ECR Repository
resource "aws_ecr_repository" "github_consumer" {
  name = "github-consumer"
}

# IAM Roles
resource "aws_iam_role" "ecs_task_execution" {
  name = "github-consumer-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Add ECR pull permissions
resource "aws_iam_role_policy" "ecs_task_execution_ecr" {
  name = "github-consumer-ecr-pull"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "github-consumer-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# VPC Configuration
resource "aws_security_group" "github_consumer" {
  name        = "github-consumer"
  description = "Security group for GitHub Consumer ECS service"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "alb" {
  name        = "github-consumer-alb"
  description = "Security group for GitHub Consumer ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Application Load Balancer
resource "aws_lb" "github_consumer" {
  name               = "github-consumer"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "github-consumer.speck.sh"
  }
}

resource "aws_lb_target_group" "github_consumer" {
  name        = "github-consumer"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval            = 60
    matcher            = "200,404"  # Allow 404 during startup
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener" "github_consumer" {
  load_balancer_arn = aws_lb.github_consumer.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.github_consumer.arn
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ECS Service
resource "aws_ecs_service" "github_consumer" {
  name            = "github-consumer"
  cluster         = aws_ecs_cluster.github_consumer.id
  task_definition = aws_ecs_task_definition.github_consumer.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.github_consumer.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.github_consumer.arn
    container_name   = "github-consumer"
    container_port   = 80
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_lb_target_group.github_consumer, aws_lb_listener.github_consumer]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "github_consumer" {
  name              = "/ecs/github-consumer"
  retention_in_days = 30
}

# Outputs
output "github_consumer_url" {
  value = "http://github-consumer.speck.sh"
}

output "github_consumer_dns_record" {
  value = {
    type  = "CNAME"
    name  = "github-consumer"
    value = aws_lb.github_consumer.dns_name
  }
  description = "DNS record to be added to Vercel for github-consumer.speck.sh"
}