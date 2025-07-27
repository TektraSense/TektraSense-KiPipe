import os
import requests
import json
import re
import logging
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from db_manager import DatabaseManager

# --- Basic Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Constants ---
DIGIKEY_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DIGIKEY_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"
MOUSER_API_URL = "https://api.mouser.com/api/v1/search/keyword"

# --- Data Mappers ---
DIGIKEY_MAPPER = {
    "manufacturer_part_number": "ManufacturerProductNumber", "manufacturer": "Manufacturer.Name",
    "description": "Description.DetailedDescription", "datasheet_url": "DatasheetUrl",
    "product_status": "ProductStatus.Status", "rohs_status": "Classifications.RohsStatus",
    "supplier_part_number": "ProductVariations.0.DigiKeyProductNumber", "supplier_product_url": "ProductUrl",
    "supplier_category_object": "Category", "parameters_list": "Parameters",
    "pricing_list": "ProductVariations.0.StandardPricing", "quantity_available": "QuantityAvailable",
}
MOUSER_MAPPER = {
    "manufacturer_part_number": "ManufacturerPartNumber", "manufacturer": "Manufacturer",
    "description": "Description", "datasheet_url": "DataSheetUrl",
    "product_status": "LifecycleStatus", "rohs_status": "ROHSStatus",
    "supplier_part_number": "MouserPartNumber", "supplier_product_url": "ProductDetailUrl",
    "supplier_category": "Category", "parameters_list": "ProductAttributes",
    "pricing_list": "PriceBreaks", "quantity_available": "Availability",
}

# --- Formatting Recipes ---
def format_resistance(resistance_str: Optional[str]) -> str:
    if not isinstance(resistance_str, str): return ""
    text = resistance_str.strip()
    text = re.sub(r'\s*MOhms\b', 'MΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*kOhms\b', 'kΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*mOhms\b', 'mΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*Ohms\b', 'Ω', text, flags=re.IGNORECASE)
    return text

