import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.commands import add_symbol

class Args:
    """A simple namespace for mocking argparse results."""
    def __init__(self, part_number=None, csv=None, spreadsheet=None, txt=None, col_part="Part Number", force=False):
        self.part_number = part_number
        self.csv = csv
        self.spreadsheet = spreadsheet
        self.txt = txt
        self.col_part = col_part
        self.force = force

@pytest.fixture
def mock_db_manager(mocker):
    """Provides a mocked DatabaseManager instance."""
    db_manager = MagicMock()
    db_manager.connection_pool = True
    return db_manager

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_single_best_match_non_interactive(mock_verify, mock_db_manager):
    """Tests that the first best match is chosen in non-interactive mode."""
    part_number = "MCP6001T-I/OT"
    mock_db_manager.get_component_symbol_info.return_value = ("IC OPAMP SOT23-5", None)
    mock_db_manager.fetch_all.return_value = [
        ("Device", "MCP6001"),
        ("Device", "MCP6002"),
        ("Connector", "CONN_01x02"),
        ("Device", "MCP600"),
    ]

    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    mock_db_manager.execute_query.assert_called_once_with(ANY, ('Device:MCP6001', part_number))

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_single_unique_match_non_interactive(mock_verify, mock_db_manager, mocker):
    """Tests auto-linking when there is only ONE best match."""
    part_number = "LM358ADR"
    mock_db_manager.get_component_symbol_info.return_value = ("Dual Op-Amp", None)
    mock_db_manager.fetch_all.return_value = [
        ("Amplifier_Operational", "LM358A"),
        ("Amplifier_Operational", "LM358"),
        ("Regulator_Linear", "LM1117"),
    ]
    mock_log_info = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.info')

    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    expected_link = "Amplifier_Operational:LM358A"
    mock_db_manager.execute_query.assert_called_once_with(ANY, (expected_link, part_number))
    mock_log_info.assert_any_call(f"Found exactly one match: '{expected_link}'.")

@patch('builtins.input')
@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=True)
def test_find_and_link_symbol_interactive_choice(mock_verify, mock_input, mock_db_manager):
    """Tests user selection from multiple choices in interactive mode."""
    part_number = "MCP6001T-I/OT"
    mock_db_manager.get_component_symbol_info.return_value = ("IC OPAMP SOT23-5", None)
    mock_db_manager.fetch_all.return_value = [
        ("Device", "MCP6001A"),
        ("Device", "MCP6001B"),
        ("Device", "MCP600"),
    ]
    mock_input.side_effect = ['3', '2']

    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=True)

    assert mock_input.call_count == 2
    expected_link = "Device:MCP6001B"
    mock_db_manager.execute_query.assert_called_once_with(ANY, (expected_link, part_number))

def test_find_and_link_symbol_already_exists_no_force(mock_db_manager, mocker):
    """Tests that the function exits early if a symbol exists and --force is not used."""
    part_number = "EXISTING-PART"
    mock_db_manager.get_component_symbol_info.return_value = ("Some Desc", "Existing:Symbol")
    mock_log_warning = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.warning')

    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)

    mock_db_manager.fetch_all.assert_not_called()
    mock_db_manager.execute_query.assert_not_called()
    mock_log_warning.assert_called_once_with("Part 'EXISTING-PART' already has symbol 'Existing:Symbol'. Use --force to overwrite.")

@patch('tektrasense_kipipe.commands.add_symbol._verify_symbol_exists', return_value=False)
def test_find_and_link_symbol_final_validation_fails(mock_verify, mock_db_manager, mocker):
    """Tests that the DB is not updated if the chosen symbol fails the final filesystem check."""
    part_number = "LM358ADR"
    mock_db_manager.get_component_symbol_info.return_value = ("Dual Op-Amp", None)
    mock_db_manager.fetch_all.return_value = [("Amplifier_Operational", "LM358A")]
    mock_log_error = mocker.patch('tektrasense_kipipe.commands.add_symbol.log.error')
    
    add_symbol._find_and_link_symbol(part_number, force=False, db_manager=mock_db_manager, is_interactive=False)
    
    mock_verify.assert_called_once_with("Amplifier_Operational:LM358A")
    mock_db_manager.execute_query.assert_not_called()
    mock_log_error.assert_called_once_with("Final check failed. The selected symbol 'Amplifier_Operational:LM358A' does not seem to exist in the library files.")

@patch('tektrasense_kipipe.commands.add_symbol._find_and_link_symbol')
@patch('tektrasense_kipipe.commands.add_symbol.DatabaseManager')
def test_run_with_single_part_number(MockDB, mock_find_link):
    """Tests that `run` calls the processing function for a single part number."""
    args = Args(part_number="PN-123", force=True)
    
    add_symbol.run(args)
    
    mock_find_link.assert_called_once_with("PN-123", True, ANY, is_interactive=True)

@patch('tektrasense_kipipe.commands.add_symbol._load_parts_from_file', return_value=["PN-A", "PN-B"])
@patch('tektrasense_kipipe.commands.add_symbol._find_and_link_symbol')
@patch('tektrasense_kipipe.commands.add_symbol.DatabaseManager')
def test_run_with_csv_file(MockDB, mock_find_link, mock_load_file):
    """Tests that `run` calls the processing function for each part from a file."""
    args = Args(csv="parts.csv", force=False)

    add_symbol.run(args)
    
    mock_load_file.assert_called_once_with("parts.csv", None, None, "Part Number")
    assert mock_find_link.call_count == 2
    mock_find_link.assert_any_call("PN-A", False, ANY, is_interactive=False)
    mock_find_link.assert_any_call("PN-B", False, ANY, is_interactive=False)