# tests/commands/test_add_symbol.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.commands import add_symbol

# สร้าง Namespace จำลองสำหรับ args
class Args:
    def __init__(self, part_number=None, csv=None, spreadsheet=None, txt=None, col_part="Part Number", force=False):
        self.part_number = part_number
        self.csv = csv
        self.spreadsheet = spreadsheet
        self.txt = txt
        self.col_part = col_part
        self.force = force

@pytest.fixture
def mock_db_manager(mocker):
    """Fixture to create a fully mocked DatabaseManager instance."""
    db_manager = MagicMock()
    db_manager.connection_pool = True
    return db_manager

# --- Test the main logic function: _find_and_link_symbol ---

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_single_best_match_non_interactive(mock_verify, mock_db_manager):
    """
    Tests the happy path where one best symbol is found and linked automatically.
    """
    # 1. Arrange
    part_number = "MCP6001T-I/OT"
    # จำลองว่า DB เจอข้อมูล component
    mock_db_manager.get_component_symbol_info.return_value = ("IC OPAMP SOT23-5", None)
    # จำลองผลลัพธ์จาก DB ที่มี potential symbols
    mock_db_manager.fetch_all.return_value = [
        ("Device", "MCP6001"),          # Match length 7
        ("Device", "MCP6002"),          # Match length 7
        ("Connector", "CONN_01x02"),    # No match
        ("Device", "MCP600"),           # Match length 6
    ]

    # 2. Act
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    # 3. Assert
    # ในโหมด non-interactive เมื่อเจอหลาย match ที่ดีที่สุด (MCP6001, MCP6002) มันควรจะเตือนและไม่ทำอะไร
    mock_db_manager.execute_query.assert_called_once_with(ANY, ('Device:MCP6001', part_number))

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_single_unique_match_non_interactive(mock_verify, mock_db_manager, mocker):
    """
    Tests auto-linking when there is only ONE best match.
    """
    # 1. Arrange
    part_number = "LM358ADR"
    mock_db_manager.get_component_symbol_info.return_value = ("Dual Op-Amp", None)
    mock_db_manager.fetch_all.return_value = [
        ("Amplifier_Operational", "LM358A"), # Best match, length 6
        ("Amplifier_Operational", "LM358"),  # Shorter match, length 5
        ("Regulator_Linear", "LM1117"),
    ]
    mock_log_info = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.info')

    # 2. Act
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    # 3. Assert
    # ตรวจสอบว่ามีการ update DB ด้วย match ที่ดีที่สุด
    expected_link = "Amplifier_Operational:LM358A"
    mock_db_manager.execute_query.assert_called_once_with(ANY, (expected_link, part_number))
    mock_log_info.assert_any_call(f"Found exactly one match: '{expected_link}'.")

@patch('builtins.input')
@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_interactive_choice(mock_verify, mock_input, mock_db_manager):
    # ... Arrange ...
    part_number = "MCP6001T-I/OT"
    mock_db_manager.get_component_symbol_info.return_value = ("IC OPAMP SOT23-5", None)

    # **จุดแก้ไขสำคัญ**: ทำให้ผลลัพธ์จาก DB มีคะแนนเท่ากัน 2 ตัว
    mock_db_manager.fetch_all.return_value = [
        ("Device", "MCP6001A"), # Match length 7
        ("Device", "MCP6001B"), # Match length 7
        ("Device", "MCP600"),   # Match length 6
    ]

    # กำหนด "บทพูด" ให้ถูกต้อง
    mock_input.side_effect = ['3', '2']

    # Act
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=True)

    # Assert
    assert mock_input.call_count == 2
    # ตรวจสอบว่าเลือกตัวที่ 2 ถูกต้อง (MCP6001B)
    expected_link = "Device:MCP6001B"
    mock_db_manager.execute_query.assert_called_once_with(ANY, (expected_link, part_number))

def test_find_and_link_symbol_already_exists_no_force(mock_db_manager, mocker):
    """
    Tests that the function exits early if a symbol exists and --force is not used.
    """
    # 1. Arrange
    part_number = "EXISTING-PART"
    # จำลองว่า DB คืนค่า symbol ที่มีอยู่แล้ว
    mock_db_manager.get_component_symbol_info.return_value = ("Some Desc", "Existing:Symbol")
    mock_log_warning = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.warning')

    # 2. Act
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    # 3. Assert
    # ตรวจสอบว่าไม่มีการเรียก fetch_all หรือ execute_query
    mock_db_manager.fetch_all.assert_not_called()
    mock_db_manager.execute_query.assert_not_called()
    mock_log_warning.assert_called_once_with("Part 'EXISTING-PART' already has symbol 'Existing:Symbol'. Use --force to overwrite.")

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=False)
def test_find_and_link_symbol_final_validation_fails(mock_verify, mock_db_manager, mocker):
    """
    Tests that the DB is not updated if the chosen symbol fails the final filesystem check.
    """
    # 1. Arrange
    part_number = "LM358ADR"
    mock_db_manager.get_component_symbol_info.return_value = ("Dual Op-Amp", None)
    mock_db_manager.fetch_all.return_value = [("Amplifier_Operational", "LM358A")]
    mock_log_error = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.error')
    
    # 2. Act
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)
    
    # 3. Assert
    # ตรวจสอบว่ามีการเรียก _verify_symbol_exists
    mock_verify.assert_called_once_with("Amplifier_Operational:LM358A")
    # ตรวจสอบว่า "ไม่ได้" update DB
    mock_db_manager.execute_query.assert_not_called()
    mock_log_error.assert_called_once_with("Final check failed. The selected symbol 'Amplifier_Operational:LM358A' does not seem to exist in the library files.")

# --- Test the main run function ---

@patch('tektrasense_kipipe.commands.add_symbol._find_and_link_symbol')
@patch('tektrasense_kipipe.commands.add_symbol.DatabaseManager')
def test_run_with_single_part_number(MockDB, mock_find_link):
    """Tests that `run` calls the processing function for a single part number."""
    # 1. Arrange
    args = Args(part_number="PN-123", force=True)
    
    # 2. Act
    add_symbol.run(args)
    
    # 3. Assert
    mock_find_link.assert_called_once_with("PN-123", True, ANY, is_interactive=True)

@patch('tektrasense_kipipe.commands.add_symbol._load_parts_from_file', return_value=["PN-A", "PN-B"])
@patch('tektrasense_kipipe.commands.add_symbol._find_and_link_symbol')
@patch('tektrasense_kipipe.commands.add_symbol.DatabaseManager')
def test_run_with_csv_file(MockDB, mock_find_link, mock_load_file):
    """Tests that `run` calls the processing function for each part from a file."""
    # 1. Arrange
    args = Args(csv="parts.csv", force=False)

    # 2. Act
    add_symbol.run(args)

    # 3. Assert
    # ตรวจสอบว่ามีการเรียก _load_parts_from_file
    mock_load_file.assert_called_once_with("parts.csv", None, None, "Part Number")
    
    # ตรวจสอบว่ามีการเรียก _find_and_link_symbol สำหรับแต่ละ part number
    assert mock_find_link.call_count == 2
    mock_find_link.assert_any_call("PN-A", False, ANY, is_interactive=False)
    mock_find_link.assert_any_call("PN-B", False, ANY, is_interactive=False)