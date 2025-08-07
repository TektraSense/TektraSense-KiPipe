# scripts/commands/link_footprint.py
import logging
import sys
from ..db_manager import DatabaseManager

log = logging.getLogger(__name__)

def setup_args(parser):
    parser.add_argument("-p", "--part-number", required=True, help="The manufacturer part number to link a footprint to.")

def run(args):
    log.info(f"Linking footprint for part '{args.part_number}'...")
    db_manager = DatabaseManager()

    # 1. Get all approved footprints for this part number
    query = "SELECT footprint_link FROM footprint_mappings WHERE manufacturer_part_number = %s"
    results = db_manager.fetch_all(query, (args.part_number,))
    
    if not results:
        log.warning(f"No approved footprints found for '{args.part_number}'. Use the 'add-footprint' command to teach the system first.")
        return

    approved_footprints = [row[0] for row in results]
    chosen_link = None

    if len(approved_footprints) == 1:
        chosen_link = approved_footprints[0]
        log.info(f"Found exactly one approved footprint: '{chosen_link}'. Linking automatically.")
    else:
        print(f"\nFound multiple approved footprints for '{args.part_number}':")
        for i, fp in enumerate(approved_footprints):
            print(f"  [{i + 1}] {fp}")
        
        while True:
            try:
                choice = input(f"  Please choose the correct footprint (1-{len(approved_footprints)}), or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    print("  Operation cancelled."); return
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(approved_footprints):
                    chosen_link = approved_footprints[choice_index]
                    break
                else: print("  Invalid choice.")
            except ValueError: print("  Invalid input.")
    
    if chosen_link:
        update_query = "UPDATE components SET kicad_footprint = %s WHERE manufacturer_part_number = %s"
        if db_manager.execute_query(update_query, (chosen_link, args.part_number)):
            log.info(f"Successfully linked footprint '{chosen_link}' to component.")