import os
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2 import pool
from dotenv import load_dotenv
from typing import Dict, Any, Iterator, Optional, Tuple

log = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        load_dotenv()
        self.connection_pool = None
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                minconn=1, maxconn=5,
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            log.info("Database connection pool created successfully.")
        except (Exception, psycopg2.DatabaseError) as error:
            log.critical(f"Fatal error: Could not create connection pool: {error}")

    @contextmanager
    def get_connection(self) -> Iterator[psycopg2.extensions.connection]:
        if not self.connection_pool:
            raise IOError("Connection pool is not available.")
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def _build_upsert_query(self, table_name: str, data: Dict[str, Any], pk_column: str) -> str:
        columns = data.keys()
        quoted_columns = ", ".join(f'"{col}"' for col in columns)
        placeholders = ", ".join(f"%({col})s" for col in columns)
        update_columns = [col for col in columns if col != pk_column]
        update_assignments = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])
        
        return f"""
            INSERT INTO {table_name} ({quoted_columns})
            VALUES ({placeholders})
            ON CONFLICT ({pk_column}) DO UPDATE SET
                {update_assignments},
                lastupdated = NOW();
        """

    def upsert_data(self, table_name: str, pk_column: str, data: Dict[str, Any]):
        sql = self._build_upsert_query(table_name, data, pk_column)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, data)
                conn.commit()
            log.info(f"Successfully upserted record into '{table_name}' with PK: {data.get(pk_column)}")
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Database upsert error for PK '{data.get(pk_column)}' in table '{table_name}': {error}")
            if 'conn' in locals() and conn:
                conn.rollback()

    # --- ฟังก์ชันที่เพิ่มเข้ามาใหม่ ---
    def get_category_id(self, supplier_name: str, supplier_category: str) -> Optional[int]:
        """Finds the internal category_id from the mappings table."""
        sql = "SELECT category_id FROM category_mappings WHERE supplier_name = %s AND supplier_category = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (supplier_name, supplier_category))
                    result = cur.fetchone()
                    return result[0] if result else None
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Error fetching category_id: {error}")
            return None

    def get_category_details(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Gets category details (parent_id, name, prefix) from the master categories table."""
        # เพิ่ม parent_id เข้าไปในคำสั่ง SELECT
        sql = "SELECT parent_id, category_name, category_prefix FROM categories WHERE category_id = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (category_id,))
                    result = cur.fetchone()
                    if result:
                        # เพิ่ม parent_id เข้าไปใน dictionary ที่ส่งกลับไป
                        return {"parent_id": result[0], "name": result[1], "prefix": result[2]}
                    return None
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Error fetching category details for id {category_id}: {error}")
            return None

    def get_next_internal_part_id(self, prefix: str) -> str:
        """Generates the next sequential internal_part_id for a given prefix."""
        # This is a simple implementation. For high concurrency, a sequence or a
        # dedicated table might be better.
        sql = "SELECT internal_part_id FROM components WHERE internal_part_id LIKE %s ORDER BY internal_part_id DESC LIMIT 1"
        like_pattern = f"{prefix}-%"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (like_pattern,))
                    last_id = cur.fetchone()
                    if last_id:
                        last_seq = int(last_id[0].split('-')[-1])
                        next_seq = last_seq + 1
                    else:
                        next_seq = 1
                    return f"{prefix}-{next_seq:04d}" # Formats to 4 digits, e.g., 0001
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Error generating next internal_part_id for prefix {prefix}: {error}")
            return f"{prefix}-0001" # Fallback

    def close_all_connections(self):
        if self.connection_pool:
            self.connection_pool.closeall()
            log.info("Database connection pool closed.")

    # ในคลาส DatabaseManager ของไฟล์ db_manager.py
    def add_unmapped_category(self, supplier_name: str, supplier_category: str):
        """Adds a new, unknown category to the unmapped_categories table for review."""
        # ON CONFLICT DO NOTHING จะป้องกันการเพิ่มข้อมูลซ้ำซ้อน
        sql = """
            INSERT INTO unmapped_categories (supplier_name, supplier_category)
            VALUES (%s, %s)
            ON CONFLICT (supplier_category) DO NOTHING;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (supplier_name, supplier_category))
                conn.commit()
            log.info(f"Logged new unmapped category for review: '{supplier_category}' from {supplier_name}")
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Error logging unmapped category: {error}")
            if 'conn' in locals() and conn:
                conn.rollback()