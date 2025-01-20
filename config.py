import os

class Config:
    """
    Configuration class for the application.

    Attributes:
        SQLALCHEMY_DATABASE_URI (str): The database URI for SQLAlchemy. It is fetched from the environment variable 'DATABASE_URL' 
                                       or defaults to 'sqlite:///statera.db' if the environment variable is not set.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): A flag to disable or enable the modification tracking feature of SQLAlchemy. 
                                               It is set to False to disable tracking modifications.
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///statera.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False