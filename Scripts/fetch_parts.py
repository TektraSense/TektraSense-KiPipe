# scripts/fetch_parts.py
import argparse
import sys
# ✅ 1. แก้ไข import: นำเข้า connection_pool เพื่อใช้ปิดตอนท้าย
# แก้จาก db_operations กลับไปเป็น db_manager
from utils.db_manager import upsert_component, connection_pool
from utils.api_clients import fetch_part_data

def main():
    """
    Main function to fetch one or more component data from APIs
    and load them into the database.
    """
    parser = argparse.ArgumentParser(description="Fetch KiCad component data from supplier APIs.")
    parser.add_argument("-p", "--part-number", required=True, help="The manufacturer part number to search for.")
    args = parser.parse_args()

    list_of_parts = fetch_part_data(args.part_number)

    if not list_of_parts:
        print("Could not retrieve any data for the specified part number. Exiting.")
        sys.exit(1)

    print(f"\n--- API Data Fetched Successfully: Found {len(list_of_parts)} part(s) ---")
    
    # ❗ 2. ลบบรรทัด conn = connect_to_db() ออกไปเลย
    
    # ตรวจสอบว่า connection pool ถูกสร้างสำเร็จหรือไม่
    if connection_pool:
        for part_data in list_of_parts:
            print(f"\nProcessing part: {part_data.get('manufacturer_part_number')}")
            # ✅ 3. เรียกใช้ upsert_component โดยไม่ต้องส่ง conn เข้าไป
            upsert_component(part_data)
        
        # ✅ 4. เปลี่ยน conn.close() เป็นการปิด pool ทั้งหมดเมื่อจบโปรแกรม
        connection_pool.closeall()
        print("\nDatabase connection pool closed.")
    else:
        print("\nCould not connect to the database. Skipping data upsert.")

if __name__ == '__main__':
    main()