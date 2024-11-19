terraform {
  required_version = ">= 1.9.0"
}

locals {
  cluster_name         = "statera-cluster"
  cluster_version      = "1.31.0"
}

module "infrastructure" {
  source          = "./modules"
  cluster_name    = local.cluster_name
  cluster_version = local.cluster_version
}

output "cluster_endpoint" {
  value = module.infrastructure.cluster_endpoint
}