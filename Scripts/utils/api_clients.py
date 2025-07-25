# scripts/utils/api_clients.py
import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. CONFIGURATION (The "Professional" Heart of the System)
# ==============================================================================

# แก้ไขฟังก์ชันนี้ทั้งฟังก์ชัน
def _get_nested_value(data_dict, key_path):
    """
    Safely gets a value from a nested structure (dicts and lists)
    using a dot-separated path, e.g., "ProductVariations.0.DigiKeyProductNumber".
    """
    keys = key_path.split('.')
    current_level_data = data_dict
    for key in keys:
        if key.isdigit(): # ✅ ถ้า key เป็นตัวเลข (เช่น '0') ให้ถือว่าเป็น index ของ list
            try:
                index = int(key)
                if isinstance(current_level_data, list) and len(current_level_data) > index:
                    current_level_data = current_level_data[index]
                else:
                    return None # ข้อมูลไม่ใช่ list หรือ index เกิน
            except (ValueError, IndexError):
                return None
        else: # ✅ ถ้า key เป็นข้อความปกติ ให้ถือว่าเป็น key ของ dict
            if isinstance(current_level_data, dict):
                current_level_data = current_level_data.get(key)
            else:
                return None # พยายามจะหา key ในข้อมูลที่ไม่ใช่ dict
    return current_level_data

# --- Data Mappers for each supplier ---
# Maps our standard field names to the specific field names in the supplier's API response.
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
    "mounting_type": "MountingStyle",
    "supplier_part_number": "MouserPartNumber",
    "supplier_product_url": "ProductDetailUrl",
    "category_name": "Category",
    "parameters_list": "ProductAttributes",
    "pricing_list": "PriceBreaks",
    "quantity_available": "Availability",
}

# --- Category-Specific Logic Recipes ---
# Central configuration for generating descriptions and values.
CATEGORY_RECIPES = [
    {
        # ✅ เพิ่ม cat_path and ... เพื่อป้องกัน list ว่าง
        "trigger": lambda cat_path: cat_path and "Resistors" in cat_path[0],
        "description_prefix": lambda path: path[-1].replace(" - Surface Mount", ""),
        "description_params": ["Resistance", "Tolerance", "Power (Watts)"],
        "value_generator": lambda find: f"{format_resistance(find('Resistance'))}, {find('Tolerance')}, {find('Power (Watts)').split(',')[0]}"
    },
    {
        # ✅ เพิ่ม cat_path and ...
        "trigger": lambda cat_path: cat_path and "Capacitors" in cat_path[0],
        "description_prefix": lambda path: path[-1],
        "description_params": ["Capacitance", "Tolerance", "Voltage - Rated", "Temperature Coefficient", "Package / Case"],
        "value_generator": lambda find: f"{find('Capacitance').replace(' µF', 'µF')}, {find('Voltage - Rated')}, {find('Temperature Coefficient')}"
    },
    {
        # ✅ เพิ่ม cat_path and ...
        "trigger": lambda cat_path: cat_path and len(cat_path) > 2 and "Bridge Rectifiers" in cat_path[2],
        "description_prefix": lambda path: path[2],
        "description_params": ["Diode Type", "Technology", "Voltage - Peak Reverse (Max)", "Current - Average Rectified (Io)"],
        "value_generator": lambda find: f"{find('Voltage - Peak Reverse (Max)')}, {find('Current - Average Rectified (Io)')}"
    },
    {
        # ✅ เพิ่ม cat_path and ...
        "trigger": lambda cat_path: cat_path and len(cat_path) > 2 and "Rectifiers" in cat_path[2], # แก้ไขจาก > 3 เป็น > 2
        "description_prefix": lambda path: path[-1], # Deepest category, e.g., "Standard"
        "description_params": ["Voltage - DC Reverse (Vr) (Max)", "Current - Average Rectified (Io)", "Reverse Recovery Time (trr)"],
        "value_generator": lambda find: f"{find('Voltage - DC Reverse (Vr) (Max)')}, {find('Current - Average Rectified (Io)')}"
    },
]

# ==============================================================================
# 2. GENERIC HELPER FUNCTIONS (The "Craftsman's" Tools)
# ==============================================================================

# ✅ เพิ่มฟังก์ชันนี้เข้ามา
def find_param_in_list(parameters: list, *param_names) -> str | None:
    """Finds a parameter value from a list of parameter dictionaries."""
    if not parameters:
        return None
    return next((p['ValueText'] for p in parameters if p.get('ParameterText') in param_names and p.get('ValueText') != '-'), None)

def normalize_rohs_status(status_string: str | None) -> str:
    """Normalizes RoHS status to 'Yes' or 'No'."""
    if not status_string:
        return "No"
    return "Yes" if "rohs" in status_string.lower() else "No"

def normalize_operating_temperature(data_dict: dict) -> dict:
    """Finds operating_temperature, cleans it, and updates the dictionary."""
    temp_str = data_dict.get("operating_temperature")
    if isinstance(temp_str, str):
        cleaned = re.sub(r"\s*\([^)]*\)", "", temp_str)
        data_dict["operating_temperature"] = cleaned.strip()
    return data_dict

