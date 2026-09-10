"""Pure unit tests for ui/form_rules.py.

Qt-free by construction: no PyQt6 import anywhere in this file or in
ui.form_rules itself.
"""

from ui.form_rules import (
    FieldError,
    add_item_rules,
    edit_item_rules,
    has_serialization_conflict,
    quantity_rules,
)
from ui.translations import tr

# ─── add_item_rules ─────────────────────────────────────────────────────────


def test_add_item_rules_valid_non_serialized():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert errors == []


def test_add_item_rules_valid_serialized():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="1",
        serial_number="SN-001",
        initial_notes="",
        is_serialized=True,
    )
    assert errors == []


def test_add_item_rules_missing_type():
    errors = add_item_rules(
        item_type="",
        quantity_text="5",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert [e.field for e in errors] == ["type"]


def test_add_item_rules_type_too_short():
    errors = add_item_rules(
        item_type="A",
        quantity_text="5",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert [e.field for e in errors] == ["type"]


def test_add_item_rules_quantity_empty():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert errors == [FieldError("quantity", tr("message.quantity_required"))]


def test_add_item_rules_quantity_not_a_number():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="abc",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert errors == [FieldError("quantity", tr("message.quantity_invalid"))]


def test_add_item_rules_quantity_zero():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="0",
        serial_number="",
        initial_notes="",
        is_serialized=False,
    )
    assert [e.field for e in errors] == ["quantity"]


def test_add_item_rules_serialized_missing_serial():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="1",
        serial_number="",
        initial_notes="",
        is_serialized=True,
    )
    assert errors == [FieldError("serial", tr("error.serial.required"))]


def test_add_item_rules_non_serialized_with_serial_rejected():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="SN-001",
        initial_notes="",
        is_serialized=False,
    )
    assert errors == [FieldError("serial", tr("error.serial.not_allowed"))]


def test_add_item_rules_notes_too_long():
    errors = add_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        initial_notes="x" * 1001,
        is_serialized=False,
    )
    assert [e.field for e in errors] == ["notes"]


def test_add_item_rules_order_is_type_quantity_serial_notes():
    errors = add_item_rules(
        item_type="",
        quantity_text="",
        serial_number="SN-001",
        initial_notes="x" * 1001,
        is_serialized=False,
    )
    assert [e.field for e in errors] == ["type", "quantity", "serial", "notes"]


# ─── edit_item_rules ─────────────────────────────────────────────────────────


def test_edit_item_rules_valid_non_serialized():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        item_details="",
        edit_reason="Correcting count",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert errors == []


def test_edit_item_rules_valid_serialized():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="",
        serial_number="",
        item_details="",
        edit_reason="Renamed type",
        is_serialized=True,
        remaining_serial_count=3,
    )
    assert errors == []


def test_edit_item_rules_missing_type():
    errors = edit_item_rules(
        item_type="",
        quantity_text="5",
        serial_number="",
        item_details="",
        edit_reason="Reason here",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert "type" in [e.field for e in errors]


def test_edit_item_rules_quantity_empty_non_serialized():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="",
        serial_number="",
        item_details="",
        edit_reason="Reason here",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert FieldError("quantity", tr("message.quantity_required")) in errors


def test_edit_item_rules_quantity_invalid_non_serialized():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="abc",
        serial_number="",
        item_details="",
        edit_reason="Reason here",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert FieldError("quantity", tr("message.quantity_invalid")) in errors


def test_edit_item_rules_quantity_ignored_when_serialized():
    # Bad quantity_text must not surface an error for a serialized item —
    # quantity is a read-only serial count in that case.
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="not-a-number",
        serial_number="",
        item_details="",
        edit_reason="Reason here",
        is_serialized=True,
        remaining_serial_count=2,
    )
    assert "quantity" not in [e.field for e in errors]


def test_edit_item_rules_serial_too_long():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="x" * 256,
        item_details="",
        edit_reason="Reason here",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert "serial" in [e.field for e in errors]


def test_edit_item_rules_details_too_long():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        item_details="x" * 1001,
        edit_reason="Reason here",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert "details" in [e.field for e in errors]


