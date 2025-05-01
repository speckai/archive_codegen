# variables.tf

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-1"
}

variable "container_ecr_repository_url" {
  description = "URL of the ECR repository containing the sandbox container image"
  type        = string
}

variable "manager_ecr_repository_url" {
  description = "URL of the ECR repository containing the sandbox manager image"
  type        = string
}
