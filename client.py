from kubernetes import client, config

def main():
    # Load kubeconfig (use in-cluster config if running in a pod)
    config.load_kube_config()  # For kind cluster
    # config.load_incluster_config()  # Uncomment for running in a DaemonSet

    # Initialize API clients
    v1 = client.CoreV1Api()

    # Fetch and print node details
    print("Node Resource Summary:")
    nodes = v1.list_node()
    for node in nodes.items:
        name = node.metadata.name
        capacity = node.status.capacity
        allocatable = node.status.allocatable
        print(f"Node: {name}")
        print(f"  Capacity: CPU: {capacity['cpu']}, Memory: {capacity['memory']}")
        print(f"  Allocatable: CPU: {allocatable['cpu']}, Memory: {allocatable['memory']}")
        print("-" * 40)

    # Fetch and print pod details
    print("Pod Resource Summary:")
    pods = v1.list_pod_for_all_namespaces()
    for pod in pods.items:
        name = pod.metadata.name
        namespace = pod.metadata.namespace
        print(f"Pod: {name} (Namespace: {namespace})")
        for container in pod.spec.containers:
            resources = container.resources
            requests = resources.requests or {}
            limits = resources.limits or {}
            print(f"  Container: {container.name}")
            print(f"    Requests: CPU: {requests.get('cpu', 'None')}, Memory: {requests.get('memory', 'None')}")
            print(f"    Limits: CPU: {limits.get('cpu', 'None')}, Memory: {limits.get('memory', 'None')}")
        print("-" * 40)

if __name__ == "__main__":
    main()
