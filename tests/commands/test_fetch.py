# tests/commands/test_fetch.py
import pytest
from unittest.mock import patch, mock_open, ANY # <-- เพิ่ม ANY
import pandas as pd
from tektrasense_kipipe.commands import fetch

# สร้าง Namespace จำลองสำหรับ args
class Args:
    def __init__(self, part_number=None, csv=None, spreadsheet=None, txt=None, column="part_number"):
        self.part_number = part_number
        self.csv = csv
        self.spreadsheet = spreadsheet
        self.txt = txt
        self.column = column

@patch('tektrasense_kipipe.commands.fetch._process_part')
def test_run_fetch_from_csv(mock_process_part, mocker):
    """Tests loading part numbers from a mocked CSV file."""
    # 1. Arrange
    args = Args(csv="fake.csv", column="PartNo")
    mock_csv_content = "PartNo,OtherCol\nPN-1,abc\nPN-2,xyz"
    mocker.patch('builtins.open', mock_open(read_data=mock_csv_content))
    mocker.patch('tektrasense_kipipe.commands.fetch.DatabaseManager')
    mocker.patch('tektrasense_kipipe.commands.fetch.ComponentProcessor')
    
    # 2. Act
    fetch.run(args)

    # 3. Assert
    assert mock_process_part.call_count == 2
    mock_process_part.assert_any_call("PN-1", ANY, ANY)
    mock_process_part.assert_any_call("PN-2", ANY, ANY)

@patch('tektrasense_kipipe.commands.fetch._process_part')
def test_run_fetch_from_spreadsheet(mock_process_part, mocker):
    """Tests loading part numbers from a mocked Excel file."""
    # 1. Arrange
    args = Args(spreadsheet="fake.xlsx", column="Part Number")
    # สร้าง DataFrame จำลอง
    mock_df = pd.DataFrame({"Part Number": ["PN-A", "PN-B"]})
    mocker.patch('pandas.read_excel', return_value=mock_df)
    mocker.patch('tektrasense_kipipe.commands.fetch.DatabaseManager')
    mocker.patch('tektrasense_kipipe.commands.fetch.ComponentProcessor')

    # 2. Act
    fetch.run(args)

    # 3. Assert
    assert mock_process_part.call_count == 2
    mock_process_part.assert_any_call("PN-A", ANY, ANY)
    mock_process_part.assert_any_call("PN-B", ANY, ANY)