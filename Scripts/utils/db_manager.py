import os
import psycopg2
from dotenv import load_dotenv

def connect_to_db():
    """Connects to the PostgreSQL database server."""
    load_dotenv() # Load values from .env file
    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return None