def test_edit_item_rules_edit_reason_required():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        item_details="",
        edit_reason="",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert "edit_reason" in [e.field for e in errors]


def test_edit_item_rules_edit_reason_too_short():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="5",
        serial_number="",
        item_details="",
        edit_reason="ab",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert "edit_reason" in [e.field for e in errors]


def test_edit_item_rules_serialized_must_keep_at_least_one_serial():
    errors = edit_item_rules(
        item_type="Laptop",
        quantity_text="",
        serial_number="",
        item_details="",
        edit_reason="Reason here",
        is_serialized=True,
        remaining_serial_count=0,
    )
    assert errors == [FieldError("serial", tr("message.at_least_one_serial"))]


def test_edit_item_rules_order():
    errors = edit_item_rules(
        item_type="",
        quantity_text="",
        serial_number="x" * 256,
        item_details="x" * 1001,
        edit_reason="",
        is_serialized=False,
        remaining_serial_count=0,
    )
    assert [e.field for e in errors] == [
        "type",
        "quantity",
        "serial",
        "details",
        "edit_reason",
    ]


# ─── quantity_rules ────────────────────────────────────────────────────────────


def test_quantity_rules_valid_add():
    errors = quantity_rules(
        quantity_text="5", notes="", is_add=True, current_quantity=10
    )
    assert errors == []


def test_quantity_rules_valid_remove_within_current():
    errors = quantity_rules(
        quantity_text="5", notes="", is_add=False, current_quantity=10
    )
    assert errors == []


def test_quantity_rules_empty():
    errors = quantity_rules(
        quantity_text="", notes="", is_add=True, current_quantity=10
    )
    assert errors == [FieldError("quantity", tr("message.quantity_required"))]


def test_quantity_rules_not_a_number():
    errors = quantity_rules(
        quantity_text="abc", notes="", is_add=True, current_quantity=10
    )
    assert errors == [FieldError("quantity", tr("message.quantity_invalid"))]


def test_quantity_rules_zero_or_negative():
    errors = quantity_rules(
        quantity_text="0", notes="", is_add=True, current_quantity=10
    )
    assert errors == [FieldError("quantity", tr("message.quantity_positive"))]


def test_quantity_rules_remove_more_than_available():
    errors = quantity_rules(
        quantity_text="15", notes="", is_add=False, current_quantity=10
    )
    expected_message = (
        f"{tr('message.not_enough_quantity')}\n"
        f"{tr('message.not_enough_quantity_detail', requested=15, available=10)}"
    )
    assert errors == [FieldError("quantity", expected_message)]


def test_quantity_rules_add_more_than_current_is_fine():
    # "not enough" only applies to remove, not add
    errors = quantity_rules(
        quantity_text="9999", notes="", is_add=True, current_quantity=10
    )
    assert errors == []


def test_quantity_rules_notes_too_long():
    errors = quantity_rules(
        quantity_text="5", notes="x" * 1001, is_add=True, current_quantity=10
    )
    assert [e.field for e in errors] == ["notes"]


def test_quantity_rules_order_is_quantity_then_notes():
    errors = quantity_rules(
        quantity_text="", notes="x" * 1001, is_add=True, current_quantity=10
    )
    assert [e.field for e in errors] == ["quantity", "notes"]


# ─── has_serialization_conflict ─────────────────────────────────────────────────


def test_no_conflict_when_no_existing_type():
    assert (
        has_serialization_conflict(
            existing_is_serialized=None, current_is_serialized=True
        )
        is False
    )


def test_no_conflict_when_states_match():
    assert (
        has_serialization_conflict(
            existing_is_serialized=True, current_is_serialized=True
        )
        is False
    )
    assert (
        has_serialization_conflict(
            existing_is_serialized=False, current_is_serialized=False
        )
        is False
    )


def test_conflict_when_states_differ():
    assert (
        has_serialization_conflict(
            existing_is_serialized=True, current_is_serialized=False
        )
        is True
    )
    assert (
        has_serialization_conflict(
            existing_is_serialized=False, current_is_serialized=True
        )
        is True
    )
