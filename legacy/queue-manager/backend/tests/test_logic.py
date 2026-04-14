"""
Unit tests for TurnRulesService business logic.

Tests use mocked Firestore functions to test stateless async service.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.turn_rules import (
    TurnRulesService,
    TechnicianEntity,
    TechnicianNotFoundError,
    TechnicianNotAvailableError,
    NoAvailableTechniciansError,
)


# --- Helper to create mock technician data ---

def make_tech(id: int, name: str, status: str = "AVAILABLE", 
              queue_position: int = 1, is_active: bool = True) -> dict:
    """Create a technician dict for mocking."""
    return {
        "id": id,
        "name": name,
        "status": status,
        "queue_position": queue_position,
        "is_active": is_active,
        "status_start_time": None
    }


# --- Tests ---

@pytest.mark.asyncio
async def test_get_next_tech_returns_lowest_position():
    """Next available tech should be the one with lowest queue_position."""
    service = TurnRulesService()
    
    # Mock returns Bob (position 1, available, active)
    mock_tech = make_tech(2, "Bob", "AVAILABLE", 1, True)
    
    with patch("app.database.get_next_available_technician", 
               new_callable=AsyncMock, return_value=mock_tech):
        next_tech = await service.get_next_tech()
    
    assert next_tech is not None
    assert next_tech.id == 2
    assert next_tech.name == "Bob"


@pytest.mark.asyncio
async def test_get_next_tech_none_available():
    """Should return None when no technicians are available."""
    service = TurnRulesService()
    
    with patch("app.database.get_next_available_technician",
               new_callable=AsyncMock, return_value=None):
        result = await service.get_next_tech()
    
    assert result is None


@pytest.mark.asyncio
async def test_get_tech_by_id():
    """Should return technician when found."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice")
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=mock_tech):
        tech = await service.get_tech_by_id(1)
    
    assert tech is not None
    assert tech.id == 1
    assert tech.name == "Alice"


@pytest.mark.asyncio
async def test_get_tech_by_id_not_found():
    """Should return None when technician not found."""
    service = TurnRulesService()
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=None):
        tech = await service.get_tech_by_id(999)
    
    assert tech is None


@pytest.mark.asyncio
async def test_get_tech_by_id_or_raise_not_found():
    """Should raise TechnicianNotFoundError when not found."""
    service = TurnRulesService()
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=None):
        with pytest.raises(TechnicianNotFoundError):
            await service.get_tech_by_id_or_raise(999)


@pytest.mark.asyncio
async def test_add_technician():
    """Adding a technician should create a new entry at the bottom of queue."""
    service = TurnRulesService()
    
    with patch("app.database.get_next_technician_id",
               new_callable=AsyncMock, return_value=1), \
         patch("app.database.get_technician_count",
               new_callable=AsyncMock, return_value=0), \
         patch("app.database.save_technician",
               new_callable=AsyncMock, return_value=1):
        
        new_tech = await service.add_technician("Alice")
    
    assert new_tech.name == "Alice"
    assert new_tech.id == 1
    assert new_tech.queue_position == 1
    assert new_tech.status == "AVAILABLE"
    assert new_tech.is_active is False


@pytest.mark.asyncio
async def test_remove_technician():
    """Removing a technician should delete from Firestore and repack positions."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice")
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=mock_tech), \
         patch("app.database.delete_technician",
               new_callable=AsyncMock) as mock_delete, \
         patch("app.database.repack_queue_positions",
               new_callable=AsyncMock) as mock_repack:
        
        await service.remove_technician(1)
    
    mock_delete.assert_awaited_once_with(1)
    mock_repack.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_technician_not_found_raises():
    """Removing a non-existent technician should raise TechnicianNotFoundError."""
    service = TurnRulesService()
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=None):
        with pytest.raises(TechnicianNotFoundError):
            await service.remove_technician(999)


@pytest.mark.asyncio
async def test_assign_tech_marks_as_busy():
    """Assigning a tech should mark them as BUSY."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice", "AVAILABLE")
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=mock_tech), \
         patch("app.database.update_technician_fields",
               new_callable=AsyncMock, return_value=True):
        
        assigned = await service.assign_tech(1)
    
    assert assigned.status == "BUSY"


@pytest.mark.asyncio
async def test_assign_tech_not_found_raises():
    """Assigning a non-existent tech should raise TechnicianNotFoundError."""
    service = TurnRulesService()
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=None):
        with pytest.raises(TechnicianNotFoundError):
            await service.assign_tech(999)


