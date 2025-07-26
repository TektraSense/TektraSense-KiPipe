import os
import requests
import json
import re
import logging
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

# --- Basic Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Constants ---
DIGIKEY_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DIGIKEY_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"
MOUSER_API_URL = "https://api.mouser.com/api/v1/search/keyword"

# --- Data Mappers ---
DIGIKEY_MAPPER = {
    "manufacturer_part_number": "ManufacturerProductNumber",
    "manufacturer": "Manufacturer.Name",
    "datasheet_url": "DatasheetUrl",
    "product_status": "ProductStatus.Status",
    "rohs_status": "Classifications.RohsStatus",
    "supplier_part_number": "ProductVariations.0.DigiKeyProductNumber",
    "supplier_product_url": "ProductUrl",
    "category_obj": "Category",
    "parameters_list": "Parameters",
    "pricing_list": "ProductVariations.0.StandardPricing",
    "quantity_available": "QuantityAvailable",
}

MOUSER_MAPPER = {
    "manufacturer_part_number": "ManufacturerPartNumber",
    "manufacturer": "Manufacturer",
    "datasheet_url": "DataSheetUrl",
    "product_status": "LifecycleStatus",
    "rohs_status": "ROHSStatus",
    "supplier_part_number": "MouserPartNumber",
    "supplier_product_url": "ProductDetailUrl",
    "category_obj": {"key": "Category", "is_mouser": True}, # Special handling for Mouser's flat category
    "parameters_list": "ProductAttributes",
    "pricing_list": "PriceBreaks",
    "quantity_available": "Availability",
}

