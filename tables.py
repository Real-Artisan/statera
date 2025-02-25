from models import db
from database import create_app

app = create_app()

def create_tables():
    with app.app_context():
        try:
            # Check if the database is initialized and tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            required_tables = ['pod_metrics']
            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                db.create_all()
                print(f"Database tables created: {', '.join(missing_tables)}.")
            else:
                print("All required database tables already exist.")
        except Exception as e:
            print(f"Error initializing database: {e}")