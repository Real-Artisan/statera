resource "kind_cluster" "statera_kind_cluster" {
  name       = var.cluster_name
  node_image = "kindest/node:v${var.cluster_version}"
  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"
    node {
      role = "control-plane"
      kubeadm_config_patches = [
        "kind: InitConfiguration\nnodeRegistration:\n  kubeletExtraArgs:\n    node-labels: \"ingress-ready=true\"\n"
      ]
    }
    node {
      role = "worker_01"
      extra_port_mappings {
        container_port = 80
        host_port      = 8086
      }
    }
    node {
      role = "worker_02"
      extra_port_mappings {
        container_port = 80
        host_port      = 8087
      }
    }

  }
}