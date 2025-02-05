from flask import Flask
from kubernetes import client, config
import urllib3
from config import Config
from models import db, PodMetrics
import pandas as pd

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def load_kube_config():
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

def collect_metrics(namespace="kube-system"):
    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    try:
        print(f"Fetching pods and metrics in namespace {namespace}...")
        pod_list = core_api.list_namespaced_pod(namespace)
        pod_specs = {pod.metadata.name: pod for pod in pod_list.items}

        metrics_response = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods"
        )
        metrics = []

        for pod in metrics_response.get("items", []):
            pod_name = pod["metadata"]["name"]
            namespace = pod["metadata"]["namespace"]
            pod_spec = pod_specs.get(pod_name, None)

            for container in pod["containers"]:
                container_name = container["name"]
                cpu = container["usage"]["cpu"]
                memory = container["usage"]["memory"]

                container_spec = next((c for c in pod_spec.spec.containers if c.name == container_name), None) if pod_spec else None

                cpu_request = container_spec.resources.requests.get("cpu", None) if container_spec.resources.requests else None
                cpu_limit = container_spec.resources.limits.get("cpu", None) if container_spec.resources.limits else None
                memory_request = container_spec.resources.requests.get("memory", None) if container_spec.resources.requests else None
                memory_limit = container_spec.resources.limits.get("memory", None) if container_spec.resources.limits else None

                metrics.append({
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "container_name": container_name,
                    "cpu_usage": cpu,
                    "memory_usage": memory,
                    "cpu_request": cpu_request,
                    "cpu_limit": cpu_limit,
                    "memory_request": memory_request,
                    "memory_limit": memory_limit
                })
        return metrics
    except Exception as e:
        print(f"Error fetching pod metrics: {e}")
        return []

def preprocess_metrics(metrics):
    def convert_cpu(cpu_value):
        if not cpu_value:  # Handle None case
            return None
        if cpu_value.endswith("n"):
            return f"{float(cpu_value[:-1]) / 1000000}m"
        return cpu_value  # Already in millicores

    def convert_memory(memory_value):
        if not memory_value:  # Handle None case
            return None
        if memory_value.endswith("Ki"):
            return f"{float(memory_value[:-2]) / 1024}Mi"
        return memory_value  # Already in MiB

    for metric in metrics:
        metric["cpu_usage"] = convert_cpu(metric["cpu_usage"])
        metric["memory_usage"] = convert_memory(metric["memory_usage"])
        metric["cpu_request"] = convert_cpu(metric["cpu_request"])
        metric["cpu_limit"] = convert_cpu(metric["cpu_limit"])
        metric["memory_request"] = convert_memory(metric["memory_request"])
        metric["memory_limit"] = convert_memory(metric["memory_limit"])

    return metrics

def store_metrics(metrics):
    with app.app_context():
        try:
            for metric in metrics:
                pod_metric = PodMetrics(
                    pod_name=metric["pod_name"],
                    namespace=metric["namespace"],
                    container_name=metric["container_name"],
                    cpu_usage=metric["cpu_usage"],
                    memory_usage=metric["memory_usage"],
                    cpu_request=metric["cpu_request"],
                    cpu_limit=metric["cpu_limit"],
                    memory_request=metric["memory_request"],
                    memory_limit=metric["memory_limit"]
                )
                db.session.add(pod_metric)
            db.session.commit()
            print(f"Stored {len(metrics)} metrics in the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error storing metrics: {e}")

def collect_preprocess_and_store_metrics():
    raw_metrics = collect_metrics()
    processed_metrics = preprocess_metrics(raw_metrics)
    print("Processed metrics, storing in database...")
    try:
        store_metrics(processed_metrics)
    except Exception as e:
        print(f"Error storing metrics: {e}")

def query_metrics(limit=10):
    with app.app_context():
        try:
            metrics = PodMetrics.query.order_by(PodMetrics.timestamp.desc()).limit(limit).all()
            return metrics
        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []

def display_metrics(limit=10):
    metrics = query_metrics(limit)
    for metric in metrics:
        print(f"Pod: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU Usage: {metric.cpu_usage}, Memory Usage: {metric.memory_usage}, CPU Request: {metric.cpu_request}, CPU Limit: {metric.cpu_limit}, Memory Request: {metric.memory_request}, Memory Limit: {metric.memory_limit}, Timestamp: {metric.timestamp}")

def main():
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
