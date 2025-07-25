# scripts/db_operations.py (ตัวอย่างชื่อไฟล์ใหม่)
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# --- 1. PROFESSIONAL: Connection Pooling ---
# สร้าง Pool ของ Connection ไว้ที่ระดับ Module เพื่อใช้ร่วมกัน
# โดยจะถูกสร้างแค่ครั้งเดียวตอนที่ import ไฟล์นี้
try:
    load_dotenv()
    connection_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,  # กำหนดจำนวน Connection สูงสุดที่ต้องการ
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    print("Database connection pool created successfully.")
except (Exception, psycopg2.DatabaseError) as error:
    print(f"Error while creating connection pool: {error}")
    connection_pool = None

def upsert_component(part_data: dict):
    """
    Insert or update a component using a connection from the pool.
    The SQL query is generated dynamically based on the input dictionary's keys.
    """
    if not connection_pool:
        print("Database pool not available. Skipping upsert.")
        return

    # --- CRAFTSMAN: Dynamic SQL Generation ---
    # ทำให้ไม่ต้อง hardcode ชื่อคอลัมน์อีกต่อไป
    # 1. สร้างลิสต์ของคอลัมน์จาก keys ของ dictionary
    columns = part_data.keys()
    columns_str = ", ".join(columns)

    # 2. สร้างส่วนของ VALUES แบบไดนามิก
    values_str = ", ".join([f"%({col})s" for col in columns])

    # 3. สร้างส่วนของ UPDATE SET แบบไดนามิก
    # ไม่ต้องอัปเดต primary key (manufacturer_part_number)
    update_columns = [col for col in columns if col != 'manufacturer_part_number']
    update_str = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
    
    # 4. ประกอบร่าง SQL ทั้งหมด
    sql = f"""
        INSERT INTO components ({columns_str})
        VALUES ({values_str})
        ON CONFLICT (manufacturer_part_number) DO UPDATE SET
            {update_str},
            lastupdated = NOW();
    """

    conn = None
    try:
        # PROFESSIONAL: "ยืม" connection จาก pool
        conn = connection_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, part_data)
        conn.commit()
        print(f"Successfully upserted part: {part_data.get('manufacturer_part_number')}")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database upsert error for '{part_data.get('manufacturer_part_number')}': {error}")
        if conn:
            conn.rollback()
            
    finally:
        # PROFESSIONAL: "คืน" connection กลับเข้า pool เสมอ ไม่ว่าจะสำเร็จหรือล้มเหลว
        if conn:
            connection_pool.putconn(conn)

# --- ตัวอย่างการเรียกใช้งาน ---
# ที่ไฟล์หลักของคุณ (เช่น fetch_parts.py) คุณจะ import และเรียกใช้แบบนี้
# from scripts.db_operations import upsert_component, connection_pool
#
# def main():
#     # ... โค้ด fetch data ของคุณ ...
#     if list_of_parts:
#         for part in list_of_parts:
#             upsert_component(part) # << เรียกใช้ฟังก์ชันที่ refactor แล้ว
#
#     # เมื่อแอปพลิเคชันจะปิดตัวลง ก็ควรปิด Pool ด้วย
#     if connection_pool:
#         connection_pool.closeall()
#         print("Database connection pool closed.")
#
# if __name__ == "__main__":
#     main()