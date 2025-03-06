from flask import jsonify
from database import create_app
from tables import create_tables
from metrics import collect_preprocess_and_store_metrics, query_metrics, get_namespaces
from kubeconfig import load_kube_config

app = create_app()


@app.route('/', methods=['GET'])
def index():
    return "Statera API"

@app.route('/pods', methods=['GET'])
def pods():
    output = []
    metrics = query_metrics()
    for metric in metrics:
        output.append({
            "pod_name": metric.pod_name,
            "namespace": metric.namespace,
            "container_name": metric.container_name,
            "cpu_usage": metric.cpu_usage,
            "memory_usage": metric.memory_usage,
            "cpu_request": metric.cpu_request,
            "cpu_limit": metric.cpu_limit,
            "memory_request": metric.memory_request,
            "memory_limit": metric.memory_limit
        })
    return output, 200

@app.route('/metrics', methods=['GET'])
def podMetrics():
    metrics = query_metrics()
    return jsonify(metrics), 200

@app.route('/ns', methods=['GET'])
def namespaces():
    return jsonify(get_namespaces()), 200

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
