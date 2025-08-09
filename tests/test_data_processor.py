# tests/test_data_processor.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.data_processor import ComponentProcessor

@pytest.fixture
def mock_db():
    """Fixture for a mocked DatabaseManager instance."""
    db = MagicMock()
    db.get_category_id.return_value = 101 # Simulate finding a category ID
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
    # Simulate responses from the APIs.
    mock_apis.call_digikey_api.return_value = {"ManufacturerProductNumber": "PN-DK", "ChildCategories": {"Name": "Resistors"}}
    mock_apis.call_mouser_api.return_value = {"ManufacturerPartNumber": "PN-MS"}
    
    # Mock _process_and_format_data to isolate the test to fetch_part_data's logic.
    with patch.object(processor, '_process_and_format_data') as mock_process:
        mock_process.return_value = {"processed": "data"} # Mocked processed data.
        
        # 2. Act
        result = processor.fetch_part_data("SOME-PN")

        # 3. Assert
        # Verify that both APIs were called.
        mock_apis.call_digikey_api.assert_called_once_with("SOME-PN")
        mock_apis.call_mouser_api.assert_called_once_with("SOME-PN")
        
        # Verify that get_category_id was called with data from DigiKey first.
        mock_db.get_category_id.assert_called_once_with("DigiKey", "Resistors")
        
        # Verify that _process_and_format_data was called with raw data from DigiKey.
        mock_process.assert_called_once()
        # ANY is a placeholder for the mapper dict that is passed in.
        mock_process.assert_called_with(mock_apis.call_digikey_api.return_value, ANY, 101)

        # Verify that data from Supplier 2 (Mouser) is included in the result.
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
    
    # Simulate the DB not finding a category mapping.
    mock_db.get_category_id.return_value = None

    # 2. Act
    result = processor.fetch_part_data("UNMAPPED-PN")

    # 3. Assert
    # Verify that an attempt was made to log the unmapped category.
    mock_db.add_unmapped_category.assert_called_once_with("DigiKey", "Unmapped Resistors")
    # Verify that the function returns None because the category could not be found.
    assert result is None