variable "cluster_name" {
  type        = string
  default     = "test-cluster"
  description = "Clustername for kind cluster"
}

variable "cluster_version" {
  type        = string
  default     = "1.31.0"
  description = "Kubernetes version for kind cluster"
}