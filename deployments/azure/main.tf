# main.tf

# Step 1: Define the Azure provider
provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
}

# Step 2: Create a Resource Group
resource "azurerm_resource_group" "speck_rg" {
  name     = "speck-main-rg"
  location = "West US"
}

# Step 3: Create an App Service Plan
resource "azurerm_app_service_plan" "speck_asp" {
  name                = "speck-app-service-plan"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "PremiumV3"
    size = "P2v3"
  }
}

# Step 4: Read and parse the .env file for the environment variables
locals {
  api_env_file_content = file("${path.module}/.env.api")
  api_env_lines        = [
    for line in split("\n", local.api_env_file_content) : trim(line, " ")
    if length(trim(line, " ")) > 0 && !startswith(trim(line, " "), "#")
  ]
  api_env_vars = {
    for line in local.api_env_lines :
    regex("^(.*?)=(.*)$", line)[0] => trim(regex("^(.*?)=(.*)$", line)[1], "\"")
    if can(regex("^([^=]+)=(.*)$", line))
  }
}

# Step 5: Create an App Service Web App for Containers
resource "azurerm_app_service" "speck_api" {
  name                = "speck-api"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  app_service_plan_id = azurerm_app_service_plan.speck_asp.id

  site_config {
    linux_fx_version = "DOCKER|ghcr.io/${var.github_username}/speck-api:${var.image_tag}"
    always_on        = true
    health_check_path = "/health"
  }

  lifecycle {
    ignore_changes = [
      site_config[0].linux_fx_version
    ]
  }

  app_settings = merge({
    WEBSITES_PORT                   = "80"
    DOCKER_REGISTRY_SERVER_URL      = "https://ghcr.io"
    DOCKER_REGISTRY_SERVER_USERNAME = var.docker_username
    DOCKER_REGISTRY_SERVER_PASSWORD = var.docker_password
    REDIS_CONNECTION_STRING         = "rediss://:${azurerm_redis_cache.speck_redis.primary_access_key}@${azurerm_redis_cache.speck_redis.hostname}:6380"
    WORKER_ID                      = "$${WEBSITE_INSTANCE_ID}"
    APPINSIGHTS_INSTRUMENTATIONKEY  = azurerm_application_insights.speck_app_insights.instrumentation_key
  }, local.api_env_vars)
}

# Add custom domain binding for api.speck.sh
resource "azurerm_app_service_custom_hostname_binding" "speck_api_custom_domain" {
  hostname            = "api.speck.sh"
  app_service_name    = azurerm_app_service.speck_api.name
  resource_group_name = azurerm_resource_group.speck_rg.name

  depends_on = [
    azurerm_app_service.speck_api
  ]
}

# Add managed certificate for the custom domain
resource "azurerm_app_service_managed_certificate" "speck_api_cert" {
  custom_hostname_binding_id = azurerm_app_service_custom_hostname_binding.speck_api_custom_domain.id
}

# Bind the certificate to the custom domain
resource "azurerm_app_service_certificate_binding" "speck_api_cert_binding" {
  hostname_binding_id = azurerm_app_service_custom_hostname_binding.speck_api_custom_domain.id
  certificate_id      = azurerm_app_service_managed_certificate.speck_api_cert.id
  ssl_state          = "SniEnabled"
}

# Step 6: Create a Cosmos DB Account with MongoDB API
resource "azurerm_cosmosdb_account" "speck_mongo" {
  name                = "speck-mongo-db"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  offer_type          = "Standard"
  kind                = "MongoDB"
  mongo_server_version = "7.0"
  burst_capacity_enabled = true
  
  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.speck_rg.location
    failover_priority = 0
  }
}

# Step 7: Create a MongoDB Database
resource "azurerm_cosmosdb_mongo_database" "speck_mongo_db" {
  name                = "speck-mongo-db"
  resource_group_name = azurerm_resource_group.speck_rg.name
  account_name        = azurerm_cosmosdb_account.speck_mongo.name
}

# Step 8: Create an Application Insights Resource
resource "azurerm_application_insights" "speck_app_insights" {
  name                = "speck-app-insights"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  application_type    = "web"
}

# Step 9: Create Redis Cache
resource "azurerm_redis_cache" "speck_redis" {
  name                = "speck-redis-cache"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  capacity            = 1
  family              = "C"
  sku_name            = "Standard"
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_reserved = 50
    maxmemory_delta    = 50
    maxmemory_policy   = "allkeys-lru"
  }
}

# Step 10: Create AKS Cluster for Qdrant
resource "azurerm_kubernetes_cluster" "speck_qdrant_cluster" {
  name                = "speck-qdrant-cluster"
  location            = azurerm_resource_group.speck_rg.location
  resource_group_name = azurerm_resource_group.speck_rg.name
  dns_prefix          = "speck-qdrant"

  identity {
    type = "SystemAssigned"
  }

  default_node_pool {
    name       = "system"
    vm_size    = "Standard_D2_v2"
    node_count = 1
  }

  network_profile {
    network_plugin    = "kubenet"
    load_balancer_sku = "standard"
  }

  http_application_routing_enabled = false
}

# Step 11: Dedicated node pool for Qdrant
resource "azurerm_kubernetes_cluster_node_pool" "qdrant_nodes" {
  name                  = "qdrant"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.speck_qdrant_cluster.id
  vm_size              = "Standard_B4s_v2"  # 4 vCPUs, 16 GB RAM
  node_count           = 3

  node_taints = [
    "qdrant-node=present:NoSchedule"
  ]
}

terraform {
  backend "azurerm" {
    storage_account_name = "specktfstatev1"
    container_name       = "tfstate"
    key                 = "terraform.tfstate"
    access_key          = "RnW/HPnCNM+ZxEWjbjteSpGe/3zzMIgbpr9x98Q9xeVsVUo2zVxC52sRo++5T3X2r437HJd8a1th+ASte1WDOQ=="
  }
}

# Outputs
output "speck_api_url" {
  description = "The URL of the Speck API"
  value       = azurerm_app_service.speck_api.default_site_hostname
}

output "mongodb_connection_string" {
  description = "The connection string for the MongoDB database"
  value       = azurerm_cosmosdb_account.speck_mongo.primary_mongodb_connection_string
  sensitive   = true
}

output "redis_connection_string" {
  description = "The connection string for Redis"
  value       = azurerm_redis_cache.speck_redis.primary_connection_string
  sensitive   = true
}

output "aks_qdrant_credentials" {
  value = {
    host                   = azurerm_kubernetes_cluster.speck_qdrant_cluster.kube_config[0].host
    cluster_ca_certificate = azurerm_kubernetes_cluster.speck_qdrant_cluster.kube_config[0].cluster_ca_certificate
  }
  sensitive = true
}