def format_resistance(resistance_raw: str) -> str:
    """Formats resistance string with appropriate symbols."""
    if not isinstance(resistance_raw, str): return ""
    text = resistance_raw.strip()
    text = re.sub(r'\s*MOhms\b', 'MΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*kOhms\b', 'kΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*mOhms\b', 'mΩ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*Ohms\b', 'Ω', text, flags=re.IGNORECASE)
    return text

def get_category_path(category_node: dict | None) -> list:
    """Recursively finds the category path names as a list."""
    if not isinstance(category_node, dict):
        return []
    current_name = category_node.get("Name", "")
    child_categories = category_node.get("ChildCategories")
    if child_categories:
        path_from_child = get_category_path(child_categories[0])
        return [current_name] + path_from_child
    return [current_name]

# ==============================================================================
# 3. API CALLING LAYER (Focused Responsibility)
# ==============================================================================

def _call_digikey_api(part_number: str) -> dict | None:
    """Calls the Digi-Key API and returns the raw product data dictionary."""
    client_id = os.getenv("DIGIKEY_CLIENT_ID")
    client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")
    if not client_id or not client_secret: return None

    try:
        # Get Token
        token_endpoint = "https://api.digikey.com/v1/oauth2/token"
        auth_body = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
        token_response = requests.post(token_endpoint, data=auth_body)
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        
        # Search for part
        print(f"Calling Digi-Key API V4 KeywordSearch for '{part_number}'...")
        search_endpoint = "https://api.digikey.com/products/v4/search/keyword"
        headers = {"Authorization": f"Bearer {access_token}", "X-DIGIKEY-Client-Id": client_id, "Content-Type": "application/json", "X-DIGIKEY-Locale-Site": "US", "X-DIGIKEY-Locale-Language": "en"}
        search_body = {"Keywords": part_number, "RecordCount": 1}
        search_response = requests.post(search_endpoint, headers=headers, json=search_body)
        if search_response.status_code == 404: return None
        search_response.raise_for_status()
        results = search_response.json()

        return results.get('Products')[0] if results.get('Products') else None
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return None

def _call_mouser_api(part_number: str) -> dict | None:
    """Calls the Mouser API and returns the raw product data dictionary."""
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key: return None
    
    print(f"Calling Mouser Keyword API for '{part_number}'...")
    endpoint = f"https://api.mouser.com/api/v1/search/keyword?apiKey={api_key}"
    headers = {'Content-Type': 'application/json'}
    body = {"SearchByKeywordRequest": {"keyword": part_number, "records": 1}}
    
    try:
        response = requests.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        results = response.json()
        part = results.get('SearchResults', {}).get('Parts', [None])[0]

        # Mouser can return irrelevant parts, so we double-check the part number
        if not part or part.get("ManufacturerPartNumber", "").upper() != part_number.upper():
            return None
        return part
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return None

# ==============================================================================
# 4. DATA TRANSFORMATION & BUSINESS LOGIC LAYER (The Brains)
# ==============================================================================

def _transform_data(raw_part: dict, mapper: dict) -> dict:
    """Transforms raw API data into our standard format using a mapper."""
    normalized = {}
    for standard_field, supplier_field in mapper.items():
        normalized[standard_field] = _get_nested_value(raw_part, supplier_field)
    return normalized

def _apply_category_logic(part_data: dict) -> dict:
    """Applies category-specific logic to generate description and value."""
    category_path = get_category_path(part_data.get("category_obj"))
    parameters = part_data.get("parameters_list", [])

    def find_param(*param_names):
        # Helper to search within the part's specific parameter list
        return next((p['ValueText'] for p in parameters if p.get('ParameterText') in param_names and p.get('ValueText') != '-'), None)

    # Find the correct recipe
    for recipe in CATEGORY_RECIPES:
        if recipe["trigger"](category_path):
            # Generate description
            desc_details = [recipe["description_prefix"](category_path)]
            desc_details.extend(find_param(p) for p in recipe["description_params"])
            part_data["description"] = ", ".join(filter(None, desc_details))
            
            # Generate component value
            try:
                part_data["component_value"] = recipe["value_generator"](find_param)
            except (TypeError, AttributeError): # Handle cases where a needed param is None
                part_data["component_value"] = part_data.get("manufacturer_part_number")
            
            return part_data
    
    # Fallback if no recipe matches
    part_data["description"] = _get_nested_value(part_data, "Description.DetailedDescription") # Example path
    part_data["component_value"] = part_data.get("manufacturer_part_number")
    return part_data

# ในไฟล์ scripts/utils/api_clients.py

