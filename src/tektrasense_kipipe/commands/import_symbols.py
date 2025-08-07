import logging
import sys
import os
import re
from pathlib import Path
from typing import List # <--- Add this import
from ..db_manager import DatabaseManager
from .. import config

log = logging.getLogger(__name__)

def setup_args(parser):
    """Sets up arguments for the 'import-symbols' command."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Filename of a single .kicad_sym library to import.")
    group.add_argument("-d", "--directory", help="Path to a directory to scan for all .kicad_sym files.")

def run(args):
    """Main logic for the 'import-symbols' command."""
    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        sys.exit(1)

    files_to_process = []

    # --- Logic to handle single file or directory ---
    if args.file:
        file_path = _find_single_file(args.file)
        if file_path:
            files_to_process.append(file_path)
    elif args.directory:
        files_to_process = _find_all_sym_files(args.directory)

    if not files_to_process:
        log.warning("No .kicad_sym files found to process.")
        db_manager.close_all_connections()
        return

    # --- Process all found files ---
    total_summary = {'symbols': 0, 'updated': 0, 'failed': 0}
    for file_path in files_to_process:
        summary = _parse_and_update_db(file_path, db_manager)
        total_summary['symbols'] += summary['symbols']
        total_summary['updated'] += summary['updated']
        total_summary['failed'] += summary['failed']

    log.info(f"--- Import Finished ---")
    log.info(f"Total Symbols Processed: {total_summary['symbols']}")
    log.info(f"Total Added/Updated: {total_summary['updated']}")
    log.info(f"Total Failed: {total_summary['failed']}")
    
    db_manager.close_all_connections()


def _find_single_file(filename: str) -> Path | None:
    """Finds a single file in all configured search paths."""
    for base_path in config.SYMBOL_SEARCH_PATHS:
        potential_path = Path(base_path) / filename
        if potential_path.is_file():
            return potential_path
    log.error(f"File '{filename}' not found in any of the specified library paths.")
    log.error("Please ensure the file exists and the path is configured in 'config.py'.")
    return None

def _find_all_sym_files(directory_path: str) -> List[Path]:
    """Recursively finds all .kicad_sym files in a given directory."""
    found_files = []
    start_path = Path(directory_path)
    if not start_path.is_dir():
        log.error(f"Provided path is not a valid directory: {directory_path}")
        return []
    
    log.info(f"Scanning directory '{start_path}' for .kicad_sym files...")
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.endswith(".kicad_sym"):
                found_files.append(Path(root) / file)
    return found_files

def _parse_and_update_db(file_path: Path, db_manager: DatabaseManager) -> dict:
    """Parses a single .kicad_sym file and updates the database."""
    log.info(f"Processing file: {file_path.name}")
    summary = {'symbols': 0, 'updated': 0, 'failed': 0}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        symbol_definitions = re.findall(r'\(symbol\s+"([^"]+)"(.*?\)\s*\)\s*\))', content, re.DOTALL)

        if not symbol_definitions:
            log.warning(f"No symbols found in {file_path.name}.")
            return summary

        summary['symbols'] = len(symbol_definitions)
        for symbol_name, properties_block in symbol_definitions:
            
            def get_prop(prop_name, default='~'):
                match = re.search(fr'\(property\s+"{prop_name}"\s+"([^"]*)"', properties_block)
                return match.group(1).replace('\n', ' ').strip() if match else default

            description = get_prop("Description", "")
            datasheet = get_prop("Datasheet", "~")
            keywords = get_prop("ki_keywords", "")
            full_keywords = f"{symbol_name} {description} {keywords}".strip()
            
            symbol_data = {
                "library_nickname": file_path.stem,
                "symbol_name": symbol_name,
                "description": description,
                "datasheet": datasheet,
                "keywords": full_keywords
            }
            
            if db_manager.upsert_symbol(symbol_data):
                summary['updated'] += 1
            else:
                summary['failed'] += 1
        
        return summary

    except Exception as e:
        log.critical(f"An error occurred with {file_path.name}: {e}")
        return summary