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
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)