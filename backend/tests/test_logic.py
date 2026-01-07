"""
Unit tests for TurnRulesService business logic.
"""

import pytest
from app.services.turn_rules import (
    TurnRulesService,
    TechnicianEntity,
    TechnicianNotFoundError,
    TechnicianNotAvailableError,
    NoAvailableTechniciansError,
)


def test_get_next_tech_returns_lowest_position():
    """Next available tech should be the one with lowest queue_position."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=2, is_active=True)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=1, is_active=True)
    tech3 = TechnicianEntity(id=3, name="Charlie", status="BUSY", queue_position=3, is_active=True)

    service = TurnRulesService([tech1, tech2, tech3])
    next_tech = service.get_next_tech()

    assert next_tech == tech2
    assert next_tech.id == 2


def test_get_next_tech_skips_busy():
    """Busy technicians should be skipped when finding next available."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="BUSY", queue_position=1, is_active=True)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=2, is_active=True)

    service = TurnRulesService([tech1, tech2])
    next_tech = service.get_next_tech()

    assert next_tech == tech2
    assert tech1.queue_position == 1  # Busy tech keeps position


def test_get_next_tech_skips_inactive():
    """Inactive (checked-out) technicians should be skipped."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=False)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=2, is_active=True)

    service = TurnRulesService([tech1, tech2])
    next_tech = service.get_next_tech()

    assert next_tech == tech2


def test_get_next_tech_none_available():
    """Should return None when no technicians are available."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="BUSY", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])
    assert service.get_next_tech() is None


def test_complete_turn_moves_to_bottom():
    """Completing a turn should move technician to bottom of queue."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="BUSY", queue_position=1, is_active=True)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=2, is_active=True)

    service = TurnRulesService([tech1, tech2])

    # Complete Alice's turn - should move to position 2 (repacked: Bob=1, Alice=2)
    service.handle_tech_completion(tech_id=1, is_request=False)

    assert tech1.queue_position == 2  # Repacked: contiguous positions
    assert tech1.status == "AVAILABLE"


def test_assign_tech_marks_as_busy():
    """Assigning a tech should mark them as BUSY."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])

    assigned = service.assign_tech(1)

    assert assigned.status == "BUSY"


def test_assign_tech_not_found_raises():
    """Assigning a non-existent tech should raise TechnicianNotFoundError."""
    service = TurnRulesService([])

    with pytest.raises(TechnicianNotFoundError):
        service.assign_tech(999)


def test_assign_tech_not_available_raises():
    """Assigning a busy tech should raise TechnicianNotAvailableError."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="BUSY", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])

    with pytest.raises(TechnicianNotAvailableError):
        service.assign_tech(1)


def test_assign_next_available_raises_when_empty():
    """Should raise NoAvailableTechniciansError when queue is empty."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="BUSY", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])

    with pytest.raises(NoAvailableTechniciansError):
        service.assign_next_available()


def test_add_technician():
    """Adding a technician should create a new entry at the bottom of queue."""
    service = TurnRulesService([])

    new_tech = service.add_technician("Alice")

    assert new_tech.name == "Alice"
    assert new_tech.id == 1
    assert new_tech.queue_position == 1
    assert new_tech.status == "AVAILABLE"
    assert new_tech.is_active is False


def test_remove_technician():
    """Removing a technician should remove them from the list."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])

    service.remove_technician(1)

    assert len(service.technicians) == 0


def test_remove_technician_not_found_raises():
    """Removing a non-existent technician should raise TechnicianNotFoundError."""
    service = TurnRulesService([])

    with pytest.raises(TechnicianNotFoundError):
        service.remove_technician(999)


def test_toggle_active_status():
    """Toggle should switch is_active state."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=False)
    service = TurnRulesService([tech1])

    service.toggle_active_status(1)
    assert tech1.is_active is True

    service.toggle_active_status(1)
    assert tech1.is_active is False


def test_take_break():
    """Taking a break should set status to ON_BREAK."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=True)
    service = TurnRulesService([tech1])

    service.take_break(1)

    assert tech1.status == "ON_BREAK"


def test_return_from_break():
    """Returning from break should set status to AVAILABLE and move to bottom."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="ON_BREAK", queue_position=1, is_active=True)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=2, is_active=True)
    service = TurnRulesService([tech1, tech2])

    service.return_from_break(1)

    assert tech1.status == "AVAILABLE"
    assert tech1.queue_position == 2  # Repacked: Bob=1, Alice=2


def test_reorder_queue():
    """Reordering should update queue positions based on new order."""
    tech1 = TechnicianEntity(id=1, name="Alice", status="AVAILABLE", queue_position=1, is_active=True)
    tech2 = TechnicianEntity(id=2, name="Bob", status="AVAILABLE", queue_position=2, is_active=True)
    tech3 = TechnicianEntity(id=3, name="Charlie", status="AVAILABLE", queue_position=3, is_active=True)
    service = TurnRulesService([tech1, tech2, tech3])

    # Reorder: Bob first, then Charlie, then Alice
    service.reorder_queue([2, 3, 1])

    assert tech1.queue_position == 3
    assert tech2.queue_position == 1
    assert tech3.queue_position == 2
