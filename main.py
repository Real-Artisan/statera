import os
import yaml
from kubernetes import client, config
import re

def load_kube_config():
    try:
        config.load_incluster_config()  # Try in-cluster config
        print("Using in-cluster kubeconfig.")
    except config.ConfigException:
        config.load_kube_config()  # Fallback to local kubeconfig
        print("Using local kubeconfig.")

# Parse CPU (e.g., 200m -> 0.2 cores, 2 -> 2 cores)
def parse_cpu(cpu_str):
    """
    Parse a Kubernetes CPU string and convert it to a float representing cores.
    """
    if cpu_str.endswith("m"):  # Handles millicores like '200m'
        return float(cpu_str[:-1]) / 1000
    try:
        return float(cpu_str)  # Handles cores like '2'
    except ValueError:
        raise ValueError(f"Invalid CPU format: {cpu_str}")


# Parse memory (e.g., 512Mi -> 512 MiB, 2Gi -> 2048 MiB)
def parse_memory(memory_str):
    pattern = re.compile(r'(\d+)([KMGTE]+i)')
    match = pattern.match(memory_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)

        # Conversion factors for memory units
        conversion_factors = {
            "Ki": 1 / 1024,  # Convert Ki to Mi
            "Mi": 1,         # Mi is the base unit
            "Gi": 1024,      # Convert Gi to Mi
            "Ti": 1024 * 1024  # Convert Ti to Mi
        }

        return value * conversion_factors.get(unit, 1)  # Default to Mi
    raise ValueError(f"Invalid memory format: {memory_str}")


def simulate_pod_capacity(node_resources, pod_resources):
    node_cpu = float(node_resources['cpu'])
    node_memory = float(node_resources['memory'])
    pod_cpu = float(pod_resources['cpu'])
    pod_memory = float(pod_resources['memory'])

    cpu_pod_capacity = node_cpu // pod_cpu
    memory_pod_capacity = node_memory // pod_memory

    return min(cpu_pod_capacity, memory_pod_capacity)


def calculate_optimized_pod_capacity(node_resources, optimized_resources):
    node_cpu = float(node_resources['cpu'])
    node_memory = float(node_resources['memory'])
    optimized_cpu = parse_cpu(optimized_resources['cpu'])
    optimized_memory = parse_memory(optimized_resources['memory'])

    optimized_cpu_capacity = node_cpu // optimized_cpu
    optimized_memory_capacity = node_memory // optimized_memory

    return min(optimized_cpu_capacity, optimized_memory_capacity)


def calculate_pod_capacity(node_resources, pod_resources, optimized_resources):
    current_capacity = simulate_pod_capacity(node_resources, pod_resources)
    optimized_capacity = calculate_optimized_pod_capacity(node_resources, optimized_resources)
    return current_capacity, optimized_capacity


def main():
    try:
        load_kube_config()
    except Exception as e:
        print(f"Error loading kube config: {e}")
        return

    v1 = client.CoreV1Api()
    nodes = v1.list_node()

    node_resources = {}
    for node in nodes.items:
        node_cpu = parse_cpu(node.status.capacity['cpu'])
        node_memory = parse_memory(node.status.capacity['memory'])

        node_resources[node.metadata.name] = {
            'cpu': node_cpu,
            'memory': node_memory
        }

    pod_resources = {
        'cpu': '1',   # 1 core
        'memory': '2048'  # 2 GiB
    }

    optimized_resources = {
        'cpu': '50m', 
        'memory': '150Mi'
    }

    for node_name, resources in node_resources.items():
        current_capacity, optimized_capacity = calculate_pod_capacity(resources, pod_resources, optimized_resources)
        print(f"Node: {node_name}")
        print(f"Current Pods: {current_capacity}")
        print(f"Optimized Pods: {optimized_capacity}")
        print("-" * 40)

        # Save results in ConfigMap
        configmap_data = {
            "data": {
                "pod_capacity_report": f"Node: {node_name}\nCurrent Pods: {current_capacity}\nOptimized Pods: {optimized_capacity}"
            }
        }
        with open('/etc/configmap/pod_capacity.yaml', 'w') as f:
            yaml.dump(configmap_data, f)

        os.system("kubectl apply -f /etc/configmap/pod_capacity.yaml")


if __name__ == "__main__":
    main()
