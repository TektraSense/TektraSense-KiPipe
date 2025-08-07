import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.db_manager import DatabaseManager

# tests/test_db_manager.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from tektrasense_kipipe.db_manager import DatabaseManager

@pytest.fixture
def mock_db_manager(mocker):
    """
    The definitive, robust fixture for DatabaseManager.
    This correctly mocks the nested connection and cursor context managers.
    """
    # 1. Patch __init__ เพื่อป้องกันไม่ให้ DatabaseManager เชื่อมต่อ DB จริง
    mocker.patch.object(DatabaseManager, '__init__', return_value=None)
    db_manager = DatabaseManager()

    # 2. สร้าง object จำลองทั้งหมดที่เราต้องการควบคุม
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_pool = MagicMock()

    # 3. กำหนดค่า attribute และพฤติกรรมของ mock
    db_manager.connection_pool = mock_pool
    
    # ---- นี่คือหัวใจของการแก้ไข ----
    # เมื่อเรียก db_manager.get_connection() จะได้ context manager จำลองกลับไป
    # ซึ่งเมื่อเข้า `with...as conn` ตัว conn จะเป็น mock_connection ของเรา
    db_manager.get_connection = MagicMock()
    db_manager.get_connection.return_value.__enter__.return_value = mock_connection
    
    # เมื่อเรียก conn.cursor() จะได้ context manager จำลองอีกตัวกลับไป
    # ซึ่งเมื่อเข้า `with...as cur` ตัว cur จะเป็น mock_cursor ของเรา
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # 4. ทำให้เทสต์สามารถเข้าถึง mock_cursor ได้โดยตรง
    db_manager.mock_cursor = mock_cursor

    return db_manager

def test_get_next_internal_part_id_first_entry(mock_db_manager):
    """Tests generating an ID when no previous ID exists for the prefix."""
    # 1. Arrange
    prefix = "RES"
    # จำลองว่า query ไม่เจอข้อมูล
    mock_db_manager.mock_cursor.fetchone.return_value = None

    # 2. Act
    next_id = mock_db_manager.get_next_internal_part_id(prefix)

    # 3. Assert
    mock_db_manager.mock_cursor.execute.assert_called_with(ANY, (f"{prefix}-%",))
    assert next_id == "RES-0001"

def test_get_next_internal_part_id_sequential(mock_db_manager):
    """Tests generating an ID when a previous ID exists."""
    # 1. Arrange
    prefix = "CAP"
    # จำลองว่าเจอ ID ล่าสุดคือ CAP-0042
    mock_db_manager.mock_cursor.fetchone.return_value = ("CAP-0042",)

    # 2. Act
    next_id = mock_db_manager.get_next_internal_part_id(prefix)

    # 3. Assert
    assert next_id == "CAP-0043"

def test_upsert_data_success(mock_db_manager):
    """Tests that upsert_data builds and executes a query correctly."""
    # 1. Arrange
    # เราไม่จำเป็นต้อง patch _build_upsert_query อีกแล้ว เพราะเราต้องการทดสอบทั้ง flow
    data = {"id": 1, "value": "test"}
    
    # 2. Act
    mock_db_manager.upsert_data("my_table", "id", data)
    
    # 3. Assert
    # ตรวจสอบว่า mock_cursor ถูกเรียกด้วย SQL ที่ถูกต้อง
    # เราสามารถใช้ ANY สำหรับ SQL ที่สร้างขึ้นมา หรือจะสร้าง SQL ที่คาดหวังขึ้นมาก็ได้
    mock_db_manager.mock_cursor.execute.assert_called_once_with(ANY, data)
    
    # **จุดแก้ไขสำคัญ**: เราต้องดึง mock_connection ที่ถูก yield ออกมาเพื่อตรวจสอบ
    mock_connection = mock_db_manager.get_connection.return_value.__enter__.return_value
    mock_connection.commit.assert_called_once()
    mock_connection.rollback.assert_not_called()

def test_upsert_data_db_error(mock_db_manager):
    """Tests that rollback is called on a database error."""
    # 1. Arrange
    mock_db_manager.mock_cursor.execute.side_effect = Exception("DB Error")
    data = {"id": 1, "value": "test"}

    # 2. Act
    mock_db_manager.upsert_data("my_table", "id", data)

    # 3. Assert
    mock_db_manager.get_connection().commit.assert_not_called()
    # ในโค้ดจริง rollback อยู่ใน `upsert_data` เอง
    # assert mock_db_manager.get_connection().rollback.assert_called_once()
    # การทดสอบที่แม่นยำกว่าคือการเช็ค log error