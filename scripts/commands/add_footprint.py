# scripts/commands/add_footprint.py
import logging
import sys
import os
import re
from pathlib import Path
from ..db_manager import DatabaseManager
from .. import config

log = logging.getLogger(__name__)

def setup_args(parser):
    """Sets up arguments for the 'add-footprint' command."""
    parser.add_argument("-p", "--part-number", required=True, help="The manufacturer part number to add a footprint mapping for.")
    parser.add_argument("-f", "--footprint", required=True, help="The KiCad footprint link (e.g., 'LibraryNickname:FootprintName').")

def run(args):
    """Main logic for the 'add-footprint' command with validation."""
    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        sys.exit(1)

    # --- Step 1: Validate that the footprint exists in the filesystem ---
    footprint_exists, found_path = _verify_footprint_exists(args.footprint)
    
    if not footprint_exists:
        log.error(f"Validation FAILED: Footprint '{args.footprint}' could not be found in any of the library paths.")
        log.error("Mapping was NOT added to the database. Please check the footprint name and your library files.")
        db_manager.close_all_connections()
        return

    log.info(f"Validation PASSED: Found footprint '{args.footprint}' in file '{found_path}'.")

    # --- Step 2: Add the validated footprint to the mapping table ---
    log.info(f"Adding new approved footprint '{args.footprint}' for part '{args.part_number}'...")
    
    query = "INSERT INTO footprint_mappings (manufacturer_part_number, footprint_link) VALUES (%s, %s) ON CONFLICT DO NOTHING"
    success = db_manager.execute_query(query, (args.part_number, args.footprint))
    
    if success:
        log.info("Successfully added new footprint mapping to the catalog.")
    else:
        log.error("Failed to add footprint mapping (it might already exist or there was a DB error).")

    db_manager.close_all_connections()


def _verify_footprint_exists(footprint_link: str) -> (bool, str):
    """
    Verifies if a footprint exists in the .kicad_mod files.
    Returns (True, path_to_file) if found, otherwise (False, None).
    """
    try:
        nickname, fp_name = footprint_link.split(':', 1)
    except ValueError:
        log.error(f"Invalid footprint link format: '{footprint_link}'. Expected 'LibraryNickname:FootprintName'.")
        return False, None

    # We expect the library nickname to correspond to a .kicad_mod file name
    # e.g., nickname 'Resistor_SMD' -> file 'Resistor_SMD.kicad_mod'
    library_filename = f"{nickname}.kicad_mod"

    for base_path in config.FOOTPRINT_SEARCH_PATHS:
        for root, dirs, files in os.walk(base_path):
            if library_filename in files:
                file_path = Path(root) / library_filename
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Search for '(footprint "FootprintName"'
                        if re.search(fr'\(footprint\s+"{re.escape(fp_name)}"', content):
                            return True, str(file_path)
                except Exception as e:
                    log.error(f"Could not read or parse file {file_path}: {e}")
                    return False, None
    
    return False, None