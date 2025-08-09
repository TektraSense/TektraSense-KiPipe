import pytest
from unittest.mock import MagicMock
import requests
from tektrasense_kipipe import supplier_apis

@pytest.fixture
def mock_env_vars(mocker):
    """Mocks all required environment variables for API calls."""
    mocker.patch('os.getenv', side_effect=lambda key: {
        "DIGIKEY_CLIENT_ID": "fake_client_id",
        "DIGIKEY_CLIENT_SECRET": "fake_client_secret",
        "MOUSER_API_KEY": "fake_mouser_key"
    }.get(key))

# --- DigiKey API Tests ---

def test_call_digikey_api_success(mocker, mock_env_vars):
    """Tests a successful DigiKey API call, including token exchange."""
    # 1. Arrange
    # Mock the response for the authentication token request
    mock_auth_resp = MagicMock()
    mock_auth_resp.status_code = 200
    mock_auth_resp.json.return_value = {"access_token": "fake_token"}

    # Mock the response for the part search request
    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {"Products": [{"ManufacturerProductNumber": "PN-123"}]}

    # Patch requests.post to return the mocked responses in sequence
    mocker.patch('requests.post', side_effect=[mock_auth_resp, mock_search_resp])

    # 2. Act
    result = supplier_apis.call_digikey_api("PN-123")

    # 3. Assert
    assert result is not None
    assert result["ManufacturerProductNumber"] == "PN-123"

def test_call_digikey_api_request_exception(mocker, mock_env_vars):
    """Tests DigiKey API call failure due to a requests.RequestException."""
    # 1. Arrange
    mocker.patch('requests.post', side_effect=requests.exceptions.RequestException("Network Error"))

    # 2. Act
    result = supplier_apis.call_digikey_api("PN-123")

    # 3. Assert
    assert result is None

# --- Mouser API Tests ---

def test_call_mouser_api_success(mocker, mock_env_vars):
    """Tests a successful Mouser API call where a matching part is found."""
    # 1. Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "SearchResults": {"Parts": [{"ManufacturerPartNumber": "PN-ABC"}]}
    }
    mocker.patch('requests.post', return_value=mock_resp)

    # 2. Act
    result = supplier_apis.call_mouser_api("PN-ABC")

    # 3. Assert
    assert result is not None
    assert result["ManufacturerPartNumber"] == "PN-ABC"

def test_call_mouser_api_no_parts_found(mocker, mock_env_vars):
    """Tests the Mouser API call when the search returns no parts."""
    # 1. Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200 # API call is successful but returns empty result
    mock_resp.json.return_value = {"SearchResults": {"Parts": []}}
    mocker.patch('requests.post', return_value=mock_resp)

    # 2. Act
    result = supplier_apis.call_mouser_api("PN-XYZ")

    # 3. Assert
    assert result is None