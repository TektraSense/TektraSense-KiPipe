import logging
import sys
import os
import re
import csv
import pandas as pd
from pathlib import Path
from ..db_manager import DatabaseManager
from .. import config

log = logging.getLogger(__name__)

def setup_args(parser):
    """Sets up arguments for the 'add-symbol' command."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--part-number", help="A single manufacturer part number to find and link a symbol for.")
    group.add_argument("--csv", help="Path to CSV file with part numbers for bulk processing.")
    group.add_argument("--spreadsheet", help="Path to Excel/ODS file with part numbers for bulk processing.")
    group.add_argument("--txt", help="Path to a plain text file with one part number per line.")
    
    parser.add_argument("--col-part", default="Part Number", help="Column name for part numbers in a file. Default: 'Part Number'")
    parser.add_argument("--force", action="store_true", help="Force overwrite if a symbol already exists.")

def run(args):
    """Main logic for the 'add-symbol' command."""
    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        sys.exit(1)

    part_numbers = []
    if args.part_number:
        part_numbers.append(args.part_number)
    else: # Bulk modes
        part_numbers = _load_parts_from_file(args.csv, args.spreadsheet, args.txt, args.col_part)

    for pn in part_numbers:
        is_interactive_mode = bool(args.part_number)
        _find_and_link_symbol(pn, args.force, db_manager, is_interactive=is_interactive_mode)

    log.info("Add symbol process complete.")

def _verify_symbol_exists(symbol_link: str) -> bool:
    """
    Verifies if a symbol exists within its corresponding .kicad_sym file.
    """
    try:
        nickname, symbol_name = symbol_link.split(':', 1)
    except ValueError:
        log.error(f"Invalid symbol link format: '{symbol_link}'.")
        return False

    library_filename = f"{nickname}.kicad_sym"

    for base_path in config.SYMBOL_SEARCH_PATHS:
        for root, dirs, files in os.walk(base_path):
            if library_filename in files:
                file_path = Path(root) / library_filename
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Search for '(symbol "SymbolName"'
                        if re.search(fr'\(symbol\s+"{re.escape(symbol_name)}"', content):
                            log.info(f"Validation PASSED: Found symbol '{symbol_link}' in file '{file_path}'.")
                            return True
                except Exception as e:
                    log.error(f"Could not read or parse file {file_path}: {e}")
                    return False
    
    log.warning(f"Validation FAILED: Library file '{library_filename}' not found for symbol link '{symbol_link}'.")
    return False

def _find_and_link_symbol(part_number: str, force: bool, db_manager: DatabaseManager, is_interactive: bool):
    part_number = str(part_number).strip()
    if not part_number: return

    component_info = db_manager.get_component_symbol_info(part_number)
    if not component_info:
        log.error(f"Part '{part_number}' not found in DB. Please run 'fetch' first.")
        return

    description, existing_symbol = component_info
    if existing_symbol and not force:
        log.warning(f"Part '{part_number}' already has symbol '{existing_symbol}'. Use --force to overwrite.")
        return

    log.info(f"Searching for best symbol match for '{part_number}'...")
    
    all_symbols_raw = db_manager.fetch_all("SELECT library_nickname, symbol_name FROM symbols")
    if not all_symbols_raw:
        log.warning("The 'symbols' table is empty. Please import symbols first.")
        return

    best_match_len = 0
    found_symbols = []

    for nickname, symbol_name in all_symbols_raw:
        clean_s_name = re.sub(r'^[A-Z]+_', '', symbol_name)
        clean_s_name = re.sub(r'_[A-Z]$', '', clean_s_name)
        clean_s_name = clean_s_name.replace('x', '').replace('X', '')

        common_prefix_len = 0
        for i in range(min(len(clean_s_name), len(part_number))):
            if clean_s_name[i] == part_number[i]:
                common_prefix_len += 1
            else:
                break
        
        if common_prefix_len < 5:
            continue

        if common_prefix_len > best_match_len:
            best_match_len = common_prefix_len
            found_symbols = [{"nickname": nickname, "symbol": symbol_name}]
        elif common_prefix_len == best_match_len:
            found_symbols.append({"nickname": nickname, "symbol": symbol_name})

    if not found_symbols:
        log.warning(f"No potential symbols found in the database for '{part_number}'.")
        return

    chosen_link = None
    if len(found_symbols) == 1 and not is_interactive:
        chosen_symbol = found_symbols[0]
        chosen_link = f"{chosen_symbol['nickname']}:{chosen_symbol['symbol']}"
        log.info(f"Found exactly one match: '{chosen_link}'.")
    elif is_interactive:
        print(f"\n> For Component: \"{description}\"")
        print(f"  Found potential symbols (best match length: {best_match_len}):")
        for i, sym in enumerate(found_symbols):
            print(f"    [{i + 1}] {sym['nickname']}:{sym['symbol']}")
        
        while True:
            try:
                choice = input(f"  Please choose the correct symbol (1-{len(found_symbols)}), or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    print("  Skipping part number."); return
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(found_symbols):
                    chosen_symbol = found_symbols[choice_index]
                    chosen_link = f"{chosen_symbol['nickname']}:{chosen_symbol['symbol']}"
                    break
                else: print("  Invalid choice.")
            except ValueError: print("  Invalid input.")
    else:
        log.warning(f"Ambiguous symbol for '{part_number}'. Found {len(found_symbols)} matches. Please resolve manually with '-p {part_number}'.")
        return

    if chosen_link:
        # --- Final Validation Step ---
        if _verify_symbol_exists(chosen_link):
            _update_symbol_in_db(part_number, chosen_link, db_manager)
        else:
            log.error(f"Final check failed. The selected symbol '{chosen_link}' does not seem to exist in the library files.")


def _update_symbol_in_db(part_number, link_string, db_manager):
    update_query = "UPDATE components SET kicad_symbol = %s WHERE manufacturer_part_number = %s"
    if db_manager.execute_query(update_query, (link_string, part_number)):
        log.info(f"Successfully linked symbol '{link_string}' to part '{part_number}'.")

def _load_parts_from_file(csv_path, spreadsheet_path, txt_path, col_part):
    try:
        if csv_path:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if col_part not in reader.fieldnames:
                    log.error(f"CSV must contain column: '{col_part}'"); return []
                return [row.get(col_part) for row in reader]
        elif spreadsheet_path:
            engine = "odf" if spreadsheet_path.endswith(".ods") else None
            df = pd.read_excel(spreadsheet_path, engine=engine)
            if col_part not in df.columns:
                log.error(f"Spreadsheet must contain column: '{col_part}'"); return []
            return df[col_part].dropna().unique()
        elif txt_path:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f]
    except Exception as e:
        log.critical(f"Failed to process file: {e}")
    return []