# --- Category-Specific Logic Recipes ---
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
    """Safely gets a value from a nested structure using a dot-separated path."""
    keys = path.split('.')
    current_level = data
    for key in keys:
        if isinstance(current_level, dict):
            current_level = current_level.get(key)
        elif isinstance(current_level, list) and key.isdigit():
            try:
                current_level = current_level[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current_level

def find_param_in_list(parameters: Optional[List[Dict[str, str]]], *param_names: str) -> Optional[str]:
    """Finds a parameter value from a list of parameter dictionaries."""
    if not parameters:
        return None
    return next((p.get('ValueText') or p.get('AttributeValue') for p in parameters if (p.get('ParameterText') or p.get('AttributeName')) in param_names and (p.get('ValueText') or p.get('AttributeValue')) != '-'), None)

def normalize_rohs_status(status: Optional[str]) -> str:
    """Normalizes RoHS status string to 'Yes' or 'No'."""
    return "Yes" if status and "rohs" in status.lower() else "No"

def format_resistance(resistance_str: Optional[str]) -> str:
    """Formats resistance string with appropriate symbols (e.g., kOhms -> kΩ)."""
    if not isinstance(resistance_str, str): return ""
    text = resistance_str.strip()
    text = re.sub(r'\s*MOhms\b', 'MΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*kOhms\b', 'kΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*mOhms\b', 'mΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*Ohms\b', 'Ω', text, flags=re.IGNORECASE)
    return text

def get_category_path(category_obj: Optional[Dict[str, Any]]) -> List[str]:
    """Recursively builds the category path from a nested Digi-Key category object."""
    if not isinstance(category_obj, dict):
        return []
    name = category_obj.get("Name", "")
    children = category_obj.get("ChildCategories")
    # Base case: no more children
    if not children:
        return [name]
    # Recursive step
    return [name] + get_category_path(children[0])


# ==============================================================================
# 3. API CALLING LAYER
# ==============================================================================

def _call_digikey_api(part_number: str) -> Optional[Dict[str, Any]]:
    """Calls the Digi-Key API to search for a part number."""
    client_id = os.getenv("DIGIKEY_CLIENT_ID")
    client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")
    if not all([client_id, client_secret]):
        logging.error("Digi-Key API credentials are not set.")
        return None

    try:
        # Get Token
        auth_resp = requests.post(DIGIKEY_TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"})
        auth_resp.raise_for_status()
        access_token = auth_resp.json()["access_token"]
        
        # Search for part
        headers = {
            "Authorization": f"Bearer {access_token}", 
            "X-DIGIKEY-Client-Id": client_id, 
            "Content-Type": "application/json",
            "X-DIGIKEY-Locale-Site": "US",
            "X-DIGIKEY-Locale-Language": "en"
        }
        search_body = {"Keywords": part_number, "RecordCount": 1}
        logging.info(f"Calling Digi-Key KeywordSearch API for '{part_number}'...")
        search_resp = requests.post(DIGIKEY_SEARCH_URL, headers=headers, json=search_body)

        if search_resp.status_code == 404:
            return None
        search_resp.raise_for_status()
        results = search_resp.json()

        return results.get('Products')[0] if results.get('Products') else None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        logging.error(f"Digi-Key API call failed: {e}")
        return None

def _call_mouser_api(part_number: str) -> Optional[Dict[str, Any]]:
    """Calls the Mouser API to search for a part number."""
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        logging.error("Mouser API key is not set.")
        return None
    
    endpoint = f"{MOUSER_API_URL}?apiKey={api_key}"
    headers = {'Content-Type': 'application/json'}
    body = {"SearchByKeywordRequest": {"keyword": part_number, "records": 1}}
    
    try:
        logging.info(f"Calling Mouser Keyword API for '{part_number}'...")
        response = requests.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        results = response.json()
        parts = results.get('SearchResults', {}).get('Parts', [])

        if not parts:
            return None
        
        # Mouser can return irrelevant parts, so double-check the part number
        part = parts[0]
        if part.get("ManufacturerPartNumber", "").upper() == part_number.upper():
            return part
        return None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        logging.error(f"Mouser API call failed: {e}")
        return None


# ==============================================================================
# 4. DATA TRANSFORMATION & BUSINESS LOGIC LAYER
# ==============================================================================

def _transform_data(raw_part: Dict[str, Any], mapper: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms raw API data into our standard format using a mapper."""
    normalized = {}
    for standard_field, supplier_field in mapper.items():
        if isinstance(supplier_field, dict) and supplier_field.get("is_mouser"):
            # Special handling for Mouser's flat category string
            normalized[standard_field] = {"Name": raw_part.get(supplier_field["key"])}
        else:
            normalized[standard_field] = _get_nested_value(raw_part, supplier_field)
    return normalized

def _apply_category_logic(part_data: Dict[str, Any]) -> Dict[str, Any]:
    """Applies category-specific logic to generate description and value."""
    category_path = get_category_path(part_data.get("category_obj"))
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
                # value_generator จะคืนค่าเป็น string ที่สมบูรณ์แล้ว
                part_data["component_value"] = recipe["value_generator"](find_param, category_path)
            except (TypeError, AttributeError):
                part_data["component_value"] = part_data.get("manufacturer_part_number")
            
            # ทำให้แน่ใจว่าถ้า component_value เป็นค่าว่าง ให้ใช้ part_number แทน
            if not part_data.get("component_value"):
                part_data["component_value"] = part_data.get("manufacturer_part_number")

            return part_data
    
    # Fallback if no recipe matches
    part_data["description"] = _get_nested_value(part_data, "Description.DetailedDescription")
    part_data["component_value"] = part_data.get("manufacturer_part_number")
    return part_data

def _extract_physical_params(part_data: Dict[str, Any], params_list: List[Dict], category_path: List[str]):
    """Extracts and standardizes physical parameters like temperature and mounting type."""
    if category_path:
        part_data["sub_subcategories"] = re.sub(r"\s*-\s*Surface Mount$", "", category_path[-1]).strip()
    else:
        part_data["sub_subcategories"] = None

    part_data["package_case"] = find_param_in_list(params_list, "Package / Case")
    
    # Extract and clean operating temperature
    temp_str = find_param_in_list(params_list, "Operating Temperature", "Operating Temperature - Junction")
    if isinstance(temp_str, str):
        part_data["operating_temperature"] = re.sub(r"\s*\([^)]*\)", "", temp_str).strip()
    else:
        part_data["operating_temperature"] = None

    # Standardize mounting type from parameter list first, then from category path
    mount_type = find_param_in_list(params_list, "Mounting Type")
    if isinstance(mount_type, str):
        if "surface mount" in mount_type.lower():
            part_data["mounting_type"] = "Surface Mount"
        elif "through-hole" in mount_type.lower() or "through hole" in mount_type.lower():
            part_data["mounting_type"] = "Through-Hole"
    elif not part_data.get("mounting_type"): # Fallback to category path
        path_str = " ".join(category_path).lower()
        if "surface mount" in path_str:
            part_data["mounting_type"] = "Surface Mount"
        elif "through-hole" in path_str or "through hole" in path_str:
            part_data["mounting_type"] = "Through-Hole"


def _format_pricing_and_availability(part_data: Dict[str, Any], category_path: List[str]):
    """Formats pricing into a string and builds the final parameters JSON."""
    price_breaks = []
    for price in part_data.get("pricing_list") or []:
        quantity = price.get('BreakQuantity') or price.get('Quantity')
        unit_price = price.get('UnitPrice') or str(price.get('Price', '')).replace('$', '')
        if quantity is not None and unit_price:
            price_breaks.append(f"{quantity}:{unit_price}")
    
    parameters = {
        "availability": part_data.get('quantity_available'), 
        "category": category_path[0] if category_path else None,
        "price_breaks_usd": ", ".join(price_breaks)
    }
    part_data['parameters'] = json.dumps(parameters)


def _normalize_final_fields(part_data: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrates final cleanup and data formatting."""
    part_data["rohs_status"] = normalize_rohs_status(part_data.get("rohs_status"))
    
    params_list = part_data.get("parameters_list", [])
    category_path = get_category_path(part_data.get("category_obj"))
    
    _extract_physical_params(part_data, params_list, category_path)
    _format_pricing_and_availability(part_data, category_path)

    # Clean up temporary fields that are now embedded in other fields
    part_data.pop("pricing_list", None)
    part_data.pop("parameters_list", None)
    part_data.pop("category_obj", None)
    part_data.pop("quantity_available", None)
    
    return part_data


# ==============================================================================
# 5. ORCHESTRATION LAYER (The Public Interface)
# ==============================================================================

def _process_supplier_data(raw_part: Optional[Dict[str, Any]], mapper: Dict[str, Any], supplier_name: str) -> Optional[Dict[str, Any]]:
    """Chains together the full data processing pipeline for a single supplier."""
    if not raw_part:
        return None
    
    logging.info(f"Processing raw data from {supplier_name}...")
    normalized_data = _transform_data(raw_part, mapper)
    normalized_data = _apply_category_logic(normalized_data)
    normalized_data = _normalize_final_fields(normalized_data)
    normalized_data['supplier_name'] = supplier_name # Add supplier name for later use
    
    return normalized_data

def fetch_part_data(part_number: str) -> Optional[List[Dict[str, Any]]]:
    """
    Orchestrates fetching data from all suppliers, normalizing it,
    and applying business logic for supplier priority.
    """
    logging.info(f"Orchestrator: Starting search for '{part_number}'...")

    digikey_raw = _call_digikey_api(part_number)
    mouser_raw = _call_mouser_api(part_number)

    processed_results = [
        _process_supplier_data(digikey_raw, DIGIKEY_MAPPER, "Digi-Key"),
        _process_supplier_data(mouser_raw, MOUSER_MAPPER, "Mouser")
    ]

    valid_results = [res for res in processed_results if res is not None]

    if not valid_results:
        logging.warning(f"Orchestrator: Part '{part_number}' not found on any supplier.")
        return None

    # Ensure Digi-Key is the primary data source by sorting it to the front of the list.
    valid_results.sort(key=lambda x: x['supplier_name'] != 'Digi-Key')

    # Use the first result as the base for our final data.
    final_data = valid_results[0]
    final_data["supplier_1"] = final_data.pop('supplier_name')
    final_data['supplier_part_number_1'] = final_data.pop('supplier_part_number')
    final_data['supplier_product_url_1'] = final_data.pop('supplier_product_url')

    # If a second supplier exists, merge its key information.
    if len(valid_results) > 1:
        secondary_supplier = valid_results[1]
        logging.info(
            f"Data found on both suppliers. Using {final_data['supplier_1']} as base, "
            f"merging from {secondary_supplier['supplier_name']}."
        )
        final_data["supplier_2"] = secondary_supplier.get("supplier_name")
        final_data["supplier_part_number_2"] = secondary_supplier.get("supplier_part_number")
        final_data["supplier_product_url_2"] = secondary_supplier.get("supplier_product_url")

    return [final_data]