import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app import app
from models import db, PodMetrics
# from app.models import PodMetrics
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Function to convert CPU and Memory values to numeric
def convert_cpu(cpu_value):
    if isinstance(cpu_value, str):
        if cpu_value.endswith("n"):  # Convert nanocores to millicores
            return float(cpu_value[:-1]) / 1e6
        elif cpu_value.endswith("m"):  # Convert millicores to cores
            return float(cpu_value[:-1]) / 1000
    return float(cpu_value) if cpu_value else np.nan  # Already in cores

def convert_memory(memory_value):
    if isinstance(memory_value, str):
        if memory_value.endswith("Ki"):  # Convert KiB to MiB
            return float(memory_value[:-2]) / 1024
        elif memory_value.endswith("Mi"):  # Already in MiB
            return float(memory_value[:-2])
    return float(memory_value) if memory_value else np.nan  # Already in MiB

# Load data from database
# Load data from database
def load_data():
    with app.app_context():
        try:
            engine = db.engine
            session = db.session
            query = session.query(PodMetrics).statement
            data = pd.read_sql(f"{query}", con=engine)
            # data = query
            return data
        except Exception as e:
            logger.error(f"Error loading data from database: {e}")
            return None
        
data = load_data()

print(data)

# # Convert CPU and Memory values
# data["cpu_usage"] = data["cpu_usage"].apply(lambda x: convert_cpu(x) if pd.notna(x) else np.nan)
# data["memory_usage"] = data["memory_usage"].apply(lambda x: convert_memory(x) if pd.notna(x) else np.nan)
# data["cpu_request"] = data["cpu_request"].apply(lambda x: convert_cpu(x) if pd.notna(x) else np.nan)
# data["cpu_limit"] = data["cpu_limit"].apply(lambda x: convert_cpu(x) if pd.notna(x) else np.nan)
# data["memory_request"] = data["memory_request"].apply(lambda x: convert_memory(x) if pd.notna(x) else np.nan)
# data["memory_limit"] = data["memory_limit"].apply(lambda x: convert_memory(x) if pd.notna(x) else np.nan)

# # Drop unnecessary columns
# data.drop(columns=["id", "pod_name", "namespace", "container_name", "timestamp"], inplace=True)

# # Fill NaN values with 0 (assumes missing request/limit means unset)
# data.fillna(0, inplace=True)

# # Define features and targets
# X = data[["cpu_usage", "memory_usage"]]  # Features (usage metrics)
# Y = data[["cpu_request", "cpu_limit", "memory_request", "memory_limit"]]  # Targets (requests/limits)

# # Split dataset into training and testing sets
# X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

# # Train Random Forest Regressor
# model = RandomForestRegressor(n_estimators=100, random_state=42)
# model.fit(X_train, Y_train)

# # Predictions
# Y_pred = model.predict(X_test)

# # Evaluate the model
# mae = mean_absolute_error(Y_test, Y_pred)
# r2 = r2_score(Y_test, Y_pred)

# print(f"Mean Absolute Error: {mae}")
# print(f"R² Score: {r2}")
