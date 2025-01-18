from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
class PodMetrics(db.Model):
    """
    Represents the metrics of a Kubernetes Pod.

    Attributes:
        id (int): The primary key of the PodMetrics entry.
        pod_name (str): The name of the pod.
        namespace (str): The namespace in which the pod is running.
        container_name (str): The name of the container within the pod.
        cpu (float): The CPU usage of the container.
        memory (float): The memory usage of the container.
        timestamp (datetime): The timestamp when the metrics were recorded.
    """
    id = db.Column(db.Integer, primary_key=True)
    pod_name = db.Column(db.String(64), index=True, nullable=False)
    namespace = db.Column(db.String(64), index=True, nullable=False)
    container_name = db.Column(db.String(64), index=True, nullable=False)
    cpu = db.Column(db.Float, nullable=False)
    memory = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)