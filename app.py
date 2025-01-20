from flask import Flask
from kubernetes import client, config
import urllib3
from config import Config
from models import db, PodMetrics

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def load_kube_config():
    """
    Load Kubernetes configuration.

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

def create_tables():
    """
    Initializes the database by creating required tables if they do not already exist.

    This function checks if the required tables are present in the database. If any of the
    required tables are missing, it creates them. The function operates within the application
    context and handles any exceptions that may occur during the process.

    Required tables:
    - pod_metrics

    Prints:
    - A message indicating whether the required tables were created or already exist.
    - An error message if there is an issue initializing the database.
    """
    with app.app_context():
        try:
            # Check if the database is initialized and tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            required_tables = ['pod_metrics']
            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                db.create_all()
                print(f"Database tables created: {', '.join(missing_tables)}.")
            else:
                print("All required database tables already exist.")
        except Exception as e:
            print(f"Error initializing database: {e}")

def collect_metrics():
    """
    Collects metrics from the Kubernetes metrics server for all pods in the "kube-system" namespace.

    This function uses the Kubernetes CustomObjectsApi to list custom objects of kind "pods" in the 
    "metrics.k8s.io/v1beta1" API group. It extracts CPU and memory usage for each container in each pod.

    Returns:
        list: A list of dictionaries, each containing the following keys:
            - "pod_name" (str): The name of the pod.
            - "namespace" (str): The namespace of the pod.
            - "container_name" (str): The name of the container.
            - "cpu" (str): The CPU usage of the container.
            - "memory" (str): The memory usage of the container.

    Raises:
        urllib3.exceptions.MaxRetryError: If the maximum number of retries is exceeded when making the API call.
        Exception: For any other exceptions that occur during the API call.
    """
    namespace = "kube-system"
    api_instance = client.CustomObjectsApi()
    try:
        response = api_instance.list_namespaced_custom_object("metrics.k8s.io", "v1beta1", namespace, "pods")
        metrics = []
        for pod in response.get("items", []):
            pod_name = pod["metadata"]["name"]
            namespace = pod["metadata"]["namespace"]
            for container in pod["containers"]:
                container_name = container["name"]
                cpu = container["usage"]["cpu"]
                memory = container["usage"]["memory"]
                metrics.append({
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "container_name": container_name,
                    "cpu": cpu,
                    "memory": memory,
                })
        return metrics
    except urllib3.exceptions.MaxRetryError as e:
        print(f"MaxRetryError: {e}")
    except Exception as e:
        print(f"Error collecting metrics: {e}")

def preprocess_metrics(metrics):
    """
    Preprocess a list of metrics by converting CPU and memory values to standard units.
    Args:
        metrics (list of dict): A list of dictionaries where each dictionary contains
                                'cpu' and 'memory' keys with their respective values.
    Returns:
        list of dict: The input list with 'cpu' values converted to millicores and
                      'memory' values converted to MiB.
    """
    def convert_cpu(cpu_value):
        """
        Convert CPU value from nanocores to millicores.

        Args:
            cpu_value (str): The CPU value as a string, which may end with 'n' indicating nanocores.

        Returns:
            str: The CPU value converted to millicores if it was in nanocores, otherwise the original value.
        """
        if cpu_value.endswith("n"):
            return f"{float(cpu_value[:-1]) // 1000000}m"
        return cpu_value # Already in millicores
    
    def convert_memory(memory_value):
        """
        Convert memory value from KiB to MiB if necessary.

        Args:
            memory_value (str): The memory value as a string, which may end with "Ki" indicating KiB.

        Returns:
            str: The memory value converted to MiB if it was in KiB, otherwise the original value.
        """
        if memory_value.endswith("Ki"):
            return f"{float(memory_value[:-2]) / 1024}Mi"
        return memory_value # Already in MiB
    
    for metric in metrics:
        metric["cpu"] = convert_cpu(metric["cpu"])
        metric["memory"] = convert_memory(metric["memory"])
    return metrics

def store_metrics(metrics):
    """
    Stores a list of pod metrics in the database.

    Args:
        metrics (list): A list of dictionaries, where each dictionary contains
                        the following keys:
                        - pod_name (str): The name of the pod.
                        - namespace (str): The namespace of the pod.
                        - container_name (str): The name of the container.
                        - cpu (float): The CPU usage of the container.
                        - memory (float): The memory usage of the container.

    Raises:
        Exception: If there is an error storing the metrics in the database.
    """
    with app.app_context():
        try:
            for metric in metrics:
                pod_metric = PodMetrics(
                    pod_name=metric["pod_name"],
                    namespace=metric["namespace"],
                    container_name=metric["container_name"],
                    cpu=metric["cpu"],
                    memory=metric["memory"]
                )
                db.session.add(pod_metric)
            db.session.commit()
            print(f"Stored {len(metrics)} metrics in the database -f store_metrics.")
        except Exception as e:
            db.session.rollback()
            print(f"Error storing metrics: {e}")

def collect_preprocess_and_store_metrics():
    """
    Collects raw metrics, preprocesses them, and stores them in the database.

    This function performs the following steps:
    1. Collects raw metrics by calling the `collect_metrics` function.
    2. Preprocesses the collected metrics by calling the `preprocess_metrics` function.
    3. Attempts to store the processed metrics in the database by calling the `store_metrics` function.
    4. Prints the number of metrics stored in the database if successful.
    5. Catches and prints any exceptions that occur during the storage process.

    Raises:
        Exception: If an error occurs during the storage of metrics.
    """
    raw_metrics = collect_metrics()
    processed_metrics = preprocess_metrics(raw_metrics)
    try:
        store_metrics(processed_metrics)
        print(f"Stored {len(processed_metrics)} metrics in the database -f collect_preprocess_and_store_metrics.")
    except Exception as e:
        print(f"Error in collect_preprocess_and_store_metrics: {e}")

def query_metrics(limit=10):
    """
    Query the most recent PodMetrics from the database.

    Args:
        limit (int): The maximum number of metrics to retrieve. Defaults to 10.

    Returns:
        list: A list of PodMetrics objects ordered by timestamp in descending order.
              Returns an empty list if an error occurs during the query.
    """
    with app.app_context():
        try:
            metrics = PodMetrics.query.order_by(PodMetrics.timestamp.desc()).limit(limit).all()
            return metrics
        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []

def display_metrics(limit=10):
    """
    Display metrics for a specified number of pods.

    Args:
        limit (int, optional): The number of metrics to display. Defaults to 10.

    Returns:
        None

    Prints:
        A formatted string for each metric containing:
        - Pod name
        - Namespace
        - Container name
        - CPU usage
        - Memory usage
        - Timestamp
    """
    metrics = query_metrics(limit)
    for metric in metrics:
        print(f"Pod: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU: {metric.cpu}, Memory: {metric.memory}, Timestamp: {metric.timestamp}")

def main():
    """
    Main function to load Kubernetes configuration, create database tables,
    collect, preprocess, and store metrics, and display the metrics.

    This function performs the following steps:
    1. Attempts to load the Kubernetes configuration using `load_kube_config()`.
       If an exception occurs, it prints an error message and exits the function.
    2. Creates necessary database tables by calling `create_tables()`.
    3. Collects, preprocesses, and stores metrics by calling 
       `collect_preprocess_and_store_metrics()`.
    4. Displays the collected metrics by calling `display_metrics()`.
    """
    try:
        load_kube_config()
    except Exception as e:
        print(f"Error loading kube config: {e}")
        return
    create_tables()
    collect_preprocess_and_store_metrics()
    display_metrics()

if __name__ == "__main__":
    main()
    app.run(host='0.0.0.0', port=8080, debug=True)
