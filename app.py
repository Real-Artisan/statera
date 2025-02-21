from flask import Flask, jsonify
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

def collect_metrics(namespace="banking-backend"):
    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    with app.app_context():
        # Check if the database is initialized and tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        if "pod_metrics" not in tables:
            print("Database tables not initialized, skipping metrics collection.")
            return []

        try:
            print(f"Fetching pods and metrics in namespace {namespace}...")
            pod_list = core_api.list_namespaced_pod(namespace)
            pod_specs = {pod.metadata.name: pod for pod in pod_list.items}

            metrics_response = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods"
            )
            metrics = []
            live_pods = set()

            for pod in metrics_response.get("items", []):
                pod_name = pod["metadata"]["name"]
                namespace = pod["metadata"]["namespace"]
                live_pods.add((namespace, pod_name))
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

                    # Check if pod already exists in DB
                    existing_entry = PodMetrics.query.filter_by(
                        pod_name=pod_name,
                        namespace=namespace,
                        container_name=container_name
                    ).first()

                    if existing_entry:
                        print(f"Pod {pod_name} already exists in DB, updating metrics...")
                        existing_entry.cpu_usage = convert_cpu(cpu)
                        existing_entry.memory_usage = convert_memory(memory)
                        existing_entry.cpu_request = convert_cpu(cpu_request)
                        existing_entry.cpu_limit = convert_cpu(cpu_limit)
                        existing_entry.memory_request = convert_memory(memory_request)
                        existing_entry.memory_limit = convert_memory(memory_limit)
                    else:
                        print(f"Pod {pod_name} does not exist in DB, adding metrics...")
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
            
            # Remove deleted pods from the database
            all_entries = PodMetrics.query.with_entities(PodMetrics.namespace, PodMetrics.pod_name).all()
            for db_namespace, db_pod_name in all_entries:
                if (db_namespace, db_pod_name) not in live_pods:
                    print(f"Pod {db_pod_name} in namespace {db_namespace} no longer exists, removing from DB...")
                    PodMetrics.query.filter_by(namespace=db_namespace, pod_name=db_pod_name).delete()
            
            db.session.commit()
            print("Metrics collection complete.")
            return metrics
        except urllib3.exceptions.MaxRetryError as e:
            print(f"MaxRetryError: {e}")
        except Exception as e:
            print(f"Error fetching pod metrics: {e}")
            return []

def preprocess_metrics(metrics):
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

def parse_cpu(cpu_value):
    if cpu_value.endswith("m"):
        return float(cpu_value[:-1]) / 1000
    return float(cpu_value)

def parse_memory(memory_value):
    if memory_value.endswith("Mi"):
        return float(memory_value[:-2])
    elif memory_value.endswith("Gi"):
        return float(memory_value[:-2]) * 1024
    return float(memory_value)

def load_data():

    with app.app_context():
        try:
            metrics = PodMetrics.query.order_by(PodMetrics.timestamp.desc()).limit(5).all()
        except Exception as e:
            print(f"Error querying metrics: {e}")
            return

    data = []

    for metric in metrics:
        try:
            data.append({
                "cpu_usage": parse_cpu(metric.cpu_usage),
                "memory_usage": parse_memory(metric.memory_usage),
                "cpu_request": parse_cpu(metric.cpu_request),
                "cpu_limit": parse_cpu(metric.cpu_limit),
                "memory_request": parse_memory(metric.memory_request),
                "memory_limit": parse_memory(metric.memory_limit)
            })
        except Exception as e:
            print(f"Error parsing metric: {e}")

    df =  pd.DataFrame(data).dropna()
    return df

@app.route('/', methods=['GET'])
def index():
    return "Statera API"

@app.route('/pods', methods=['GET'])
def pods():
    output = []
    metrics = query_metrics()
    for metric in metrics:
        output.append(f"Pod: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU Usage: {metric.cpu_usage}, Memory Usage: {metric.memory_usage}, CPU Request: {metric.cpu_request}, CPU Limit: {metric.cpu_limit}, Memory Request: {metric.memory_request}, Memory Limit: {metric.memory_limit}, Timestamp: {metric.timestamp}")
    return jsonify(output), 200

def main():
    try:
        load_kube_config()
    except Exception as e:
        print(f"Error loading kube config: {e}")
        return
    create_tables()
    collect_preprocess_and_store_metrics()

if __name__ == "__main__":
    main()
    app.run(host='0.0.0.0', port=8080, debug=True)
