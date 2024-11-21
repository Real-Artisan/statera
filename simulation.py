def simulate_pod_placement(nodes, pod_request_cpu, pod_request_memory):
    """
    Simulates how many pods can be placed in the cluster given resource requests.

    :param nodes: List of nodes with allocatable resources.
    :param pod_request_cpu: CPU request per pod (millicores, e.g., '500m').
    :param pod_request_memory: Memory request per pod (e.g., '128Mi').
    :return: Number of pods that can be placed.
    """
    total_pods = 0

    for node in nodes:
        cpu_allocatable = parse_resource(node['cpu'])
        memory_allocatable = parse_resource(node['memory'])

        pods_per_node_cpu = cpu_allocatable // pod_request_cpu
        pods_per_node_memory = memory_allocatable // pod_request_memory

        pods_per_node = min(pods_per_node_cpu, pods_per_node_memory)
        total_pods += pods_per_node

    return total_pods

def parse_resource(resource_str):
    """
    Converts Kubernetes resource strings (e.g., '500m', '128Mi') to integer values.

    :param resource_str: Resource string from Kubernetes API.
    :return: Parsed value as an integer.
    """
    if resource_str.endswith('m'):  # CPU in millicores
        return int(resource_str[:-1])
    elif resource_str.endswith('Mi'):  # Memory in MiB
        return int(resource_str[:-2]) * 1024 * 1024
    elif resource_str.endswith('Gi'):  # Memory in GiB
        return int(resource_str[:-2]) * 1024 * 1024 * 1024
    return int(resource_str)

# Example Input // You can update this array with values 
# from nodes in your actual cluster and see
# how much more pods you can produce.
# The nodes below are from one of the Clusters I manage.
# I currently had a maximum of 51 but these configurations
# helped me free up resources for 9 extra pods
nodes = [
    {"cpu": "2000m", "memory": "3Gi"},
    {"cpu": "2000m", "memory": "3Gi"},
    {"cpu": "2000m", "memory": "3Gi"},
]

# Simulating placement of pods requesting 500m CPU and 128Mi memory
pods = simulate_pod_placement(nodes, 100, 120 * 1024 * 1024)
print(f"Total Pods that can be placed: {pods}")