@pytest.mark.asyncio
async def test_assign_tech_not_available_raises():
    """Assigning a busy tech should raise TechnicianNotAvailableError."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice", "BUSY")
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=mock_tech):
        with pytest.raises(TechnicianNotAvailableError):
            await service.assign_tech(1)


@pytest.mark.asyncio
async def test_assign_next_available_raises_when_empty():
    """Should raise NoAvailableTechniciansError when queue is empty."""
    service = TurnRulesService()
    
    with patch("app.database.get_next_available_technician",
               new_callable=AsyncMock, return_value=None):
        with pytest.raises(NoAvailableTechniciansError):
            await service.assign_next_available()


@pytest.mark.asyncio
async def test_complete_turn_moves_to_bottom():
    """Completing a turn should move technician to bottom of queue."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice", "BUSY", 1)
    mock_tech_updated = make_tech(1, "Alice", "AVAILABLE", 2)
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, side_effect=[mock_tech, mock_tech_updated]), \
         patch("app.database.get_max_queue_position",
               new_callable=AsyncMock, return_value=1), \
         patch("app.database.update_technician_fields",
               new_callable=AsyncMock), \
         patch("app.database.repack_queue_positions",
               new_callable=AsyncMock):
        
        tech = await service.handle_tech_completion(1)
    
    assert tech.status == "AVAILABLE"
    assert tech.queue_position == 2


@pytest.mark.asyncio
async def test_toggle_active_status():
    """Toggle should switch is_active state."""
    service = TurnRulesService()
    mock_tech = make_tech(1, "Alice", is_active=False)
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, return_value=mock_tech), \
         patch("app.database.update_technician_fields",
               new_callable=AsyncMock):
        
        tech = await service.toggle_active_status(1)
    
    assert tech.is_active is True


@pytest.mark.asyncio
async def test_take_break():
    """Taking a break should set status to ON_BREAK."""
    service = TurnRulesService()
    mock_tech_before = make_tech(1, "Alice", "AVAILABLE")
    mock_tech_after = make_tech(1, "Alice", "ON_BREAK")
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, side_effect=[mock_tech_before, mock_tech_after]), \
         patch("app.database.update_technician_fields",
               new_callable=AsyncMock):
        
        tech = await service.take_break(1)
    
    assert tech.status == "ON_BREAK"


@pytest.mark.asyncio
async def test_return_from_break():
    """Returning from break should set status to AVAILABLE and move to bottom."""
    service = TurnRulesService()
    mock_tech_before = make_tech(1, "Alice", "ON_BREAK", 1)
    mock_tech_after = make_tech(1, "Alice", "AVAILABLE", 2)
    
    with patch("app.database.get_technician",
               new_callable=AsyncMock, side_effect=[mock_tech_before, mock_tech_after]), \
         patch("app.database.get_max_queue_position",
               new_callable=AsyncMock, return_value=1), \
         patch("app.database.update_technician_fields",
               new_callable=AsyncMock), \
         patch("app.database.repack_queue_positions",
               new_callable=AsyncMock):
        
        tech = await service.return_from_break(1)
    
    assert tech.status == "AVAILABLE"
    assert tech.queue_position == 2


@pytest.mark.asyncio
async def test_reorder_queue():
    """Reordering should update queue positions based on new order."""
    service = TurnRulesService()
    
    mock_techs = [
        make_tech(1, "Alice", queue_position=1),
        make_tech(2, "Bob", queue_position=2),
        make_tech(3, "Charlie", queue_position=3),
    ]
    
    with patch("app.database.load_technicians",
               new_callable=AsyncMock, return_value=mock_techs), \
         patch("app.database.save_all_technicians",
               new_callable=AsyncMock) as mock_save:
        
        await service.reorder_queue([2, 3, 1])
    
    # Verify save was called with updated positions
    mock_save.assert_awaited_once()
    saved_techs = mock_save.call_args[0][0]
    tech_positions = {t["id"]: t["queue_position"] for t in saved_techs}
    
    assert tech_positions[2] == 1  # Bob first
    assert tech_positions[3] == 2  # Charlie second
    assert tech_positions[1] == 3  # Alice third


@pytest.mark.asyncio
async def test_get_all_techs_sorted():
    """Should return all technicians sorted by queue position."""
    service = TurnRulesService()
    
    mock_techs = [
        make_tech(2, "Bob", queue_position=1),
        make_tech(1, "Alice", queue_position=2),
    ]
    
    with patch("app.database.load_technicians",
               new_callable=AsyncMock, return_value=mock_techs):
        
        result = await service.get_all_techs_sorted()
    
    assert len(result) == 2
    assert result[0]["id"] == 2  # Bob first (position 1)
    assert result[1]["id"] == 1  # Alice second (position 2)
