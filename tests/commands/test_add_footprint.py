# tests/commands/test_add_footprint.py
import pytest
from unittest.mock import MagicMock, patch
from tektrasense_kipipe.commands import add_footprint

# สร้าง Namespace จำลองสำหรับ args
class Args:
    def __init__(self, part_number, footprint):
        self.part_number = part_number
        self.footprint = footprint

@pytest.fixture
def mock_filesystem(mocker):
    """
    A fixture to create a virtual filesystem for footprint libraries.
    Yields a function to set up the file content and found files.
    """
    def _setup(file_content, found_files):
        mocker.patch('tektrasense_kipipe.config.FOOTPRINT_SEARCH_PATHS', ['/fake/lib'])
        mocker.patch('os.walk', return_value=[('/fake/lib', [], found_files)])
        mocker.patch('builtins.open', mocker.mock_open(read_data=file_content))
    return _setup

# --- ทดสอบ _verify_footprint_exists ด้วย Parameterization ---
@pytest.mark.parametrize(
    "footprint_link, file_content, found_files, expected_result, expected_log",
    [
        # Case 1: Happy Path - เจอ Footprint ในไฟล์
        ("Resistor_SMD:R_0805", '(footprint "R_0805" (layer F.Cu))', ["Resistor_SMD.kicad_mod"], True, None),
        # Case 2: ไม่เจอ Footprint ในไฟล์
        ("Resistor_SMD:R_1206", '(footprint "R_0805")', ["Resistor_SMD.kicad_mod"], False, None),
        # Case 3: ไม่เจอไฟล์ Library เลย
        ("Other_Lib:Other_FP", '', [], False, None),
        # Case 4: Format ของ Link ผิด
        ("InvalidFormat", '', [], False, "Invalid footprint link format: 'InvalidFormat'."),
    ]
)
def test_verify_footprint_exists(mock_filesystem, caplog, footprint_link, file_content, found_files, expected_result, expected_log):
    """
    Tests _verify_footprint_exists with various scenarios using parameterization.
    """
    # 1. Arrange
    mock_filesystem(file_content, found_files)
    
    # 2. Act
    exists, _ = add_footprint._verify_footprint_exists(footprint_link)
    
    # 3. Assert
    assert exists is expected_result
    if expected_log:
        assert expected_log in caplog.text

# --- ทดสอบ `run` ฟังก์ชันหลัก (ยังคงเดิม แต่ดูสะอาดขึ้นเมื่อใช้ fixture) ---
@patch('tektrasense_kipipe.commands.add_footprint._verify_footprint_exists')
@patch('tektrasense_kipipe.commands.add_footprint.DatabaseManager')
def test_run_when_validation_passes_updates_db(MockDB, mock_verify):
    """Tests that run() calls the database when validation succeeds."""
    # 1. Arrange
    args = Args("PN-123", "Lib:FP-Valid")
    mock_verify.return_value = (True, "/fake/path/Lib.kicad_mod") # จำลองว่าเจอ
    db_instance = MockDB.return_value
    db_instance.connection_pool = True
    
    # 2. Act
    add_footprint.run(args)
    
    # 3. Assert
    db_instance.execute_query.assert_called_once()

@patch('tektrasense_kipipe.commands.add_footprint._verify_footprint_exists')
@patch('tektrasense_kipipe.commands.add_footprint.DatabaseManager')
def test_run_when_validation_fails_does_not_update_db(MockDB, mock_verify):
    """Tests that run() does NOT call the database when validation fails."""
    # 1. Arrange
    args = Args("PN-456", "Lib:FP-Invalid")
    mock_verify.return_value = (False, None) # จำลองว่าไม่เจอ
    db_instance = MockDB.return_value
    db_instance.connection_pool = True
    
    # 2. Act
    add_footprint.run(args)
    
    # 3. Assert
    db_instance.execute_query.assert_not_called()