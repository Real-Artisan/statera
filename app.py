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
    Create all database tables.
    This function initializes the database tables within the Flask application context.
    """
    with app.app_context():
        try:
            # Check if the database is initialized and tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            if 'pod_metrics' not in tables:
                db.create_all()
                print("Database tables created.")
            else:
                print("Database tables already exist.")
        except Exception as e:
            print(f"Error initializing database: {e}")

def collect_metrics():
    """
    Collects metrics from Kubernetes pods in the "kube-system" namespace.

    This function uses the Kubernetes CustomObjectsApi to list custom objects
    of kind "pods" in the "metrics.k8s.io/v1beta1" API group. It extracts CPU
    and memory usage metrics for each container in each pod and returns them
    as a list of dictionaries.

    Returns:
        list: A list of dictionaries, each containing the following keys:
            - pod_name (str): The name of the pod.
            - namespace (str): The namespace of the pod.
            - container_name (str): The name of the container.
            - cpu (str): The CPU usage of the container.
            - memory (str): The memory usage of the container.

    Raises:
        urllib3.exceptions.MaxRetryError: If the maximum number of retries is exceeded.
        Exception: For any other errors that occur while collecting metrics.
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

def save_metrics_to_db(metrics):
    """
    Save a list of pod metrics to the database.

    Args:
        metrics (list): A list of dictionaries, where each dictionary contains
                        the following keys:
                        - "pod_name" (str): The name of the pod.
                        - "namespace" (str): The namespace of the pod.
                        - "container_name" (str): The name of the container.
                        - "cpu" (float): The CPU usage of the container.
                        - "memory" (float): The memory usage of the container.

    Raises:
        Exception: If there is an error while saving the metrics to the database,
                   the transaction is rolled back and the exception is printed.
    """
    with app.app_context():
        try:
            for metric in metrics:
                pod_metric = PodMetrics(
                    pod_name=metric["pod_name"],
                    namespace=metric["namespace"],
                    container_name=metric["container_name"],
                    cpu_usage=metric["cpu"],
                    memory_usage=metric["memory"],
                )
                db.session.add(pod_metric)
            db.session.commit()
            print("Metrics saved to database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving metrics to database: {e}")

def collect_and_save_metrics():
    """
    Collects metrics and saves them to the database.

    This function collects metrics using the `collect_metrics` function,
    saves them to the database using the `save_metrics_to_db` function,
    and prints the number of metrics collected and saved.

    Returns:
        None
    """
    metrics = collect_metrics()
    save_metrics_to_db(metrics)
    print(f"Collected and saved {len(metrics)} metrics.")

def query_metrics(limit=10):
    """
    Query the latest PodMetrics from the database.

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
    Display a list of metrics with details such as ID, Pod Name, Namespace, Container Name, CPU Usage, Memory Usage, and Timestamp.

    Args:
        limit (int, optional): The maximum number of metrics to display. Defaults to 10.

    Returns:
        None
    """
    metrics = query_metrics(limit)
    for metric in metrics:
        print(f"ID: {metric.id}, Pod Name: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU Usage: {metric.cpu_usage}, Memory Usage: {metric.memory_usage}, Timestamp: {metric.timestamp}")
        
def main():
    """
    Main function to load Kubernetes configuration, create database tables, 
    collect and save metrics, and display the collected metrics.

    The function performs the following steps:
    1. Attempts to load the Kubernetes configuration using `load_kube_config()`.
       If an exception occurs, it prints an error message and exits.
    2. Creates necessary database tables by calling `create_tables()`.
    3. Collects and saves metrics by calling `collect_and_save_metrics()`.
    4. Displays the collected metrics by calling `display_metrics()` and prints the result.
    """
    try:
        load_kube_config()
    except Exception as e:
        print(f"Error loading kube config: {e}")
        return
    create_tables()
    collect_and_save_metrics()
    print(display_metrics())

if __name__ == "__main__":
    main()
    app.run(host='0.0.0.0', port=8080, debug=True)
