# scripts/fetch_parts.py
import argparse
import sys
from utils.db_manager import connect_to_db
from utils.api_clients import fetch_part_data

def main():
    """
    Main function to fetch component data from an API
    and prepare it for database insertion.
    """
    parser = argparse.ArgumentParser(
        description="Fetch KiCad component data from supplier APIs."
    )
    parser.add_argument(
        "-p", "--part-number",
        required=True,
        help="The manufacturer part number to search for."
    )
    args = parser.parse_args()

    part_data = fetch_part_data(args.part_number)

    if not part_data:
        print("Could not retrieve data for the specified part number. Exiting.")
        sys.exit(1)

    print("\n--- API Data Fetched Successfully ---")
    for key, value in part_data.items():
        print(f"  {key}: {value}")
    print("-----------------------------------")
    
    # --- Database Connection (Step for the future) ---
    # print("\nConnecting to database to load data...")
    # conn = connect_to_db()
    # if conn:
    #     # TODO: Add logic to load `part_data` into the database
    #     print("Data loading logic will be implemented here.")
    #     conn.close()
    #     print("Database connection closed.")


if __name__ == '__main__':
    main()