from kubernetes import client, config

def collect_node_data():
    """Fetch node allocatable resources using the Kubernetes API."""
    config.load_kube_config()
    v1 = client.CoreV1Api()

    nodes = []
    node_list = v1.list_node()
    for node in node_list.items:
        name = node.metadata.name
        allocatable = node.status.allocatable
        nodes.append({
            "name": name,
            "cpu": allocatable["cpu"],
            "memory": allocatable["memory"]
        })
    return nodes

def simulate_pod_placement(nodes, pod_request_cpu, pod_request_memory):
    """
    Simulates how many pods can be placed in the cluster given resource requests.
    """
    total_pods = 0
    for node in nodes:
        cpu_allocatable = parse_resource(node['cpu'])
        memory_allocatable = parse_resource(node['memory'])

        pods_per_node_cpu = cpu_allocatable // pod_request_cpu
        pods_per_node_memory = memory_allocatable // pod_request_memory

        pods_per_node = min(pods_per_node_cpu, pods_per_node_memory)
        total_pods += pods_per_node

        print(f"Node {node['name']} can fit {pods_per_node} pods.")
    return total_pods

def parse_resource(resource_str):
    """
    Converts Kubernetes resource strings to integer values.
    
    Supports:
    - CPU: "500m" (millicores)
    - Memory: "128Mi", "1Gi", "5440968Ki"
    """
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
    # Step 1: Collect node data
    nodes = collect_node_data()
    print("Collected Node Data:", nodes)

    # Step 2: Define pod resource requirements for simulation
    pod_request_cpu = 10  # in millicores
    pod_request_memory = 128 * 1024 * 1024  # in bytes (128Mi)

    # Step 3: Simulate pod placement
    total_pods = simulate_pod_placement(nodes, pod_request_cpu, pod_request_memory)
    print(f"Total Pods that can be placed: {total_pods}")

if __name__ == "__main__":
    main()
