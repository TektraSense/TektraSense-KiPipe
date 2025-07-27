# data_processor.py
"""
Main data processing and orchestration logic.
Contains the ComponentProcessor class.
"""
import json
import logging
import re
from typing import Optional, List, Dict, Any
import config
import supplier_apis
from db_manager import DatabaseManager

log = logging.getLogger(__name__)

class ComponentProcessor:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        keys = path.split('.')
        current_level = data
        for key in keys:
            if isinstance(current_level, dict): current_level = current_level.get(key)
            elif isinstance(current_level, list) and key.isdigit():
                try: current_level = current_level[int(key)]
                except (ValueError, IndexError): return None
            else: return None
        return current_level

    def _find_param_in_list(self, parameters: Optional[List[Dict[str, str]]], *param_names: str) -> Optional[str]:
        if not parameters: return None
        return next((p.get('ValueText') or p.get('AttributeValue') for p in parameters if (p.get('ParameterText') or p.get('AttributeName')) in param_names and (p.get('ValueText') or p.get('AttributeValue')) != '-'), None)

    def _normalize_rohs_status(self, status: Optional[str]) -> str:
        return "Yes" if status and "rohs" in status.lower() else "No"

    def _get_category_path_from_object(self, category_obj: Optional[Dict[str, Any]]) -> List[str]:
        if not isinstance(category_obj, dict): return []
        name = category_obj.get("Name", "")
        children = category_obj.get("ChildCategories")
        if not children: return [name]
        return [name] + self._get_category_path_from_object(children[0])

    def _apply_formatting_recipes(self, part_data: Dict[str, Any], category_details: Dict[str, Any], category_path: List[str]) -> Dict[str, Any]:
        params = part_data.get("parameters_list", [])
        def find_param(*param_names):
            return self._find_param_in_list(params, *param_names)

        for recipe in config.CATEGORY_RECIPES:
            if recipe["trigger"](category_path):
                params_to_find = recipe["description_params"](category_path)
                desc_details = [recipe["description_prefix"](category_path)]
                desc_details.extend(find_param(p) for p in params_to_find)
                part_data["description"] = ", ".join(filter(None, desc_details))
                try:
                    part_data["component_value"] = recipe["value_generator"](find_param, category_path)
                except (TypeError, AttributeError): pass
                if not part_data.get("component_value"):
                    part_data["component_value"] = part_data.get("manufacturer_part_number")
                return part_data
        
        if not part_data.get("description"):
            part_data["description"] = part_data.get("description")
        if not part_data.get("component_value"):
            part_data["component_value"] = part_data.get("manufacturer_part_number")
        return part_data

    def _process_and_format_data(self, raw_part: Dict[str, Any], mapper: Dict[str, Any], category_id: int) -> Optional[Dict[str, Any]]:
        part_data = {std_field: self._get_nested_value(raw_part, sup_field) for std_field, sup_field in mapper.items()}
        part_data['category_id'] = category_id
        
        category_details = self.db_manager.get_category_details(category_id)
        if not category_details:
            log.error(f"Could not find details for category_id {category_id}")
            return None

        parent_details = self.db_manager.get_category_details(category_details['parent_id']) if category_details.get('parent_id') else None
        full_prefix = category_details['prefix']
        if parent_details:
            full_prefix = f"{parent_details['prefix']}-{full_prefix}"
        part_data['internal_part_id'] = self.db_manager.get_next_internal_part_id(full_prefix)

        category_path = self._get_category_path_from_object(part_data.get("supplier_category_object"))
        part_data = self._apply_formatting_recipes(part_data, category_details, category_path)

        part_data["rohs_status"] = self._normalize_rohs_status(part_data.get("rohs_status"))
        price_breaks = []
        for price in part_data.get("pricing_list") or []:
            quantity = price.get('BreakQuantity') or price.get('Quantity')
            unit_price = str(price.get('UnitPrice') or price.get('Price', '')).replace('$', '')
            if quantity is not None and unit_price: price_breaks.append(f"{quantity}:{unit_price}")
        
        parameters_json = {"availability": part_data.get('quantity_available'), "price_breaks_usd": ", ".join(price_breaks)}
        part_data['parameters'] = json.dumps(parameters_json)
        
        params_list = part_data.get("parameters_list", [])
        part_data["package_case"] = self._find_param_in_list(params_list, "Package / Case")
        
        mount_type = self._find_param_in_list(params_list, "Mounting Type")
        part_data["mounting_type"] = None
        if isinstance(mount_type, str):
            if "surface mount" in mount_type.lower(): part_data["mounting_type"] = "Surface Mount"
            elif "through-hole" in mount_type.lower() or "through hole" in mount_type.lower(): part_data["mounting_type"] = "Through-Hole"
        if not part_data.get("mounting_type"):
            path_str = " ".join(category_path).lower()
            if "surface mount" in path_str: part_data["mounting_type"] = "Surface Mount"
            elif "through-hole" in path_str or "through hole" in path_str: part_data["mounting_type"] = "Through-Hole"
        
        temp_str = self._find_param_in_list(params_list, "Operating Temperature", "Operating Temperature - Junction")
        if isinstance(temp_str, str):
            part_data["operating_temperature"] = re.sub(r"\s*\([^)]*\)", "", temp_str).strip()
        else:
            part_data["operating_temperature"] = None
        
        part_data.pop("pricing_list", None)
        part_data.pop("parameters_list", None)
        part_data.pop("quantity_available", None)
        part_data.pop("supplier_category", None)
        part_data.pop("supplier_category_object", None)
        
        return part_data

    def fetch_part_data(self, part_number: str) -> Optional[List[Dict[str, Any]]]:
        log.info(f"Orchestrator: Starting search for '{part_number}'...")

        digikey_raw = supplier_apis.call_digikey_api(part_number)
        mouser_raw = supplier_apis.call_mouser_api(part_number)

        if not digikey_raw and not mouser_raw:
            log.warning(f"Orchestrator: Part '{part_number}' not found on any supplier.")
            return None

        # Step 1: Find a valid Category ID, prioritizing Digi-Key
        category_id = None
        dk_cat_name, mouser_cat_name = None, None

        if digikey_raw:
            dk_cat_obj = self._get_nested_value(digikey_raw, config.DIGIKEY_MAPPER['supplier_category_object'])
            dk_cat_name = self._get_nested_value(dk_cat_obj, "Name")
            if dk_cat_name:
                category_id = self.db_manager.get_category_id("Digi-Key", dk_cat_name)

        if not category_id and mouser_raw:
            mouser_cat_name = self._get_nested_value(mouser_raw, config.MOUSER_MAPPER['supplier_category'])
            if mouser_cat_name:
                log.info("Borrowing category from Mouser...")
                category_id = self.db_manager.get_category_id("Mouser", mouser_cat_name)

        if not category_id:
            log.warning(f"No valid category mapping found for '{part_number}'. Logging for review.")
            if dk_cat_name: self.db_manager.add_unmapped_category("Digi-Key", dk_cat_name)
            if mouser_cat_name: self.db_manager.add_unmapped_category("Mouser", mouser_cat_name)
            return None

        # Step 2: Process the data, ALWAYS prioritizing Digi-Key's raw data if it exists
        base_raw_data = digikey_raw if digikey_raw else mouser_raw
        base_mapper = config.DIGIKEY_MAPPER if digikey_raw else config.MOUSER_MAPPER
        
        final_data = self._process_and_format_data(base_raw_data, base_mapper, category_id)

        if not final_data:
            log.warning(f"Orchestrator: Failed to process data for '{part_number}' after finding category.")
            return None

        # Step 3: Rename generic keys and merge supplier-specific info
        final_data['supplier_1'] = "Digi-Key" if digikey_raw else "Mouser"
        # --- FIX: Use .pop() to move the value and remove the old key ---
        final_data['supplier_part_number_1'] = final_data.pop('supplier_part_number', None)
        final_data['supplier_product_url_1'] = final_data.pop('supplier_product_url', None)
        
        secondary_raw = mouser_raw if digikey_raw and mouser_raw else None
        if secondary_raw:
            final_data['supplier_2'] = "Mouser"
            final_data['supplier_part_number_2'] = self._get_nested_value(secondary_raw, config.MOUSER_MAPPER['supplier_part_number'])
            final_data['supplier_product_url_2'] = self._get_nested_value(secondary_raw, config.MOUSER_MAPPER['supplier_product_url'])

        return [final_data]