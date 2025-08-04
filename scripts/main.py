# scripts/main.py
import argparse
import sys
import logging
from .db_manager import DatabaseManager
from .commands import fetch, map_categories, add_symbol, scan_missing, import_symbols, add_footprint, link_footprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log = logging.getLogger(__name__)

def main():
    log.info("Application starting...")
    db_manager = DatabaseManager()

    if not db_manager.connection_pool:
        log.critical("Database connection pool failed to initialize. Exiting.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="KiCad Component Pipeline CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Setup for 'fetch' command ---
    parser_fetch = subparsers.add_parser("fetch", help="Fetch component data from APIs.")
    fetch.setup_args(parser_fetch)

    # --- Setup for 'map-categories' command ---
    parser_map = subparsers.add_parser("map-categories", help="Run the interactive category mapping assistant.")
    
    # --- Setup for 'add-symbol' command ---
    parser_add_symbol = subparsers.add_parser("add-symbol", help="Find and link a KiCad symbol to a component.")
    add_symbol.setup_args(parser_add_symbol)

    # --- Setup for 'scan-missing' command ---
    parser_scan = subparsers.add_parser("scan-missing", help="Scan database for components missing data.")
    scan_missing.setup_args(parser_scan)

    # --- Setup for 'import-symbols' command (ส่วนที่เพิ่ม) ---
    parser_import = subparsers.add_parser("import-symbols", help="Parse a .kicad_sym file and import/update symbols in the database.")
    import_symbols.setup_args(parser_import)

     # --- Setup for 'add-footprint' command ---
    parser_add_fp = subparsers.add_parser("add-footprint", help="Teach the system a new valid footprint for a part.")
    add_footprint.setup_args(parser_add_fp)

    # --- Setup for 'link-footprint' command ---
    parser_link_fp = subparsers.add_parser("link-footprint", help="Choose from approved footprints to link to a component.")
    link_footprint.setup_args(parser_link_fp)

    args = parser.parse_args()

    # --- Call the appropriate run function based on the command ---
    if args.command == "fetch":
        fetch.run(args)
    elif args.command == "map-categories":
        map_categories.run(args)
    elif args.command == "add-symbol":
        add_symbol.run(args)
    elif args.command == "scan-missing":
        scan_missing.run(args)
    elif args.command == "import-symbols": # <--- เพิ่มเงื่อนไขนี้
        import_symbols.run(args)
    elif args.command == "add-footprint":
        add_footprint.run(args)
    elif args.command == "link-footprint":
        link_footprint.run(args)
    

    log.info("Process complete. Closing connections.")
    db_manager.close_all_connections()

if __name__ == "__main__":
    main()