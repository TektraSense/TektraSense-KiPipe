import argparse
import sys
import logging
import csv
import pandas as pd
from data_processor import ComponentProcessor
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log = logging.getLogger(__name__)

def process_part(part_number: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    part_number = str(part_number).strip()
    if not part_number or part_number.lower() == "part number":
        return

    result = processor.fetch_part_data(part_number)
    if result:
        log.info(f"Successfully fetched data for {len(result)} part(s): {part_number}")
        for part_data in result:
            db_manager.upsert_data(
                table_name="components",
                pk_column="manufacturer_part_number",
                data=part_data
            )
    else:
        log.warning(f"No data found for part number: {part_number}")

def load_from_csv(file_path: str, column_name: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    try:
        with open(file_path, newline='') as f:
            reader = csv.DictReader(f)
            if column_name not in reader.fieldnames:
                log.error(f"CSV file must contain column: '{column_name}'")
                sys.exit(1)
            for row in reader:
                process_part(row.get(column_name, ''), processor, db_manager)
    except FileNotFoundError:
        log.critical(f"CSV file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        log.critical(f"Failed to read CSV: {e}")
        sys.exit(1)

def load_from_spreadsheet(file_path: str, column_name: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    try:
        engine = "odf" if file_path.endswith(".ods") else None
        df = pd.read_excel(file_path, engine=engine)

        if column_name not in df.columns:
            log.error(f"Spreadsheet must contain column: '{column_name}'")
            sys.exit(1)

        for value in df[column_name].dropna().unique():
            process_part(value, processor, db_manager)
    except FileNotFoundError:
        log.critical(f"Spreadsheet file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        log.critical(f"Failed to read spreadsheet: {e}")
        sys.exit(1)

def main():
    log.info("Application starting...")

    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        log.critical("Database connection pool failed to initialize. Exiting.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Fetch component data from supplier APIs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--part-number", help="The manufacturer part number to search for.")
    group.add_argument("--csv", help="Path to CSV file containing part numbers.")
    group.add_argument("--spreadsheet", help="Path to Excel (.xlsx) or ODS (.ods) file containing part numbers.")
    parser.add_argument("--column", default="part_number", help="Column name containing part numbers. Default: part_number")

    args = parser.parse_args()
    processor = ComponentProcessor(db_manager)

    if args.part_number:
        process_part(args.part_number, processor, db_manager)
    elif args.csv:
        load_from_csv(args.csv, args.column, processor, db_manager)
    elif args.spreadsheet:
        load_from_spreadsheet(args.spreadsheet, args.column, processor, db_manager)

    log.info("Process complete. Closing connections.")
    db_manager.close_all_connections()

if __name__ == "__main__":
    main()
