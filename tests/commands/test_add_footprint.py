import pytest
from unittest.mock import MagicMock, patch
from tektrasense_kipipe.commands import add_footprint

class Args:
    """A simple namespace for mocking argparse results."""
    def __init__(self, part_number, footprint):
        self.part_number = part_number
        self.footprint = footprint

@pytest.fixture
def mock_filesystem(mocker):
    """A fixture to create a virtual filesystem for footprint libraries."""
    def _setup(file_content, found_files):
        mocker.patch('tektrasense_kipipe.config.FOOTPRINT_SEARCH_PATHS', ['/fake/lib'])
        mocker.patch('os.walk', return_value=[('/fake/lib', [], found_files)])
        mocker.patch('builtins.open', mocker.mock_open(read_data=file_content))
    return _setup

@pytest.mark.parametrize(
    "footprint_link, file_content, found_files, expected_result, expected_log",
    [
        ("Resistor_SMD:R_0805", '(footprint "R_0805" (layer F.Cu))', ["Resistor_SMD.kicad_mod"], True, None),
        ("Resistor_SMD:R_1206", '(footprint "R_0805")', ["Resistor_SMD.kicad_mod"], False, None),
        ("Other_Lib:Other_FP", '', [], False, None),
        ("InvalidFormat", '', [], False, "Invalid footprint link format: 'InvalidFormat'."),
    ]
)
def test_verify_footprint_exists(mock_filesystem, caplog, footprint_link, file_content, found_files, expected_result, expected_log):
    """Tests _verify_footprint_exists with various scenarios."""
    mock_filesystem(file_content, found_files)
    
    exists, _ = add_footprint._verify_footprint_exists(footprint_link)
    
    assert exists is expected_result
    if expected_log:
        assert expected_log in caplog.text

@patch('tektrasense_kipipe.commands.add_footprint.DatabaseManager')
@patch('tektrasense_kipipe.commands.add_footprint._verify_footprint_exists', return_value=(True, "/fake/path/Lib.kicad_mod"))
def test_run_when_validation_passes_updates_db(mock_verify, MockDB):
    """Tests that run() calls the database when validation succeeds."""
    args = Args("PN-123", "Lib:FP-Valid")
    db_instance = MockDB.return_value
    db_instance.connection_pool = True
    
    add_footprint.run(args)
    
    db_instance.execute_query.assert_called_once()

@patch('tektrasense_kipipe.commands.add_footprint.DatabaseManager')
@patch('tektrasense_kipipe.commands.add_footprint._verify_footprint_exists', return_value=(False, None))
def test_run_when_validation_fails_does_not_update_db(mock_verify, MockDB):
    """Tests that run() does NOT call the database when validation fails."""
    args = Args("PN-456", "Lib:FP-Invalid")
    db_instance = MockDB.return_value
    db_instance.connection_pool = True
    
    add_footprint.run(args)
    
    db_instance.execute_query.assert_not_called()