# tests/test_data_processor.py
import pytest
from tektrasense_kipipe.data_processor import ComponentProcessor

# เราไม่จำเป็นต้องใช้ db_manager จริงๆ ในการทดสอบนี้
# แต่เราต้องสร้าง instance ของ Class ขึ้นมาก่อน
@pytest.fixture
def processor():
    """Creates an instance of ComponentProcessor for testing."""
    # ในอนาคต เราจะใช้ Mocking เพื่อจำลอง db_manager ที่นี่
    return ComponentProcessor(db_manager=None)

def test_normalize_rohs_status(processor):
    """
    Tests the _normalize_rohs_status method with various inputs.
    """
    # --- 1. Arrange (เตรียมข้อมูล) ---
    input_compliant = "RoHS Compliant by Exemption"
    input_non_compliant = "Non-Compliant"
    input_none = None
    input_other = "Some other text"

    # --- 2. Act (เรียกใช้ฟังก์ชันที่ต้องการทดสอบ) ---
    result_compliant = processor._normalize_rohs_status(input_compliant)
    result_non_compliant = processor._normalize_rohs_status(input_non_compliant)
    result_none = processor._normalize_rohs_status(input_none)
    result_other = processor._normalize_rohs_status(input_other)

    # --- 3. Assert (ตรวจสอบว่าผลลัพธ์ถูกต้อง) ---
    assert result_compliant == "Yes"
    assert result_non_compliant == "No"
    assert result_none == "No"
    assert result_other == "No"