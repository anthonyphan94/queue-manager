import pytest
from backend.turn_manager import TurnEngine, Technician, TechnicianStatus

def test_rule_1_next_turn_available_lowest_position():
    tech1 = Technician(id=1, name="Alice", status=TechnicianStatus.AVAILABLE, queue_position=2)
    tech2 = Technician(id=2, name="Bob", status=TechnicianStatus.AVAILABLE, queue_position=1)
    tech3 = Technician(id=3, name="Charlie", status=TechnicianStatus.BUSY, queue_position=3)

    engine = TurnEngine([tech1, tech2, tech3])
    next_tech = engine.get_next_tech()

    assert next_tech == tech2
    assert next_tech.id == 2

def test_rule_2_skip_unavailable_keeps_position():
    # Setup: Tech 1 is unavailable (skipped), Tech 2 is available
    tech1 = Technician(id=1, name="Alice", status=TechnicianStatus.BUSY, queue_position=1)
    tech2 = Technician(id=2, name="Bob", status=TechnicianStatus.AVAILABLE, queue_position=2)

    engine = TurnEngine([tech1, tech2])
    
    # Next tech should be Bob, because Alice is busy
    next_tech = engine.get_next_tech()
    assert next_tech == tech2

    # Verification: Alice should still have queue_position 1 (conceptually, or we check state if we modified it, but rules say they keep position)
    assert tech1.queue_position == 1

def test_rule_3_complete_turn_moves_to_bottom():
    tech1 = Technician(id=1, name="Alice", status=TechnicianStatus.BUSY, queue_position=1)
    tech2 = Technician(id=2, name="Bob", status=TechnicianStatus.AVAILABLE, queue_position=2)
    
    engine = TurnEngine([tech1, tech2])

    # Case A: is_request = False (Standard rotation)
    # Alice completes a turn. Max position is currently 2. She should move to 3.
    engine.complete_turn(tech_id=1, is_request=False)
    
    assert tech1.queue_position == 3
    # Check that others might shift or just relative order matters?
    # Request says: "Tech moves to bottom of queue (max position + 1)"
    
    # Case B: is_request = True
    # Bob completes a turn. Max position is now 3 (Alice). Bob should move to 4.
    engine.complete_turn(tech_id=2, is_request=True)
    assert tech2.queue_position == 4

def test_get_next_tech_none_available():
    tech1 = Technician(id=1, name="Alice", status=TechnicianStatus.BUSY, queue_position=1)
    engine = TurnEngine([tech1])
    assert engine.get_next_tech() is None
