# main.tf

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
}

# Read and parse the .env files for environment variables
locals {
  # Parse .env.manager file
  manager_env_file_content = file("${path.module}/.env.manager")
  manager_env_lines = [
    for line in split("\n", local.manager_env_file_content) : trim(line, " ")
    if length(trim(line, " ")) > 0 && !startswith(trim(line, " "), "#")
  ]
  manager_env_vars = {
    for line in local.manager_env_lines :
    regex("^(.*?)=(.*)$", line)[0] => trim(regex("^(.*?)=(.*)$", line)[1], "\"")
    if can(regex("^([^=]+)=(.*)$", line))
  }
  
  # Parse .env.container file
  container_env_file_content = file("${path.module}/.env.container")
  container_env_lines = [
    for line in split("\n", local.container_env_file_content) : trim(line, " ")
    if length(trim(line, " ")) > 0 && !startswith(trim(line, " "), "#")
  ]
  container_env_vars = {
    for line in local.container_env_lines :
    regex("^(.*?)=(.*)$", line)[0] => trim(regex("^(.*?)=(.*)$", line)[1], "\"")
    if can(regex("^([^=]+)=(.*)$", line))
  }
}

# VPC Configuration
resource "aws_vpc" "sandbox" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "sandbox-vpc"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.sandbox.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "sandbox-public-${count.index + 1}"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.sandbox.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "sandbox-private-${count.index + 1}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.sandbox.id

  tags = {
    Name = "sandbox-igw"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "sandbox-nat-${count.index + 1}"
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count = 2
  domain = "vpc"

  tags = {
    Name = "sandbox-eip-${count.index + 1}"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.sandbox.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "sandbox-public-rt"
  }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.sandbox.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "sandbox-private-rt-${count.index + 1}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ECS Cluster
resource "aws_ecs_cluster" "sandbox" {
  name = "sandbox-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Associate capacity providers with the cluster
resource "aws_ecs_cluster_capacity_providers" "sandbox" {
  cluster_name = aws_ecs_cluster.sandbox.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "sandbox-ecs-task-execution-role"

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

# Add SSM permissions for ECS Exec
resource "aws_iam_role_policy" "ecs_task_execution_role_policy" {
  name = "sandbox-ecs-task-execution-role-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
          "ecs:ListTasks",
          "ecs:DescribeTasks",
          "ecs:ListClusters",
          "ecs:TagResource",
          "ecs:ExecuteCommand",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTaskDefinitions",
          "ecs:ListServices",
          "ecs:DescribeServices"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "sandbox-ecs-task-role"

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

# Policy for ECS Task Role
resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "sandbox-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks",
          "ecs:ListClusters",
          "ecs:ListTasks",
          "ecs:TagResource",
          "ecs:ExecuteCommand",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTaskDefinitions",
          "ecs:ListServices",
          "ecs:DescribeServices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
        aws_iam_role.ecs_task_execution_role.arn,
        aws_iam_role.ecs_task_role.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeInstances",
          "ec2:CreateNetworkInterface",
          "ec2:AttachNetworkInterface",
          "ec2:DeleteNetworkInterface",
          "ec2:DetachNetworkInterface",
          "ec2:ModifyNetworkInterfaceAttribute",
          "ec2:ResetNetworkInterfaceAttribute"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# EFS for Shared Package Cache
resource "aws_efs_file_system" "package_cache" {
  creation_token = "sandbox-package-cache"
  performance_mode = "generalPurpose"
  throughput_mode = "bursting"
  encrypted = true
  
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  
  tags = {
    Name = "sandbox-package-cache"
  }
}

# EFS Mount Targets
resource "aws_efs_mount_target" "package_cache" {
  count = length(aws_subnet.public)
  file_system_id = aws_efs_file_system.package_cache.id
  subnet_id      = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# Security Group for EFS
resource "aws_security_group" "efs" {
  name        = "sandbox-efs"
  description = "Allow EFS access from ECS tasks"
  vpc_id      = aws_vpc.sandbox.id

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description = "NFS access from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sandbox-efs"
  }
}

# Add EFS access to ECS Task Role
resource "aws_iam_role_policy" "ecs_task_role_efs_policy" {
  name = "sandbox-ecs-task-efs-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.package_cache.arn
      }
    ]
  })
}

