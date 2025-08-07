# tests/test_data_processor.py
import pytest
from unittest.mock import MagicMock, patch, ANY # <-- เพิ่ม ANY ตรงนี้
from tektrasense_kipipe.data_processor import ComponentProcessor

@pytest.fixture
def mock_db():
    """Fixture for a mocked DatabaseManager instance."""
    db = MagicMock()
    db.get_category_id.return_value = 101 # สมมติว่าเจอ Category ID
    db.get_category_details.return_value = {"prefix": "RES", "parent_id": None}
    db.get_next_internal_part_id.return_value = "RES-0001"
    return db

@pytest.fixture
def processor(mock_db):
    """Fixture for a ComponentProcessor with a mocked DB."""
    return ComponentProcessor(mock_db)

@patch('tektrasense_kipipe.data_processor.supplier_apis')
def test_fetch_part_data_digikey_primary(mock_apis, processor, mock_db):
    """
    Tests the main fetch logic where DigiKey data is available and used as primary.
    """
    # 1. Arrange
    # จำลอง response จาก API
    mock_apis.call_digikey_api.return_value = {"ManufacturerProductNumber": "PN-DK", "ChildCategories": {"Name": "Resistors"}}
    mock_apis.call_mouser_api.return_value = {"ManufacturerPartNumber": "PN-MS"}
    
    # Mock process_and_format_data เพื่อทดสอบ fetch_part_data โดยเฉพาะ
    with patch.object(processor, '_process_and_format_data') as mock_process:
        mock_process.return_value = {"processed": "data"} # ข้อมูลจำลองที่ผ่านการ process
        
        # 2. Act
        result = processor.fetch_part_data("SOME-PN")

        # 3. Assert
        # ตรวจสอบว่าเรียก API ทั้งสอง
        mock_apis.call_digikey_api.assert_called_once_with("SOME-PN")
        mock_apis.call_mouser_api.assert_called_once_with("SOME-PN")
        
        # ตรวจสอบว่า get_category_id ถูกเรียกด้วยข้อมูลจาก DigiKey ก่อน
        mock_db.get_category_id.assert_called_once_with("DigiKey", "Resistors")
        
        # ตรวจสอบว่า _process_and_format_data ถูกเรียกด้วยข้อมูลดิบจาก DigiKey
        mock_process.assert_called_once()
        # ANY คือ placeholder สำหรับ mapper dict ที่ส่งเข้าไป
        mock_process.assert_called_with(mock_apis.call_digikey_api.return_value, ANY, 101)

        # ตรวจสอบว่ามีการรวมข้อมูลจาก Supplier 2 (Mouser) เข้าไปในผลลัพธ์
        assert result[0]['supplier_1'] == "DigiKey"
        assert result[0]['supplier_2'] == "Mouser"

@patch('tektrasense_kipipe.data_processor.supplier_apis')
def test_fetch_part_data_category_not_mapped(mock_apis, processor, mock_db):
    """
    Tests the scenario where a category is found on the supplier but not mapped in our DB.
    """
    # 1. Arrange
    mock_apis.call_digikey_api.return_value = {"ChildCategories": {"Name": "Unmapped Resistors"}}
    mock_apis.call_mouser_api.return_value = None
    
    # จำลองว่า DB ไม่เจอ category mapping
    mock_db.get_category_id.return_value = None

    # 2. Act
    result = processor.fetch_part_data("UNMAPPED-PN")

    # 3. Assert
    # ตรวจสอบว่ามีการพยายาม log unmapped category
    mock_db.add_unmapped_category.assert_called_once_with("DigiKey", "Unmapped Resistors")
    # ตรวจสอบว่าฟังก์ชันคืนค่า None เพราะหา category ไม่ได้
    assert result is None