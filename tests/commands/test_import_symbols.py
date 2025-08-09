import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from tektrasense_kipipe.commands import import_symbols

# A simple namespace for mocking argparse results
class Args:
    def __init__(self, file=None, directory=None):
        self.file = file
        self.directory = directory

@pytest.fixture
def mock_db_manager(mocker):
    """Provides a mocked DatabaseManager instance."""
    db_instance = MagicMock()
    db_instance.connection_pool = True
    mocker.patch('tektrasense_kipipe.commands.import_symbols.DatabaseManager', return_value=db_instance)
    return db_instance

@pytest.fixture
def mock_filesystem(mocker):
    """Provides a fixture to mock the filesystem for finding symbol files."""
    mocker.patch('tektrasense_kipipe.config.SYMBOL_SEARCH_PATHS', ['/fake/lib/path'])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('pathlib.Path.is_file', return_value=True)
    mocker.patch('pathlib.Path.is_dir', return_value=True)
    mock_walk = mocker.patch('os.walk')
    return mock_walk

def test_find_single_file_success(mock_filesystem):
    """Tests that a single file can be found successfully."""
    result = import_symbols._find_single_file("Device.kicad_sym")
    assert result == Path("/fake/lib/path/Device.kicad_sym")

def test_find_all_sym_files_in_directory(mock_filesystem):
    """Tests recursive finding of all .kicad_sym files."""
    mock_filesystem.return_value = [
        ('/fake/symbols', [], ['Device.kicad_sym']),
        ('/fake/symbols/sub', [], ['Connector.kicad_sym']),
    ]
    result = import_symbols._find_all_sym_files("/fake/symbols")
    assert len(result) == 2
    assert Path('/fake/symbols/sub/Connector.kicad_sym') in result

def test_parse_and_update_db_success(mocker, mock_db_manager):
    """Tests the core parsing and database upsert logic."""
    mock_sym_content = """
    (kicad_symbol_lib
      (symbol "SYMBOL_A"
        (property "Description" "First test symbol" (id 0))
        (property "Datasheet" "http://example.com/a.pdf" (id 2))
        (property "ki_keywords" "diode generic" (id 3))
      )
      (symbol "SYMBOL_B"
        (property "Description" "Second test symbol" (id 0))
        (property "Datasheet" "~" (id 2))
      )
    )
    """
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_sym_content))
    mock_db_manager.upsert_symbol.return_value = True

    summary = import_symbols._parse_and_update_db(Path("/fake/lib/Device.kicad_sym"), mock_db_manager)

    assert summary['symbols'] == 2
    assert summary['updated'] == 2
    assert summary['failed'] == 0
    
    # Verify the data passed to the database
    first_call_args = mock_db_manager.upsert_symbol.call_args_list[0].args[0]
    assert first_call_args['symbol_name'] == 'SYMBOL_A'
    assert first_call_args['library_nickname'] == 'Device'
    assert "diode generic" in first_call_args['keywords']

def test_run_with_file_argument(mocker, mock_db_manager):
    """Tests the main run function when called with a single file."""
    args = Args(file="Device.kicad_sym")
    mock_parse = mocker.patch('tektrasense_kipipe.commands.import_symbols._parse_and_update_db')
    mock_find = mocker.patch('tektrasense_kipipe.commands.import_symbols._find_single_file', return_value=Path("found_file"))
    
    import_symbols.run(args)
    
    mock_find.assert_called_once_with("Device.kicad_sym")
    mock_parse.assert_called_once_with(Path("found_file"), mock_db_manager)

def test_run_with_directory_argument(mocker, mock_db_manager):
    """Tests the main run function when called with a directory."""
    args = Args(directory="/fake/symbols")
    found_files = [Path("file1.kicad_sym"), Path("file2.kicad_sym")]
    
    mock_parse = mocker.patch('tektrasense_kipipe.commands.import_symbols._parse_and_update_db')
    mock_find = mocker.patch('tektrasense_kipipe.commands.import_symbols._find_all_sym_files', return_value=found_files)
    
    import_symbols.run(args)

    mock_find.assert_called_once_with("/fake/symbols")
    assert mock_parse.call_count == 2