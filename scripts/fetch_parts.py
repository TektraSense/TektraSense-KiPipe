# fetch_parts.py
import argparse
import sys
import logging
import json
from data_processor import ComponentProcessor
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def main():
    log.info("Application starting...")
    db_manager = DatabaseManager()

    if not db_manager.connection_pool:
        log.critical("Database connection pool failed to initialize. Exiting.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Fetch component data from supplier APIs.")
    parser.add_argument("-p", "--part-number", required=True, help="The manufacturer part number to search for.")
    args = parser.parse_args()

    processor = ComponentProcessor(db_manager)
    list_of_parts = processor.fetch_part_data(args.part_number)
    
    if list_of_parts:
        log.info(f"Successfully fetched data for {len(list_of_parts)} part(s).")
        for part_data in list_of_parts:
            db_manager.upsert_data(
                table_name="components",
                pk_column="manufacturer_part_number",
                data=part_data
            )
    else:
        log.warning(f"Could not retrieve any data for part number: {args.part_number}")

    log.info("Process complete. Closing connections.")
    db_manager.close_all_connections()

if __name__ == "__main__":
    main()