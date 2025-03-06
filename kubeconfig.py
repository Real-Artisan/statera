from kubernetes import config

def load_kube_config():
    """
    Loads the Kubernetes configuration.

    This function attempts to load the Kubernetes configuration in the following order:
    1. In-cluster configuration: If the code is running inside a Kubernetes cluster, it will try to load the in-cluster configuration.
    2. Local kubeconfig: If the in-cluster configuration fails, it will fallback to loading the local kubeconfig file.

    Prints a message indicating which configuration is being used or an error message if both attempts fail.

    Raises:
        config.ConfigException: If both in-cluster and local kubeconfig loading fail.
    """
    try:
        config.load_incluster_config()  # Try in-cluster config
        print("Using in-cluster kubeconfig.")
    except config.ConfigException:
        try:
            config.load_kube_config()  # Fallback to local kubeconfig
            print("Using local kubeconfig.")
        except Exception as e:
            print(f"Error loading local kubeconfig: {e}")
