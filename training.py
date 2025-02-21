import pandas as pd
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

db = SQLAlchemy()

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

    metrics = PodMetrics.query.all()

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