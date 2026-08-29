"""Tests for QuantityDialog's location handling — skipped where Qt cannot start."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Qt needs system graphics libraries; skip rather than fail where they're absent.
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from core import stock  # noqa: E402
from core.repositories import ItemTypeRepository, LocationRepository  # noqa: E402
from core.stock import Quantity, StockRef  # noqa: E402
from ui.dialogs.quantity_dialog import QuantityDialog  # noqa: E402


@pytest.fixture(scope="session")
def qt_app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def two_locations():
    """Stock of one type split across two locations: 12 at A, 3 at B."""
    loc_a = LocationRepository.create("Warehouse A")
    loc_b = LocationRepository.create("Warehouse B")
    item_type = ItemTypeRepository.get_or_create(name="Desk", is_serialized=False)
    stock.add(StockRef(item_type.id, loc_a.id), Quantity(12))
    stock.add(StockRef(item_type.id, loc_b.id), Quantity(3))
    return item_type, loc_a, loc_b


def test_available_follows_the_selected_location(qt_app, two_locations):
    _type, loc_a, loc_b = two_locations
    dialog = QuantityDialog(
        "Desk",
        15,
        is_add=False,
        locations=[(loc_a.id, "Warehouse A", 12), (loc_b.id, "Warehouse B", 3)],
        current_location_id=loc_b.id,
    )
    assert dialog.location_combo.currentData() == loc_b.id
    assert dialog._available() == 3

    dialog.location_combo.setCurrentIndex(dialog.location_combo.findData(loc_a.id))
    assert dialog._available() == 12
    assert "12" in dialog.current_label.text()


def test_preview_uses_the_selected_location(qt_app, two_locations):
    _type, loc_a, loc_b = two_locations
    dialog = QuantityDialog(
        "Desk",
        15,
        is_add=False,
        locations=[(loc_a.id, "Warehouse A", 12), (loc_b.id, "Warehouse B", 3)],
        current_location_id=loc_a.id,
    )
    dialog.quantity_input.setText("5")
    assert dialog.preview_label.text() == "12 - 5 = 7"


def test_combo_is_disabled_for_a_single_location(qt_app, two_locations):
    _type, _loc_a, loc_b = two_locations
    dialog = QuantityDialog(
        "Desk", 3, is_add=False, locations=[(loc_b.id, "Warehouse B", 3)]
    )
    assert dialog.location_combo.isEnabled() is False


def test_no_locations_falls_back_to_current_quantity(qt_app):
    dialog = QuantityDialog("Desk", 7, is_add=True)
    assert dialog.location_combo is None
    assert dialog._available() == 7
    assert dialog.get_location_id() is None