CATEGORY_RECIPES = [
    {
        "trigger": lambda path: path and "Resistors" in path[0],
        "description_prefix": lambda path: path[-1].replace(" - Surface Mount", ""),
        "description_params": lambda path: ["Composition", "Resistance", "Tolerance", "Power (Watts)", "Temperature Coefficient", "Package / Case", "Features", "Ratings"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                format_resistance(find('Resistance')),
                find('Tolerance'),
                (find('Power (Watts)').split(',')[0] if find('Power (Watts)') else None)
            ] if v
        )
    },
    {
        "trigger": lambda path: path and "Capacitors" in path[0],
        "description_prefix": lambda path: path[1] if len(path) > 1 else path[0],
        "description_params": lambda path: ["Capacitance", "Tolerance", "Voltage - Rated", "Temperature Coefficient", "Package / Case", "Features", "Ratings"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Capacitance'),
                find('Voltage - Rated'),
                find('Temperature Coefficient')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and "Crystals, Oscillators, Resonators" in path[0],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Frequency", "Frequency Stability", "Frequency Tolerance", "Load Capacitance", "Package / Case", "Features", "Ratings", "Applications"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Frequency'),
                find('Frequency Tolerance'),
                find('Load Capacitance')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and "Inductors, Coils, Chokes" in path[0],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Inductance", "Tolerance", "Current Rating (Amps)", "DC Resistance (DCR)", "Package / Case", "Features", "Ratings"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Inductance'),
                find('Tolerance'),
                find('Current Rating (Amps)')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and "Bridge Rectifiers" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Diode Type", "Technology", "Voltage - Peak Reverse (Max)", "Current - Average Rectified (Io)", "Package / Case", "Features", "Ratings", "Applications"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Voltage - Peak Reverse (Max)'),
                find('Current - Average Rectified (Io)')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and "Rectifiers" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Voltage - DC Reverse (Vr) (Max)", "Current - Average Rectified (Io)", "Reverse Recovery Time (trr)", "Package / Case", "Features", "Ratings", "Applications"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Voltage - DC Reverse (Vr) (Max)'),
                find('Current - Average Rectified (Io)')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and "Zener" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Voltage - Zener (Nom) (Vz)", "Tolerance", "Power - Max", "Impedance (Max) (Zzt)", "Package / Case", "Features", "Ratings", "Applications"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Voltage - Zener (Nom) (Vz)'),
                find('Tolerance'),
                find('Power - Max')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and "Bipolar (BJT)" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Transistor Type", "Voltage - Collector Emitter Breakdown (Max)", "Current - Collector (Ic) (Max)", "Power - Max", "Frequency - Transition", "Package / Case", "Grade", "Qualification"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Voltage - Collector Emitter Breakdown (Max)'),
                find('Current - Collector (Ic) (Max)'),
                find('Power - Max')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and "FETs, MOSFETs" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["FET Type", "Technology", "Drain to Source Voltage (Vdss)", "Current - Continuous Drain (Id) @ 25°C", "Power Dissipation (Max)", "Vgs (Max)", "Package / Case", "Grade", "Qualification"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Drain to Source Voltage (Vdss)'),
                next(iter(re.findall(r"(\d+mA)\s*\(Tc\)", find('Current - Continuous Drain (Id) @ 25°C') or '')), ''),
                next(iter(re.findall(r"([\d\.]+m?W)\s*\(Tc\)", find('Power Dissipation (Max)') or '')), '')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 1 and path[0] == "Optoelectronics" and "LED Indication" in path[1],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Lens Transparency", "Color", "Wavelength - Dominant", "Voltage - Forward (Vf) (Typ)", "Current - Test", "Package / Case", "Features"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Color'),
                find('Voltage - Forward (Vf) (Typ)'),
                find('Current - Test')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 1 and path[0] == "Circuit Protection" and "PTC Resettable Fuses" in path[1],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Type", "Current - Hold (Ih) (Max)", "Voltage - Max", "Current - Max", "Time to Trip", "Package / Case", "Ratings", "Approval Agency"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Current - Hold (Ih) (Max)'),
                find('Voltage - Max'),
                find('Time to Trip')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 1 and path[0] == "Circuit Protection" and "Fuses" in path[1],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Fuse Type", "Current Rating (Amps)", "Voltage Rating - DC", "Response Time", "Package / Case", "Approval Agency"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Current Rating (Amps)'),
                find('Voltage Rating - DC'),
                find('Response Time')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 2 and path[1] == "Transient Voltage Suppressors (TVS)" and "TVS Diodes" in path[2],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Type", "Voltage - Clamping (Max) @ Ipp", "Current - Peak Pulse (10/1000µs)", "Power - Peak Pulse", "Package / Case", "Applications"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Voltage - Clamping (Max) @ Ipp'),
                find('Current - Peak Pulse (10/1000µs)')
            ] if v
        )
    },
    {
        "trigger": lambda path: path and len(path) > 1 and path[0] == "Circuit Protection" and "Varistors, MOVs" in path[1],
        "description_prefix": lambda path: path[-1],
        "description_params": lambda path: ["Varistor Voltage (Typ)", "Current - Surge", "Energy", "Capacitance @ Frequency", "Package / Case", "Grade", "Qualification"],
        "value_generator": lambda find, path: ", ".join(
            v.replace(" ", "") for v in [
                find('Varistor Voltage (Typ)'),
                find('Current - Surge'),
                find('Energy')
            ] if v
        )
    }
]

# ==============================================================================
# 2. GENERIC HELPER FUNCTIONS
# ==============================================================================
def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    keys = path.split('.')
    current_level = data
    for key in keys:
        if isinstance(current_level, dict): current_level = current_level.get(key)
        elif isinstance(current_level, list) and key.isdigit():
            try: current_level = current_level[int(key)]
            except (ValueError, IndexError): return None
        else: return None
    return current_level

def find_param_in_list(parameters: Optional[List[Dict[str, str]]], *param_names: str) -> Optional[str]:
    if not parameters: return None
    return next((p.get('ValueText') or p.get('AttributeValue') for p in parameters if (p.get('ParameterText') or p.get('AttributeName')) in param_names and (p.get('ValueText') or p.get('AttributeValue')) != '-'), None)

def normalize_rohs_status(status: Optional[str]) -> str:
    return "Yes" if status and "rohs" in status.lower() else "No"

