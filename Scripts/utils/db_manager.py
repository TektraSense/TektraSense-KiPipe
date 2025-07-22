# scripts/utils/db_manager.py
import os
import psycopg2
from dotenv import load_dotenv

def connect_to_db():
    """Connects to the PostgreSQL database server."""
    load_dotenv()
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database connection error: {error}")
        return None

def upsert_component(conn, part_data: dict):
    """
    Insert or update a component in the components table.
    This is an UPSERT operation.
    """
    sql = """
        INSERT INTO components (
            manufacturer_part_number, manufacturer, description, datasheet_url,
            product_status, package_case, mounting_type
        )
        VALUES (
            %(manufacturer_part_number)s, %(manufacturer)s, %(description)s,
            %(datasheet_url)s, %(product_status)s, %(package_case)s,
            %(mounting_type)s
        )
        ON CONFLICT (manufacturer_part_number) DO UPDATE SET
            manufacturer = EXCLUDED.manufacturer,
            description = EXCLUDED.description,
            datasheet_url = EXCLUDED.datasheet_url,
            product_status = EXCLUDED.product_status,
            package_case = EXCLUDED.package_case,
            mounting_type = EXCLUDED.mounting_type,
            lastupdated = NOW();
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, part_data)
        conn.commit()
        print(f"Successfully upserted part: {part_data['manufacturer_part_number']}")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database upsert error: {error}")
        conn.rollback()