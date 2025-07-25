import os
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2 import pool
from dotenv import load_dotenv
from typing import Dict, Any, Iterator, List

log = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and operations using a connection pool.
    This class is designed to be reusable and robust.
    """
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
        """A context manager to safely get and return a connection from the pool."""
        if not self.connection_pool:
            raise IOError("Connection pool is not available.")
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def _build_upsert_query(self, table_name: str, data: Dict[str, Any], pk_column: str) -> str:
        """
        Private helper method to dynamically build a robust upsert SQL query.
        This separates query construction from execution logic.
        """
        columns = data.keys()
        
        # Use quotes around identifiers for safety against reserved keywords or special chars.
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
        """
        Inserts or updates a single record in any specified table.
        This method is now highly reusable.
        """
        sql = self._build_upsert_query(table_name, data, pk_column)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, data)
                conn.commit()
            log.info(f"Successfully upserted record into '{table_name}' with PK: {data.get(pk_column)}")
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(f"Database upsert error for PK '{data.get(pk_column)}' in table '{table_name}': {error}")
            # While the 'with' block would handle rollback on exit,
            # an explicit rollback here makes the intent crystal clear.
            if 'conn' in locals() and conn:
                conn.rollback()

    def close_all_connections(self):
        """Closes all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            log.info("Database connection pool closed.")