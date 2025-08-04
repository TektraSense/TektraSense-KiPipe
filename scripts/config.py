"""
Configuration file for the KiCad Component Pipeline.

This file stores all static configuration data, including API constants,
data mappers for suppliers, and formatting recipes for component values
and descriptions.
"""
import re
from typing import Optional, List, Dict, Any

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

SYMBOL_SEARCH_PATHS = [
    # Path for Custom Library ของคุณ
    "/Users/artrony/artronyone_wks/libs/KiCad/TektraSense-KiCad-DBLibs/symbols",
    
    # Path for KiCad Official Library
    "/Users/artrony/artronyone_wks/libs/KiCad/kicad-symbols"
]

FOOTPRINT_SEARCH_PATHS = [
    # Path for Custom Library ของคุณ
    "/Users/artrony/artronyone_wks/libs/KiCad/TektraSense-KiCad-DBLibs/footprints"

    # Path for KiCad Official Library
    "/Users/artrony/artronyone_wks/libs/KiCad/kicad-footprints"
]

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