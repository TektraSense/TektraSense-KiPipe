import logging
import sys
import csv
import pandas as pd

# Import changed slightly to reference the parent folder.
from ..data_processor import ComponentProcessor
from ..db_manager import DatabaseManager

log = logging.getLogger(__name__)

def setup_args(parser):
    """กำหนด Argument ที่ใช้สำหรับคำสั่งย่อย 'fetch'"""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--part-number", help="The manufacturer part number to search for.")
    group.add_argument("--csv", help="Path to CSV file containing part numbers.")
    group.add_argument("--spreadsheet", help="Path to Excel (.xlsx) or ODS (.ods) file containing part numbers.")
    group.add_argument("--txt", help="Path to a plain text file with one part number per line.")
    parser.add_argument("--column", default="part_number", help="Column name for CSV/Spreadsheet. Default: part_number")

def run(args):
    """Logic การทำงานหลักของคำสั่ง 'fetch'"""
    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        log.critical("Database connection pool failed to initialize. Exiting.")
        sys.exit(1)
    
    processor = ComponentProcessor(db_manager)

    if args.part_number:
        _process_part(args.part_number, processor, db_manager)
    elif args.csv:
        _load_from_csv(args.csv, args.column, processor, db_manager)
    elif args.spreadsheet:
        _load_from_spreadsheet(args.spreadsheet, args.column, processor, db_manager)
    elif args.txt:
        _load_from_txt(args.txt, processor, db_manager)

    log.info("Fetch process complete.")
    # Don't close the connection here, main.py will handle it.

# --- Helper Functions (moved from the original main.py) ---
def _process_part(part_number: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    part_number = str(part_number).strip()
    if not part_number or part_number.lower() == "part number":
        return

    result = processor.fetch_part_data(part_number)
    if result:
        log.info(f"Successfully processed data for part: {part_number}")
        for part_data in result:
            db_manager.upsert_data(
                table_name="components",
                pk_column="manufacturer_part_number",
                data=part_data
            )
    else:
        log.warning(f"No data retrieved for part number: {part_number}")

def _load_from_csv(file_path: str, column_name: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    try:
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if column_name not in reader.fieldnames:
                log.error(f"CSV file must contain column: '{column_name}'")
                return
            for row in reader:
                _process_part(row.get(column_name, ''), processor, db_manager)
    except FileNotFoundError:
        log.critical(f"CSV file not found: {file_path}")
    except Exception as e:
        log.critical(f"Failed to read CSV: {e}")

def _load_from_spreadsheet(file_path: str, column_name: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    try:
        engine = "odf" if file_path.endswith(".ods") else None
        df = pd.read_excel(file_path, engine=engine)
        if column_name not in df.columns:
            log.error(f"Spreadsheet must contain column: '{column_name}'")
            return
        for value in df[column_name].dropna().unique():
            _process_part(value, processor, db_manager)
    except FileNotFoundError:
        log.critical(f"Spreadsheet file not found: {file_path}")
    except Exception as e:
        log.critical(f"Failed to read spreadsheet: {e}")

def _load_from_txt(file_path: str, processor: ComponentProcessor, db_manager: DatabaseManager):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                _process_part(line, processor, db_manager)
    except FileNotFoundError:
        log.critical(f"Text file not found: {file_path}")
    except Exception as e:
        log.critical(f"Failed to read text file: {e}")