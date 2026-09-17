"""Pin verification logic (no network)."""
import pytest

from src.extract import ReleaseMismatch, verify_pin


def test_verify_pin_states():
    pins = {"QCL": {"sha256": "a" * 64, "catalogue_date_update": "2025-12-31"}}
    assert verify_pin("QCL", "a" * 64, pins, accept_new_releases=False) == "pinned"
    assert verify_pin("NEW", "b" * 64, pins, accept_new_releases=False) == "new"
    with pytest.raises(ReleaseMismatch):
        verify_pin("QCL", "b" * 64, pins, accept_new_releases=False)
    assert verify_pin("QCL", "b" * 64, pins, accept_new_releases=True) == "updated"
