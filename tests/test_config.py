# tests/test_config.py
import pytest
from tektrasense_kipipe import config
from unittest.mock import MagicMock

def test_format_resistance():
    """Tests the resistance formatting utility function."""
    assert config.format_resistance("10 kOhms") == "10kΩ"
    assert config.format_resistance("2.2 MOhms") == "2.2MΩ"
    assert config.format_resistance("100 mOhms") == "100mΩ"
    assert config.format_resistance("470 Ohms") == "470Ω"
    assert config.format_resistance(None) == ""

def test_resistor_recipe_trigger_and_value_generator():
    """
    Tests the trigger and value generation for the Resistors category recipe.
    """
    # 1. Arrange
    resistor_recipe = config.CATEGORY_RECIPES[0]
    
    # --- Test Trigger ---
    assert resistor_recipe["trigger"](["Resistors", "Chip Resistor - Surface Mount"]) is True
    assert resistor_recipe["trigger"](["Capacitors", "Ceramic Capacitors"]) is False
    assert resistor_recipe["trigger"](None) is False

    # --- Test Value Generator ---
    # สร้าง mock 'find' function
    def mock_find_param(param_name):
        params = {
            'Resistance': '100 kOhms',
            'Tolerance': '±5%',
            'Power (Watts)': '0.125W, 1/8W'
        }
        return params.get(param_name)

    expected_value = "100kΩ,±5%,0.125W"
    generated_value = resistor_recipe["value_generator"](mock_find_param, None)
    
    assert generated_value == expected_value

def test_fet_recipe_value_generator():
    """
    Tests the more complex regex-based value generator for the FETs recipe.
    """
    # 1. Arrange
    fet_recipe = next(r for r in config.CATEGORY_RECIPES if r["trigger"](["Semiconductors", "Transistors", "FETs, MOSFETs"]))

    # 2. Arrange
    def mock_find_param(param_name):
        params = {
            'Drain to Source Voltage (Vdss)': '60V',
            'Current - Continuous Drain (Id) @ 25°C': '12A (Ta), 25A (Tc)', # เพิ่ม Current
            'Power Dissipation (Max)': '2.5W (Ta), 150W (Tc)'
        }
        return params.get(param_name)
    
    # 3. Act
    generated_value = fet_recipe["value_generator"](mock_find_param, None)

    # 4. Assert
    # สังเกตว่า Regex จะดึงค่าที่เกี่ยวกับ (Tc) เท่านั้น
    assert generated_value == "60V,25A,150W"