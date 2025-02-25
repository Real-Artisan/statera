from flask import jsonify
from database import create_app
from tables import create_tables
from metrics import collect_preprocess_and_store_metrics, query_metrics
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
