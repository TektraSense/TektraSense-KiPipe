# tests/commands/test_link_footprint.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.commands import link_footprint

# สร้าง Namespace จำลองสำหรับ args
class Args:
    def __init__(self, part_number):
        self.part_number = part_number

@pytest.fixture
def mock_db(mocker):
    """A fixture that provides a mocked DatabaseManager instance."""
    db_instance = MagicMock()
    db_instance.connection_pool = True
    mocker.patch('tektrasense_kipipe.commands.link_footprint.DatabaseManager', return_value=db_instance)
    return db_instance

def test_auto_link_on_single_approved_footprint(mock_db):
    """Tests happy path: auto-linking when exactly one footprint is found."""
    # 1. Arrange
    args = Args(part_number="PART-A")
    mock_db.fetch_all.return_value = [("Resistor_SMD:R_0805",)] # คืนค่า 1 รายการ
    
    # 2. Act
    link_footprint.run(args)
    
    # 3. Assert
    mock_db.fetch_all.assert_called_once()
    mock_db.execute_query.assert_called_once_with(ANY, ("Resistor_SMD:R_0805", "PART-A"))

def test_no_link_when_no_approved_footprints_found(mock_db, caplog):
    """Tests that no action is taken if no approved footprints are found."""
    # 1. Arrange
    args = Args(part_number="PART-C")
    mock_db.fetch_all.return_value = [] # คืนค่า list ว่าง
    
    # 2. Act
    link_footprint.run(args)
    
    # 3. Assert
    mock_db.execute_query.assert_not_called()
    assert "No approved footprints found for 'PART-C'" in caplog.text

@patch('builtins.input', side_effect=['5', 'invalid', '2', '3']) # จำลองการพิมพ์: ผิด -> ผิด -> ถูก
def test_interactive_choice_with_invalid_then_valid_input(mock_input, mock_db):
    """Tests interactive mode, ensuring it handles invalid input before a valid one."""
    # 1. Arrange
    args = Args(part_number="PART-B")
    approved_fps = [("FP:A",), ("FP:B",), ("FP:C",)]
    mock_db.fetch_all.return_value = approved_fps
    
    # 2. Act
    link_footprint.run(args)
    
    # 3. Assert
    assert mock_input.call_count == 3 # ควรจะถาม 3 ครั้ง
    # ตรวจสอบว่าสุดท้ายแล้ว update ด้วยตัวเลือกที่ถูกต้อง (อันที่ 2)
    mock_db.execute_query.assert_called_once_with(ANY, ("FP:B", "PART-B"))

@patch('builtins.input', return_value='q')
def test_interactive_choice_user_quits(mock_input, mock_db):
    """Tests that no action is taken if the user quits the interactive prompt."""
    # 1. Arrange
    args = Args(part_number="PART-B")
    approved_fps = [("FP:A",), ("FP:B",)]
    mock_db.fetch_all.return_value = approved_fps
    
    # 2. Act
    link_footprint.run(args)
    
    # 3. Assert
    mock_input.assert_called_once()
    mock_db.execute_query.assert_not_called()