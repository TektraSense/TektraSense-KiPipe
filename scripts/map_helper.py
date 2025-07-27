# map_helper.py
import logging
from db_manager import DatabaseManager

log = logging.getLogger(__name__)

class MappingAssistant:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.internal_categories = {} # To store {id: (name, parent_id)}

    def _load_internal_categories(self):
        """Loads all internal categories from the DB into memory."""
        rows = self.db_manager.fetch_all("SELECT category_id, category_name, parent_id FROM categories ORDER BY parent_id, category_name")
        for row in rows:
            self.internal_categories[row[0]] = {"name": row[1], "parent_id": row[2]}

    def _display_internal_categories(self):
        """Prints a readable, hierarchical list of internal categories."""
        print("\n--- Your Internal Categories ---")
        parents = {cid: data for cid, data in self.internal_categories.items() if data['parent_id'] is None}
        for pid, pdata in parents.items():
            print(f"\n[{pid}] {pdata['name']}")
            children = {cid: data for cid, data in self.internal_categories.items() if data['parent_id'] == pid}
            for cid, cdata in children.items():
                print(f"  - [{cid}] {cdata['name']}")
        print("--------------------------------\n")

    def run(self):
        """Runs the interactive mapping assistant."""
        unmapped_list = self.db_manager.fetch_all("SELECT id, supplier_name, supplier_category FROM unmapped_categories ORDER BY id")
        
        if not unmapped_list:
            print("\nNo unmapped categories found. Your mapping table is up to date!")
            return

        self._load_internal_categories()
        self._display_internal_categories()
        
        for unmapped_id, supplier, sup_cat in unmapped_list:
            print(f"Mapping for: '{sup_cat}' (from {supplier})")
            
            while True:
                user_input = input("Enter the target category_id (or 's' to skip, 'q' to quit): ").strip().lower()

                if user_input == 'q':
                    print("Quitting assistant.")
                    return
                elif user_input == 's':
                    print("Skipping...")
                    break
                
                try:
                    target_id = int(user_input)
                    if target_id not in self.internal_categories:
                        print(f"ERROR: ID {target_id} is not a valid category_id. Please try again.")
                        continue
                    
                    # Add to main mapping table
                    self.db_manager.execute_query(
                        "INSERT INTO category_mappings (supplier_name, supplier_category, category_id) VALUES (%s, %s, %s)",
                        (supplier, sup_cat, target_id)
                    )
                    # Remove from unmapped table
                    self.db_manager.execute_query(
                        "DELETE FROM unmapped_categories WHERE id = %s",
                        (unmapped_id,)
                    )
                    print(f"Success! Mapped '{sup_cat}' to category ID {target_id}.\n")
                    break # Move to the next unmapped category
                    
                except ValueError:
                    print("ERROR: Invalid input. Please enter a number for the ID.")
        
        print("\nAll unmapped categories have been processed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    db = DatabaseManager()
    if db.connection_pool:
        assistant = MappingAssistant(db)
        assistant.run()
        db.close_all_connections()