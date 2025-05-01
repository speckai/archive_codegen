# variables.tf

variable "subscription_id" {
  description = "Azure Subscription ID"
}

variable "client_id" {
  description = "Azure Client ID (Service Principal)"
}

variable "client_secret" {
  description = "Azure Client Secret (Service Principal Password)"
}

variable "tenant_id" {
  description = "Azure Tenant ID"
}

variable "github_username" {
  description = "GitHub username or organization"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "docker_username" {
  description = "Docker registry username (GitHub username)"
  type        = string
}

variable "docker_password" {
  description = "Docker registry password (GitHub Personal Access Token)"
  type        = string
  sensitive   = true
}
