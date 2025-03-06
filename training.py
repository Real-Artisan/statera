# train_model.py
import numpy as np
import pandas as pd
import joblib
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from database import create_app
from models import db, PodMetrics
from preprocess import preprocess_value

app = create_app()

def train_model():
    with app.app_context():
        data = PodMetrics.query.all()
        print(f"Toatal records in DB: {len(data)}")

        # Convert database objects to a DataFrame
        df = pd.DataFrame([
            {
                "cpu_usage": preprocess_value(d.cpu_usage),
                "memory_usage": preprocess_value(d.memory_usage),
                "cpu_request": preprocess_value(d.cpu_request),
                "cpu_limit": preprocess_value(d.cpu_limit),
                "memory_request": preprocess_value(d.memory_request),
                "memory_limit": preprocess_value(d.memory_limit)
            }
            for d in data
        ])

        print(f"Raw Data before processing: \n", df)
        df.dropna()
        print(f"Data after processing: \n", df)
        print(df.dtypes)
        print("Final Training Data Shape:", df.shape)
        print("Final Training Data Preview:\n", df.head())
        # Ensure data is valid
        if df.empty:
            print("No valid data for training.")
            return None

        # Define features (X) and targets (y)
        X = df[["cpu_usage", "memory_usage"]]
        y = df[["cpu_request", "cpu_limit", "memory_request", "memory_limit"]]

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Decision Tree model
        model = DecisionTreeRegressor()
        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"Model Performance:\n MAE: {mae}\n MSE: {mse}\n R² Score: {r2}")

        # Save model
        joblib.dump(model, "model.pkl")
        print("Model saved as model.pkl")

        return model

train_model()