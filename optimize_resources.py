from kubernetes import client, config

def collect_cluster_data():
    """Fetch node and pod data from the Kubernetes cluster."""
    config.load_kube_config()
    v1 = client.CoreV1Api()

    # Collect node data
    nodes = []
    node_list = v1.list_node()
    for node in node_list.items:
        allocatable = node.status.allocatable
        nodes.append({
            "name": node.metadata.name,
            "cpu": allocatable["cpu"],
            "memory": allocatable["memory"]
        })

    # Collect pod data
    pods = []
    pod_list = v1.list_pod_for_all_namespaces()
    for pod in pod_list.items:
        if pod.status.phase == "Running":
            for container in pod.spec.containers:
                requests = container.resources.requests or {}
                pods.append({
                    "node": pod.spec.node_name,
                    "cpu": parse_resource(requests.get("cpu", "0")),
                    "memory": parse_resource(requests.get("memory", "0"))
                })

    return nodes, pods

def optimize_pod_resources(nodes, existing_pods, default_pod_requests):
    """Optimizes resource requests for new pods based on cluster resources."""
    # Calculate remaining resources per node
    for node in nodes:
        cpu_used = sum(pod['cpu'] for pod in existing_pods if pod['node'] == node['name'])
        memory_used = sum(pod['memory'] for pod in existing_pods if pod['node'] == node['name'])
        
        node['remaining_cpu'] = parse_resource(node['cpu']) - cpu_used
        node['remaining_memory'] = parse_resource(node['memory']) - memory_used
    
    # Allocate resources for new pods
    optimized_pod_requests = []
    for node in nodes:
        remaining_cpu = node['remaining_cpu']
        remaining_memory = node['remaining_memory']
        
        pods_per_node_cpu = remaining_cpu // default_pod_requests['cpu']
        pods_per_node_memory = remaining_memory // default_pod_requests['memory']
        
        num_pods = min(pods_per_node_cpu, pods_per_node_memory)
        
        for _ in range(num_pods):
            optimized_pod_requests.append({
                "node": node['name'],
                "cpu": default_pod_requests['cpu'],
                "memory": default_pod_requests['memory']
            })

    return optimized_pod_requests

def parse_resource(resource_str):
    """Converts Kubernetes resource strings to integer values."""
    if resource_str.endswith('m'):  # CPU in millicores
        return int(resource_str[:-1])
    elif resource_str.endswith('Ki'):  # Memory in Kibibytes
        return int(resource_str[:-2]) * 1024
    elif resource_str.endswith('Mi'):  # Memory in Mebibytes
        return int(resource_str[:-2]) * 1024 * 1024
    elif resource_str.endswith('Gi'):  # Memory in Gibibytes
        return int(resource_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(resource_str)

def main():
    # Step 1: Collect data from the cluster
    nodes, existing_pods = collect_cluster_data()
    print("Collected Node Data:", nodes)
    print("Collected Pod Data:", existing_pods)

    # Step 2: Define default pod resource requests for optimization
    default_pod_requests = {"cpu": 250, "memory": 128 * 1024 * 1024}

    # Step 3: Optimize resource allocation
    optimized_requests = optimize_pod_resources(nodes, existing_pods, default_pod_requests)
    print("Optimized Pod Resource Requests:", optimized_requests)

if __name__ == "__main__":
    main()
