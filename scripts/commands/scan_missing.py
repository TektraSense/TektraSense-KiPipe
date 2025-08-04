# scripts/commands/scan_missing.py
import logging
import sys
from ..db_manager import DatabaseManager

log = logging.getLogger(__name__)

def setup_args(parser):
    """Sets up arguments for the 'scan-missing' command."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbol", action="store_true", help="Scan for components missing a symbol.")
    group.add_argument("--footprint", action="store_true", help="Scan for components missing a footprint.")

def run(args):
    """Main logic for the 'scan-missing' command."""
    db_manager = DatabaseManager()
    if not db_manager.connection_pool:
        sys.exit(1)

    column_to_check = ""
    if args.symbol:
        column_to_check = "kicad_symbol"
    elif args.footprint:
        column_to_check = "kicad_footprint"
    
    log.info(f"Scanning for components where '{column_to_check}' is NULL...")
    
    # The f-string is safe here because we control the column_to_check variable
    query = f"SELECT manufacturer_part_number FROM components WHERE {column_to_check} IS NULL ORDER BY manufacturer_part_number"
    
    results = db_manager.fetch_all(query)

    if not results:
        print(f"\n✅ All components have a value for '{column_to_check}'.")
    else:
        print(f"\nFound {len(results)} components missing a '{column_to_check}':")
        for row in results:
            print(f"- {row[0]}")
    
    log.info("Scan complete.")