# Manager Service Task Definition
resource "aws_ecs_task_definition" "manager" {
  family                   = "sandbox-manager"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 4096
  memory                  = 8192
  execution_role_arn      = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn          = aws_iam_role.ecs_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture       = "X86_64"
  }

  # EFS Volume Configuration
  volume {
    name = "package-cache"
    
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.package_cache.id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name  = "manager"
      image = "${var.manager_ecr_repository_url}:latest"
      
      environment = concat([
        {
          name  = "CLUSTER_NAME"
          value = aws_ecs_cluster.sandbox.name
        },
        {
          name  = "SUBNET_IDS"
          value = join(",", aws_subnet.public[*].id)
        },
        {
          name  = "SECURITY_GROUP_ID"
          value = aws_security_group.ecs_tasks.id
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        },
        {
          name  = "IS_LOCAL"
          value = "false"
        },
        {
          name  = "ALB_DNS"
          value = aws_lb.sandbox.dns_name
        },
        {
          name  = "EFS_FILESYSTEM_ID"
          value = aws_efs_file_system.package_cache.id
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/efs"
        }
      ],
      # Add environment variables from .env.manager file
      [
        for name, value in local.manager_env_vars : {
          name  = name
          value = value
        }
      ])

      mountPoints = [
        {
          sourceVolume  = "package-cache"
          containerPath = "/efs"
          readOnly      = false
        }
      ]

      portMappings = [
        {
          containerPort = 8000
          hostPort     = 8000
          protocol     = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sandbox.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "manager"
        }
      }

      essential = true

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

# Container Service Task Definition
resource "aws_ecs_task_definition" "container" {
  family                   = "sandbox-container"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 4096
  memory                  = 8192
  execution_role_arn      = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn          = aws_iam_role.ecs_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture       = "X86_64"
  }

  # EFS Volume Configuration
  volume {
    name = "package-cache"
    
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.package_cache.id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name  = "sandbox-container"
      image = "${var.container_ecr_repository_url}:latest"
      
      environment = concat([
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        },
        {
          name  = "IS_LOCAL"
          value = "false"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/efs"
        },
        {
          name  = "PNPM_STORE_DIR"
          value = "/efs/pnpm-store"
        },
        {
          name  = "NPM_CACHE_DIR"
          value = "/efs/npm-cache"
        },
        {
          name  = "YARN_CACHE_FOLDER"
          value = "/efs/yarn-cache"
        },
        {
          name  = "BUN_CACHE_DIR"
          value = "/efs/bun-cache"
        }
      ],
      # Add environment variables from .env.container file
      [
        for name, value in local.container_env_vars : {
          name  = name
          value = value
        }
      ])

      mountPoints = [
        {
          sourceVolume  = "package-cache"
          containerPath = "/efs"
          readOnly      = false
        }
      ]

      portMappings = [
        {
          containerPort = 8000
          hostPort     = 8000
          protocol     = "tcp"
        },
        {
          containerPort = 8001
          hostPort     = 8001
          protocol     = "tcp"
        },
        {
          containerPort = 3000
          hostPort     = 3000
          protocol     = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sandbox.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "container"
        }
      }

      essential = true

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 60
        timeout     = 30
        retries     = 10
        startPeriod = 120
      }
    }
  ])
}

# Manager Service
resource "aws_ecs_service" "manager" {
  name            = "sandbox-manager"
  cluster         = aws_ecs_cluster.sandbox.id
  task_definition = aws_ecs_task_definition.manager.arn
  desired_count   = 1  # Single instance
  launch_type     = "FARGATE"
  force_new_deployment = true
  enable_execute_command = true
  platform_version      = "LATEST"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.manager.arn
    container_name   = "manager"
    container_port   = 8000
  }
}

