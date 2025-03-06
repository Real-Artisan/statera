from kubernetes import client
import urllib3
from models import db, PodMetrics
from database import create_app
from preprocess import preprocess_metrics, convert_cpu, convert_memory

app = create_app()

def get_namespaces():
    core_api = client.CoreV1Api()
    try:
        namespaces = core_api.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except Exception as e:
        print(f"Error fetching namespaces: {e}")
        return []

def collect_metrics():
    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    ns = get_namespaces()

    live_pods = set()

    with app.app_context():
        # Check if the database is initialized and tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        if "pod_metrics" not in tables:
            print("Database tables not initialized, skipping metrics collection.")
            return []

        metrics = []
        for namespace in ns:
            try:
                print(f"Fetching pods and metrics in namespace {namespace}...")
                pod_list = core_api.list_namespaced_pod(namespace)
                pod_specs = {pod.metadata.name: pod for pod in pod_list.items}

                metrics_response = custom_api.list_namespaced_custom_object(
                    group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods"
                )
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
                
            except urllib3.exceptions.MaxRetryError as e:
                print(f"MaxRetryError: {e}")
            except Exception as e:
                print(f"Error fetching pod metrics: {e}")
                return []
        # Remove deleted pods from the database
        all_entries = PodMetrics.query.with_entities(PodMetrics.namespace, PodMetrics.pod_name).all()
        for db_namespace, db_pod_name in all_entries:
            if (db_namespace, db_pod_name) not in live_pods:
                print(f"Pod {db_pod_name} in namespace {db_namespace} no longer exists, removing from DB...")
                PodMetrics.query.filter_by(namespace=db_namespace, pod_name=db_pod_name).delete()
        
        db.session.commit()
        print("Metrics collection complete.")
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

def query_metrics():
    with app.app_context():
        try:
            metrics = PodMetrics.query.order_by(PodMetrics.timestamp.desc()).all()
            return metrics
        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []

def display_metrics():
    metrics = query_metrics()
    for metric in metrics:
        print(f"Pod: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU Usage: {metric.cpu_usage}, Memory Usage: {metric.memory_usage}, CPU Request: {metric.cpu_request}, CPU Limit: {metric.cpu_limit}, Memory Request: {metric.memory_request}, Memory Limit: {metric.memory_limit}, Timestamp: {metric.timestamp}")
