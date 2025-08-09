import pytest
from unittest.mock import MagicMock, ANY
from tektrasense_kipipe.db_manager import DatabaseManager

@pytest.fixture
def mock_db_manager(mocker):
    """
    Provides a robust mock of the DatabaseManager for testing.
    This fixture correctly mocks the nested connection and cursor context managers
    without making real database calls.
    """
    # 1. Patch __init__ to prevent the real DatabaseManager from connecting to a DB.
    mocker.patch.object(DatabaseManager, '__init__', return_value=None)
    db_manager = DatabaseManager()

    # 2. Create all the mock objects we need to control.
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_pool = MagicMock()

    # 3. Assign mock attributes and define their behavior.
    db_manager.connection_pool = mock_pool

    # --- This is the core of the mocking strategy ---
    # When db_manager.get_connection() is called, it returns a mock context manager.
    # When entering the `with...as conn` block, `conn` becomes our `mock_connection`.
    db_manager.get_connection = MagicMock()
    db_manager.get_connection.return_value.__enter__.return_value = mock_connection

    # Similarly, when conn.cursor() is called, it returns another mock context manager.
    # When entering the `with...as cur` block, `cur` becomes our `mock_cursor`.
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    # 4. Attach mocks to the manager instance for easy access within tests.
    db_manager.mock_cursor = mock_cursor
    db_manager.mock_connection = mock_connection # Makes testing commit/rollback easier

    return db_manager

def test_get_next_internal_part_id_first_entry(mock_db_manager):
    """Tests generating an ID when no previous ID exists for the given prefix."""
    # 1. Arrange
    prefix = "RES"
    # Simulate the query finding no existing part number.
    mock_db_manager.mock_cursor.fetchone.return_value = None

    # 2. Act
    next_id = mock_db_manager.get_next_internal_part_id(prefix)

    # 3. Assert
    mock_db_manager.mock_cursor.execute.assert_called_with(ANY, (f"{prefix}-%",))
    assert next_id == "RES-0001"

def test_get_next_internal_part_id_sequential(mock_db_manager):
    """Tests generating the next sequential ID when a previous ID exists."""
    # 1. Arrange
    prefix = "CAP"
    # Simulate the query finding the latest ID "CAP-0042".
    mock_db_manager.mock_cursor.fetchone.return_value = ("CAP-0042",)

    # 2. Act
    next_id = mock_db_manager.get_next_internal_part_id(prefix)

    # 3. Assert
    assert next_id == "CAP-0043"

def test_upsert_data_success(mock_db_manager):
    """Tests that upsert_data correctly builds and executes a query, then commits."""
    # 1. Arrange
    # We are testing the full flow, so we don't mock the internal _build_upsert_query.
    table_name = "my_table"
    conflict_target = "id"
    data = {"id": 1, "value": "test"}

    # 2. Act
    mock_db_manager.upsert_data(table_name, conflict_target, data)

    # 3. Assert
    # Check that execute was called with some SQL (ANY) and the data dictionary.
    mock_db_manager.mock_cursor.execute.assert_called_once_with(ANY, data)
    
    # Check that the transaction was committed and not rolled back.
    mock_db_manager.mock_connection.commit.assert_called_once()
    mock_db_manager.mock_connection.rollback.assert_not_called()

def test_upsert_data_db_error_triggers_rollback(mock_db_manager):
    """Tests that the connection is rolled back if a database error occurs."""
    # 1. Arrange
    mock_db_manager.mock_cursor.execute.side_effect = Exception("Simulated DB Error")
    data = {"id": 1, "value": "test"}

    # 2. Act
    # The method is expected to catch the exception and handle it gracefully.
    mock_db_manager.upsert_data("my_table", "id", data)

    # 3. Assert
    # Verify that the failed transaction was rolled back and not committed.
    mock_db_manager.mock_connection.rollback.assert_called_once()
    mock_db_manager.mock_connection.commit.assert_not_called()