def _normalize_final_fields(part_data: dict) -> dict:
    """Performs final cleanup and formatting on the normalized data."""
    part_data["rohs_status"] = normalize_rohs_status(part_data.get("rohs_status"))
    
    # --- START: ส่วนที่แก้ไข ---

    # ดึงข้อมูลพื้นฐานที่จำเป็นออกมา
    parameters_list = part_data.get("parameters_list", [])
    category_path = get_category_path(part_data.get("category_obj"))

    # 1. ✅ เพิ่มการดึงค่า sub_subcategories (คือ category ที่ลึกที่สุด)
    part_data["sub_subcategories"] = category_path[-1] if category_path else None

    # 2. ✅ เพิ่มการดึงค่า operating_temperature
    part_data["operating_temperature"] = find_param_in_list(parameters_list, "Operating Temperature", "Operating Temperature - Junction")

    # 3. ✅ เพิ่มการดึงค่า package_case และ mounting_type
    part_data["package_case"] = find_param_in_list(parameters_list, "Package / Case")
    part_data["mounting_type"] = find_param_in_list(parameters_list, "Mounting Type")
    
    # ทำความสะอาด operating_temperature (ฟังก์ชันนี้จะจัดการเองถ้าค่าเป็น None)
    part_data = normalize_operating_temperature(part_data)

    # Infer mounting type ถ้ายังไม่มีค่า (Fallback Logic)
    if not part_data.get("mounting_type"):
        path_str = " ".join(category_path).lower()
        if "surface mount" in path_str:
            part_data["mounting_type"] = "Surface Mount"
        elif "through-hole" in path_str or "through hole" in path_str:
            part_data["mounting_type"] = "Through-Hole"
            
    # Format pricing
    price_breaks = []
    for price in part_data.get("pricing_list") or []:
        quantity = price.get('BreakQuantity') or price.get('Quantity')
        unit_price = price.get('UnitPrice') or price.get('Price', '').replace('$', '')
        if quantity is not None and unit_price is not None:
            price_breaks.append(f"{quantity}:{unit_price}")
    
    top_level_category = category_path[0] if category_path else None

    parameters = {
        "availability": part_data.get('quantity_available'), 
        "category": top_level_category
    }
    parameters["price_breaks_usd"] = ", ".join(price_breaks)
    part_data['parameters'] = json.dumps(parameters)

    # Clean up temporary fields
    part_data.pop("pricing_list", None)
    part_data.pop("parameters_list", None)
    part_data.pop("category_obj", None)
    part_data.pop("quantity_available", None)
    
    # --- END: ส่วนที่แก้ไข ---

    return part_data

# ==============================================================================
# 5. ORCHESTRATION LAYER (The Public Interface)
# ==============================================================================

def _process_supplier_data(raw_part: dict, mapper: dict) -> dict | None:
    """Chains together the transformation and normalization steps for a supplier."""
    if not raw_part:
        return None
    
    # if "DigiKeyProductNumber" in str(raw_part):
    #     print("\n--- RAW DIGI-KEY RESPONSE ---")
    #     print(json.dumps(raw_part, indent=2))
    #     print("-----------------------------\n")
    
    # Step 1: Basic transformation using mapper
    normalized_data = _transform_data(raw_part, mapper)
    
    # Step 2: Apply complex, category-based logic
    normalized_data = _apply_category_logic(normalized_data)

    # Step 3: Final cleanup and formatting
    normalized_data = _normalize_final_fields(normalized_data)
    
    return normalized_data

def fetch_part_data(part_number: str) -> list[dict] | None:
    """
    Orchestrates fetching data from all suppliers, normalizing it,
    and applying business logic for supplier priority.
    """
    print(f"API orchestrator: Searching for '{part_number}'...")
    
    digikey_raw = _call_digikey_api(part_number)
    mouser_raw = _call_mouser_api(part_number)

    digikey_data = _process_supplier_data(digikey_raw, DIGIKEY_MAPPER)
    mouser_data = _process_supplier_data(mouser_raw, MOUSER_MAPPER)

    if not digikey_data and not mouser_data:
        print(f"API orchestrator: Part number '{part_number}' not found on any supplier.")
        return None

    # Use Digi-Key data as the base if it exists, otherwise use Mouser
    final_data = digikey_data or mouser_data
    
    # Apply supplier priority rules
    if mouser_data and digikey_data:
        print("Data found on both suppliers. Setting Mouser as Supplier 1.")
        final_data["supplier_1"] = "Mouser"
        final_data["supplier_part_number_1"] = mouser_data.get("supplier_part_number")
        final_data["supplier_product_url_1"] = mouser_data.get("supplier_product_url")
        final_data["supplier_2"] = "Digi-Key"
        final_data["supplier_part_number_2"] = digikey_data.get("supplier_part_number")
        final_data["supplier_product_url_2"] = digikey_data.get("supplier_product_url")
    elif mouser_data:
        print("Data found only on Mouser.")
        final_data["supplier_1"] = "Mouser"
    elif digikey_data:
        print("Data found only on Digi-Key.")
        final_data["supplier_1"] = "Digi-Key"

    final_data.pop('supplier_part_number', None)
    final_data.pop('supplier_product_url', None)

    return [final_data]