import pytest
from app.models.schemas import ValidationStatus
from app.engine.reconciliation import is_close_enough

def test_tolerance_checks():
    # Price difference within 0.01%
    assert is_close_enough(50000.0, 50004.0, tol_pct=0.0001) is True
    # Price difference exceeding 0.01%
    assert is_close_enough(50000.0, 50010.0, tol_pct=0.0001) is False

    # Zero value handling
    assert is_close_enough(0.0, 0.0, tol_pct=0.001) is True
    assert is_close_enough(0.0, 1.0, tol_pct=0.001) is False