# Container Service
resource "aws_ecs_service" "container" {
  name            = "sandbox-container"
  cluster         = aws_ecs_cluster.sandbox.id
  task_definition = aws_ecs_task_definition.container.arn
  desired_count   = 1  # Start with 1 warm container
  launch_type     = "FARGATE"
  force_new_deployment = true
  enable_execute_command = true
  platform_version      = "LATEST"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.container.arn
    container_name   = "sandbox-container"
    container_port   = 8000
  }

  # Add deployment controller
  deployment_controller {
    type = "ECS"
  }

  # Add service connect configuration
  service_connect_configuration {
    enabled = true
    namespace = "sandbox.local"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "sandbox" {
  name              = "/ecs/sandbox"
  retention_in_days = 30
}

# Security Groups
resource "aws_security_group" "ecs_tasks" {
  name        = "sandbox-ecs-tasks"
  description = "Allow inbound traffic for sandbox containers"
  vpc_id      = aws_vpc.sandbox.id

  # Allow HTTP
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  # Allow WebSocket
  ingress {
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "WebSocket access"
  }

  # Allow React development server
  ingress {
    from_port   = 2000
    to_port     = 4999
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "React development server"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sandbox-ecs-tasks"
  }
}

# Application Load Balancer
resource "aws_lb" "sandbox" {
  name               = "sandbox-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id

  tags = {
    Name = "sandbox.speck.sh"
  }
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "sandbox-alb"
  description = "Security group for sandbox ALB"
  vpc_id      = aws_vpc.sandbox.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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

# Target Groups
resource "aws_lb_target_group" "manager" {
  name        = "sandbox-manager"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.sandbox.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 10
    interval           = 30
    matcher            = "200"
  }
}

resource "aws_lb_target_group" "container" {
  name        = "sandbox-container"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.sandbox.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval           = 60
    matcher            = "200"
  }
}

# ACM Certificate
data "aws_acm_certificate" "sandbox" {
  domain      = "sandbox.speck.sh"
  statuses    = ["PENDING_VALIDATION", "ISSUED"]
  most_recent = true
}

# DNS Validation record
resource "aws_acm_certificate_validation" "sandbox" {
  certificate_arn = data.aws_acm_certificate.sandbox.arn
  timeouts {
    create = "60m"
  }
}

# ALB Listener Rules
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.sandbox.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
      host        = "#{host}"
      path        = "/#{path}"
      query       = "#{query}"
    }
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.sandbox.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = data.aws_acm_certificate.sandbox.arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

# HTTPS Listener Rules
resource "aws_lb_listener_rule" "manager_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.manager.arn
  }

  condition {
    host_header {
      values = ["sandbox.speck.sh"]
    }
  }
}

resource "aws_lb_listener_rule" "container_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.container.arn
  }

  condition {
    host_header {
      values = ["*.${aws_lb.sandbox.dns_name}"]
    }
  }
}

# Service Discovery
resource "aws_service_discovery_private_dns_namespace" "sandbox" {
  name = "sandbox.local"
  vpc  = aws_vpc.sandbox.id
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Outputs
output "manager_url" {
  value = "https://${aws_lb.sandbox.dns_name}"
}

output "manager_service_name" {
  description = "The name of the ECS service running the manager"
  value       = aws_ecs_service.manager.name
}

output "manager_task_definition" {
  description = "The task definition ARN of the manager"
  value       = aws_ecs_task_definition.manager.arn
}

output "manager_target_group" {
  description = "The ARN of the target group for the manager"
  value       = aws_lb_target_group.manager.arn
}

output "private_subnets" {
  value = aws_subnet.public[*].id
}

output "security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "cluster_name" {
  value = aws_ecs_cluster.sandbox.name
}

output "efs_filesystem_id" {
  description = "The ID of the EFS filesystem for package caching"
  value       = aws_efs_file_system.package_cache.id
}

output "efs_arn" {
  description = "The ARN of the EFS filesystem"
  value       = aws_efs_file_system.package_cache.arn
}
