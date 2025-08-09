import pytest
from unittest.mock import patch, mock_open, ANY
import pandas as pd
from tektrasense_kipipe.commands import fetch

class Args:
    """A simple namespace for mocking argparse results."""
    def __init__(self, part_number=None, csv=None, spreadsheet=None, txt=None, column="part_number"):
        self.part_number = part_number
        self.csv = csv
        self.spreadsheet = spreadsheet
        self.txt = txt
        self.column = column

@patch('tektrasense_kipipe.commands.fetch.ComponentProcessor')
@patch('tektrasense_kipipe.commands.fetch.DatabaseManager')
@patch('tektrasense_kipipe.commands.fetch._process_part')
def test_run_fetch_from_csv(mock_process, mock_db, mock_proc_class, mocker):
    """Verifies that `run` correctly processes part numbers from a CSV file."""
    args = Args(csv="fake.csv", column="PartNo")
    mock_csv_content = "PartNo,OtherCol\nPN-1,abc\nPN-2,xyz"
    mocker.patch('builtins.open', mock_open(read_data=mock_csv_content))
    
    fetch.run(args)

    assert mock_process.call_count == 2
    mock_process.assert_any_call("PN-1", ANY, ANY)
    mock_process.assert_any_call("PN-2", ANY, ANY)

@patch('tektrasense_kipipe.commands.fetch.ComponentProcessor')
@patch('tektrasense_kipipe.commands.fetch.DatabaseManager')
@patch('tektrasense_kipipe.commands.fetch._process_part')
def test_run_fetch_from_spreadsheet(mock_process, mock_db, mock_proc_class, mocker):
    """Verifies that `run` correctly processes part numbers from a spreadsheet."""
    args = Args(spreadsheet="fake.xlsx", column="Part Number")
    mock_df = pd.DataFrame({"Part Number": ["PN-A", "PN-B"]})
    mocker.patch('pandas.read_excel', return_value=mock_df)

    fetch.run(args)

    assert mock_process.call_count == 2
    mock_process.assert_any_call("PN-A", ANY, ANY)
    mock_process.assert_any_call("PN-B", ANY, ANY)

@patch('tektrasense_kipipe.commands.fetch.ComponentProcessor')
@patch('tektrasense_kipipe.commands.fetch.DatabaseManager')
@patch('tektrasense_kipipe.commands.fetch._process_part')
def test_run_fetch_single_part_number(mock_process, mock_db, mock_proc_class):
    """Verifies that `run` correctly processes a single part number argument."""
    args = Args(part_number="SINGLE-PN-123")
    
    fetch.run(args)
    
    mock_process.assert_called_once_with("SINGLE-PN-123", ANY, ANY)