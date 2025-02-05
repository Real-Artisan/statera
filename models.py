from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
class PodMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pod_name = db.Column(db.String(64), index=True, nullable=False)
    namespace = db.Column(db.String(64), index=True, nullable=False)
    container_name = db.Column(db.String(64), index=True, nullable=False)
    cpu_usage = db.Column(db.String, nullable=False)
    memory_usage = db.Column(db.String, nullable=False)
    cpu_request = db.Column(db.String(50), nullable=True)
    cpu_limit = db.Column(db.String(50), nullable=True)
    memory_request = db.Column(db.String(50), nullable=True)
    memory_limit = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)