def get_category_path_from_object(category_obj: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(category_obj, dict): return []
    name = category_obj.get("Name", "")
    children = category_obj.get("ChildCategories")
    if not children: return [name]
    return [name] + get_category_path_from_object(children[0])

# ==============================================================================
# 3. API CALLING LAYER
# ==============================================================================
def _call_digikey_api(part_number: str) -> Optional[Dict[str, Any]]:
    client_id = os.getenv("DIGIKEY_CLIENT_ID")
    client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")
    if not all([client_id, client_secret]):
        log.error("Digi-Key API credentials are not set.")
        return None
    try:
        auth_resp = requests.post(DIGIKEY_TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"})
        auth_resp.raise_for_status()
        access_token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}", "X-DIGIKEY-Client-Id": client_id, "Content-Type": "application/json", "X-DIGIKEY-Locale-Site": "US", "X-DIGIKEY-Locale-Language": "en"}
        search_body = {"Keywords": part_number, "RecordCount": 1}
        log.info(f"Calling Digi-Key KeywordSearch API for '{part_number}'...")
        search_resp = requests.post(DIGIKEY_SEARCH_URL, headers=headers, json=search_body)
        if search_resp.status_code == 404: return None
        search_resp.raise_for_status()
        results = search_resp.json()
        return results.get('Products')[0] if results.get('Products') else None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        log.error(f"Digi-Key API call failed: {e}")
        return None

def _call_mouser_api(part_number: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        log.error("Mouser API key is not set.")
        return None
    endpoint = f"{MOUSER_API_URL}?apiKey={api_key}"
    headers = {'Content-Type': 'application/json'}
    body = {"SearchByKeywordRequest": {"keyword": part_number, "records": 1}}
    try:
        log.info(f"Calling Mouser Keyword API for '{part_number}'...")
        response = requests.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        results = response.json()
        parts = results.get('SearchResults', {}).get('Parts', [])
        if not parts: return None
        part = parts[0]
        if part.get("ManufacturerPartNumber", "").upper() == part_number.upper():
            return part
        return None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        log.error(f"Mouser API call failed: {e}")
        return None

# ==============================================================================
# 4. DATA TRANSFORMATION & BUSINESS LOGIC LAYER
# ==============================================================================

def _apply_formatting_recipes(part_data: Dict[str, Any], category_details: Dict[str, Any], category_path: List[str]) -> Dict[str, Any]:
    params = part_data.get("parameters_list", [])
    def find_param(*param_names):
        return find_param_in_list(params, *param_names)

    for recipe in CATEGORY_RECIPES:
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
    
    # Fallback if no recipe matches
    if not part_data.get("description"):
        part_data["description"] = part_data.get("description")
    if not part_data.get("component_value"):
        part_data["component_value"] = part_data.get("manufacturer_part_number")
    return part_data

def _process_and_format_data(raw_part: Dict[str, Any], mapper: Dict[str, Any], category_id: int, db_manager: DatabaseManager) -> Optional[Dict[str, Any]]:
    part_data = {std_field: _get_nested_value(raw_part, sup_field) for std_field, sup_field in mapper.items()}
    part_data['category_id'] = category_id
    
    category_details = db_manager.get_category_details(category_id)
    if not category_details:
        log.error(f"Could not find details for category_id {category_id}")
        return None

    parent_details = db_manager.get_category_details(category_details['parent_id']) if category_details.get('parent_id') else None
    full_prefix = category_details['prefix']
    if parent_details:
        full_prefix = f"{parent_details['prefix']}-{full_prefix}"
    part_data['internal_part_id'] = db_manager.get_next_internal_part_id(full_prefix)

    category_path = get_category_path_from_object(part_data.get("supplier_category_object"))
    part_data = _apply_formatting_recipes(part_data, category_details, category_path)

    part_data["rohs_status"] = normalize_rohs_status(part_data.get("rohs_status"))
    price_breaks = []
    for price in part_data.get("pricing_list") or []:
        quantity = price.get('BreakQuantity') or price.get('Quantity')
        unit_price = str(price.get('UnitPrice') or price.get('Price', '')).replace('$', '')
        if quantity is not None and unit_price: price_breaks.append(f"{quantity}:{unit_price}")
    
    parameters_json = {"availability": part_data.get('quantity_available'), "price_breaks_usd": ", ".join(price_breaks)}
    part_data['parameters'] = json.dumps(parameters_json)
    
    params_list = part_data.get("parameters_list", [])
    part_data["package_case"] = find_param_in_list(params_list, "Package / Case")
    
    mount_type = find_param_in_list(params_list, "Mounting Type")
    part_data["mounting_type"] = None
    if isinstance(mount_type, str):
        if "surface mount" in mount_type.lower(): part_data["mounting_type"] = "Surface Mount"
        elif "through-hole" in mount_type.lower() or "through hole" in mount_type.lower(): part_data["mounting_type"] = "Through-Hole"
    if not part_data.get("mounting_type"):
        path_str = " ".join(category_path).lower()
        if "surface mount" in path_str: part_data["mounting_type"] = "Surface Mount"
        elif "through-hole" in path_str or "through hole" in path_str: part_data["mounting_type"] = "Through-Hole"
    
    temp_str = find_param_in_list(params_list, "Operating Temperature", "Operating Temperature - Junction")
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

# ==============================================================================
# 5. ORCHESTRATION LAYER (The Public Interface) - FINAL CORRECTED VERSION
# ==============================================================================
def fetch_part_data(part_number: str, db_manager: DatabaseManager) -> Optional[List[Dict[str, Any]]]:
    log.info(f"Orchestrator: Starting search for '{part_number}'...")

    digikey_raw = _call_digikey_api(part_number)
    mouser_raw = _call_mouser_api(part_number)

    if not digikey_raw and not mouser_raw:
        log.warning(f"Orchestrator: Part '{part_number}' not found on any supplier.")
        return None

    # Step 1: Find a valid Category ID, prioritizing Digi-Key
    category_id = None
    dk_cat_name, mouser_cat_name = None, None

    if digikey_raw:
        dk_cat_obj = _get_nested_value(digikey_raw, DIGIKEY_MAPPER['supplier_category_object'])
        dk_cat_name = _get_nested_value(dk_cat_obj, "Name")
        if dk_cat_name:
            category_id = db_manager.get_category_id("Digi-Key", dk_cat_name)

    if not category_id and mouser_raw:
        mouser_cat_name = _get_nested_value(mouser_raw, MOUSER_MAPPER['supplier_category'])
        if mouser_cat_name:
            log.info("Borrowing category from Mouser...")
            category_id = db_manager.get_category_id("Mouser", mouser_cat_name)

    if not category_id:
        log.warning(f"No valid category mapping found for '{part_number}'. Logging for review.")
        if dk_cat_name: db_manager.add_unmapped_category("Digi-Key", dk_cat_name)
        if mouser_cat_name: db_manager.add_unmapped_category("Mouser", mouser_cat_name)
        return None

    # Step 2: Process the data, ALWAYS prioritizing Digi-Key's raw data if it exists
    base_raw_data = digikey_raw if digikey_raw else mouser_raw
    base_mapper = DIGIKEY_MAPPER if digikey_raw else MOUSER_MAPPER
    
    final_data = _process_and_format_data(base_raw_data, base_mapper, category_id, db_manager)

    if not final_data:
        log.warning(f"Orchestrator: Failed to process data for '{part_number}' after finding category.")
        return None

    # Step 3: Rename generic keys to specific supplier keys (_1, _2)
    primary_supplier_is_digikey = True if digikey_raw else False

    final_data['supplier_1'] = "Digi-Key" if primary_supplier_is_digikey else "Mouser"
    # Use .pop() to get the value AND remove the old key at the same time
    final_data['supplier_part_number_1'] = final_data.pop('supplier_part_number')
    final_data['supplier_product_url_1'] = final_data.pop('supplier_product_url')

    # Add secondary supplier info if it exists
    if primary_supplier_is_digikey and mouser_raw:
        final_data['supplier_2'] = "Mouser"
        final_data['supplier_part_number_2'] = _get_nested_value(mouser_raw, MOUSER_MAPPER['supplier_part_number'])
        final_data['supplier_product_url_2'] = _get_nested_value(mouser_raw, MOUSER_MAPPER['supplier_product_url'])

    return [final_data]