from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
class PodMetrics(db.Model):
    """
    PodMetrics model represents the metrics data for a Kubernetes pod.

    Attributes:
        id (int): Primary key for the PodMetrics entry.
        pod_name (str): Name of the pod.
        namespace (str): Namespace in which the pod is running.
        container_name (str): Name of the container within the pod.
        cpu (str): CPU usage of the container.
        memory (str): Memory usage of the container.
        timestamp (datetime): Timestamp when the metrics were recorded.
    """
    id = db.Column(db.Integer, primary_key=True)
    pod_name = db.Column(db.String(64), index=True, nullable=False)
    namespace = db.Column(db.String(64), index=True, nullable=False)
    container_name = db.Column(db.String(64), index=True, nullable=False)
    cpu = db.Column(db.String, nullable=False)
    memory = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)