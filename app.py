from flask import Flask
from kubernetes import client, config
import urllib3
from config import Config
from models import db, PodMetrics

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
    metrics = collect_metrics()
    save_metrics_to_db(metrics)
    print(f"Collected and saved {len(metrics)} metrics.")

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
        print(f"ID: {metric.id}, Pod Name: {metric.pod_name}, Namespace: {metric.namespace}, Container Name: {metric.container_name}, CPU Usage: {metric.cpu_usage}, Memory Usage: {metric.memory_usage}, Timestamp: {metric.timestamp}")
        
def main():
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
