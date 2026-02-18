"""
Automated tests for the is_serialized immutability feature.
Covers sections 9.1 (DB logic), 9.4 (translations), 9.5 (service conflict).
Sections 9.2/9.3 (UI badges) are verified via widget instantiation.

Run: python test_serialized_feature.py
"""
import os
import sys
import traceback

# Use in-memory DB to avoid touching production data
os.environ.setdefault("AUDITMAGIC_DB", ":memory:")

# ── Bootstrap ─────────────────────────────────────────────────────────────────

PASS = "OK"
FAIL = "FAIL"
results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    mark = PASS if passed else FAIL
    msg = f"  [{mark}] {name}"
    if detail:
        msg += " -- " + detail
    print(msg)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────
# Non-UI tests (no QApplication required)
# ─────────────────────────────────────────────────────────────────────────────

section("Phase 1: DB / Service Layer (no UI)")

try:
    from db import init_database
    init_database(":memory:")
    check("DB init (in-memory)", True)
except Exception as exc:
    check("DB init (in-memory)", False, str(exc))
    print("\n[FATAL] Cannot continue without DB. Exiting.")
    sys.exit(1)

try:
    from services import InventoryService
    check("Import InventoryService", True)
except Exception as exc:
    check("Import InventoryService", False, str(exc))
    sys.exit(1)

# ── 9.1 — Create serialized type, verify is_serialized = True in DB ──────────
section("9.1 -- Create & persist is_serialized flag")

ser_item = None
nonser_item = None

try:
    ser_item = InventoryService.create_item(
        item_type_name="Laptop",
        is_serialized=True,
        serial_number="SN-001",
        quantity=1,
    )
    check(
        "Create serialized type -- is_serialized=True on returned item",
        ser_item.is_serialized is True,
        f"got is_serialized={ser_item.is_serialized!r}",
    )
except Exception as exc:
    check("Create serialized type", False, str(exc))
    traceback.print_exc()

try:
    nonser_item = InventoryService.create_item(
        item_type_name="Desk",
        is_serialized=False,
        quantity=5,
    )
    check(
        "Create non-serialized type -- is_serialized=False on returned item",
        nonser_item.is_serialized is False,
        f"got is_serialized={nonser_item.is_serialized!r}",
    )
except Exception as exc:
    check("Create non-serialized type", False, str(exc))
    traceback.print_exc()

# ── 9.5 — Conflict via Service ─────────────────────────────────────────────
section("9.5 -- Conflict via Service (create_item is_serialized mismatch)")

try:
    # "Laptop" is already serialized — trying non-serialized should raise
    InventoryService.create_item(
        item_type_name="Laptop",
        is_serialized=False,
        quantity=3,
    )
    check(
        "create_item(Laptop, is_serialized=False) raises ValueError",
        False,
        "Expected ValueError -- none raised",
    )
except ValueError as exc:
    check(
        "create_item(Laptop, is_serialized=False) raises ValueError",
        True,
        str(exc)[:80],
    )
except Exception as exc:
    check(
        "create_item(Laptop, is_serialized=False) raises ValueError",
        False,
        f"Wrong exception type {type(exc).__name__}: {exc}",
    )

try:
    # "Desk" is already non-serialized — trying serialized should raise
    InventoryService.create_item(
        item_type_name="Desk",
        is_serialized=True,
        serial_number="SN-DESK-01",
        quantity=1,
    )
    check(
        "create_item(Desk, is_serialized=True) raises ValueError",
        False,
        "Expected ValueError -- none raised",
    )
except ValueError as exc:
    check(
        "create_item(Desk, is_serialized=True) raises ValueError",
        True,
        str(exc)[:80],
    )
except Exception as exc:
    check(
        "create_item(Desk, is_serialized=True) raises ValueError",
        False,
        f"Wrong exception type {type(exc).__name__}: {exc}",
    )

# Same type + same flag -> no error (idempotent add)
try:
    InventoryService.create_item(
        item_type_name="Laptop",
        is_serialized=True,
        serial_number="SN-002",
        quantity=1,
    )
    check("create_item same type+flag (idempotent) -- no error", True)
except Exception as exc:
    check("create_item same type+flag (idempotent) -- no error", False, str(exc))

# ── get_item_type_by_name_subtype ─────────────────────────────────────────────
section("9.1 extra -- get_item_type_by_name_subtype lookup")

try:
    found = InventoryService.get_item_type_by_name_subtype("Laptop", "")
    check(
        "get_item_type_by_name_subtype('Laptop') returns result",
        found is not None,
        f"got {found}",
    )
    if found is not None:
        check(
            "Returned type has is_serialized=True",
            found.is_serialized is True,
            f"is_serialized={found.is_serialized!r}",
        )
except Exception as exc:
    check("get_item_type_by_name_subtype", False, str(exc))

try:
    not_found = InventoryService.get_item_type_by_name_subtype("NonExistentXYZ", "")
    check(
        "get_item_type_by_name_subtype('NonExistentXYZ') returns None",
        not_found is None,
        f"got {not_found}",
    )
except Exception as exc:
    check("get_item_type_by_name_subtype(missing)", False, str(exc))

# ── 9.4 — Translation keys ────────────────────────────────────────────────────
section("9.4 -- Translation keys present")

required_keys = [
    "label.serialized_badge",
    "label.non_serialized_badge",
    "label.is_serialized",
    "tooltip.serialized_locked",
    "tooltip.serialized_auto",
    "error.serialized_conflict",
    "message.type_exists_serialized",
    "message.type_exists_non_serialized",
]

try:
    from ui_entities.translations import tr

    for key in required_keys:
        # tr() falls back to the raw key when missing — so a non-raw result means it's present
        val = tr(key)
        present = val != key
        check(
            f"tr key '{key}' present",
            present,
            f"value={val!r}",
        )

    serialized_badge = tr("label.serialized_badge")
    check(
        "tr('label.serialized_badge') is not raw key",
        serialized_badge != "label.serialized_badge",
        f"got {serialized_badge!r}",
    )
    non_ser_badge = tr("label.non_serialized_badge")
    check(
        "tr('label.non_serialized_badge') is not raw key",
        non_ser_badge != "label.non_serialized_badge",
        f"got {non_ser_badge!r}",
    )

except Exception as exc:
    check("Import/use translations", False, str(exc))
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────────────────────
# UI tests — requires QApplication
# ─────────────────────────────────────────────────────────────────────────────
section("Phase 2: UI Widgets (requires QApplication)")

app = None
try:
    from PyQt6.QtWidgets import QApplication, QLabel
    app = QApplication.instance() or QApplication(sys.argv)
    check("QApplication created", True)
except Exception as exc:
    check("QApplication created", False, str(exc))

if app is not None:
    # ── 9.2 — EditItemDialog badge ─────────────────────────────────────────────
    section("9.2 -- EditItemDialog badge and _type_conflict flag")

    if ser_item is not None:
        try:
            from ui_entities.edit_item_dialog import EditItemDialog

            dlg_ser = EditItemDialog(ser_item)

            check(
                "EditItemDialog._type_conflict starts False",
                dlg_ser._type_conflict is False,
            )

            badge_text = tr("label.serialized_badge")
            labels = dlg_ser.findChildren(QLabel)
            badge_texts = [lbl.text() for lbl in labels]
            has_badge = badge_text in badge_texts
            check(
                f"EditItemDialog shows serialized badge for serialized item",
                has_badge,
                f"looking for {badge_text!r} in {[t for t in badge_texts if t]}",
            )
            dlg_ser.deleteLater()
        except Exception as exc:
            check("EditItemDialog (serialized)", False, str(exc))
            traceback.print_exc()
    else:
        check("EditItemDialog (serialized)", False, "ser_item not available")

    if nonser_item is not None:
        try:
            from ui_entities.edit_item_dialog import EditItemDialog

            dlg_nonser = EditItemDialog(nonser_item)
            non_badge_text = tr("label.non_serialized_badge")
            labels = dlg_nonser.findChildren(QLabel)
            badge_texts = [lbl.text() for lbl in labels]
            has_badge = non_badge_text in badge_texts
            check(
                f"EditItemDialog shows non-serialized badge for non-serialized item",
                has_badge,
                f"looking for {non_badge_text!r} in {[t for t in badge_texts if t]}",
            )
            dlg_nonser.deleteLater()
        except Exception as exc:
            check("EditItemDialog (non-serialized)", False, str(exc))
            traceback.print_exc()
    else:
        check("EditItemDialog (non-serialized)", False, "nonser_item not available")

    # ── 9.3 — ItemDetailsDialog badge ─────────────────────────────────────────
    section("9.3 -- ItemDetailsDialog badge row")

    if ser_item is not None:
        try:
            from ui_entities.item_details_dialog import ItemDetailsDialog

            details_ser = ItemDetailsDialog(ser_item)
            badge_text = tr("label.serialized_badge")
            labels = details_ser.findChildren(QLabel)
            badge_texts = [lbl.text() for lbl in labels]
            has_badge = badge_text in badge_texts
            check(
                f"ItemDetailsDialog shows serialized badge for serialized item",
                has_badge,
                f"looking for {badge_text!r} in {[t for t in badge_texts if t]}",
            )
            details_ser.deleteLater()
        except Exception as exc:
            check("ItemDetailsDialog (serialized)", False, str(exc))
            traceback.print_exc()
    else:
        check("ItemDetailsDialog (serialized)", False, "ser_item not available")

    if nonser_item is not None:
        try:
            from ui_entities.item_details_dialog import ItemDetailsDialog

            details_nonser = ItemDetailsDialog(nonser_item)
            non_badge_text = tr("label.non_serialized_badge")
            labels = details_nonser.findChildren(QLabel)
            badge_texts = [lbl.text() for lbl in labels]
            has_badge = non_badge_text in badge_texts
            check(
                f"ItemDetailsDialog shows non-serialized badge for non-serialized item",
                has_badge,
                f"looking for {non_badge_text!r} in {[t for t in badge_texts if t]}",
            )
            details_nonser.deleteLater()
        except Exception as exc:
            check("ItemDetailsDialog (non-serialized)", False, str(exc))
            traceback.print_exc()
    else:
        check("ItemDetailsDialog (non-serialized)", False, "nonser_item not available")

    # ── 9.1 — AddItemDialog checkbox lock ─────────────────────────────────────
    section("9.1 -- AddItemDialog: checkbox state when existing type is typed")

    try:
        from ui_entities.add_item_dialog import AddItemDialog

        add_dlg = AddItemDialog()

        check("AddItemDialog has type_status_label", hasattr(add_dlg, "type_status_label"))
        check("AddItemDialog has serialized_checkbox", hasattr(add_dlg, "serialized_checkbox"))

        # Simulate typing "Laptop" (exists as serialized=True)
        add_dlg.type_edit.setText("Laptop")
        add_dlg._on_type_or_subtype_changed()

        chk_enabled = add_dlg.serialized_checkbox.isEnabled()
        chk_checked = add_dlg.serialized_checkbox.isChecked()
        status_text = add_dlg.type_status_label.text()

        check(
            "Typing existing serialized type -- checkbox disabled",
            not chk_enabled,
            f"isEnabled={chk_enabled}",
        )
        check(
            "Typing existing serialized type -- checkbox checked",
            chk_checked,
            f"isChecked={chk_checked}",
        )
        check(
            "Typing existing serialized type -- status label non-empty",
            bool(status_text),
            f"text={status_text!r}",
        )

        # Clear the type -- checkbox should re-enable
        add_dlg.type_edit.setText("")
        add_dlg._on_type_or_subtype_changed()
        check(
            "Clearing type -- checkbox re-enabled",
            add_dlg.serialized_checkbox.isEnabled(),
            f"isEnabled={add_dlg.serialized_checkbox.isEnabled()}",
        )

        # Simulate typing "Desk" (exists as non-serialized=False)
        add_dlg.type_edit.setText("Desk")
        add_dlg._on_type_or_subtype_changed()
        check(
            "Typing existing non-serialized type -- checkbox disabled",
            not add_dlg.serialized_checkbox.isEnabled(),
        )
        check(
            "Typing existing non-serialized type -- checkbox unchecked",
            not add_dlg.serialized_checkbox.isChecked(),
        )

        add_dlg.deleteLater()
    except Exception as exc:
        check("AddItemDialog checkbox lock", False, str(exc))
        traceback.print_exc()

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
section("SUMMARY")

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)

print(f"\n  Passed: {passed}/{total}")
if failed:
    print(f"  Failed: {failed}/{total}")
    print("\n  Failed checks:")
    for name, ok, detail in results:
        if not ok:
            line = f"    [FAIL] {name}"
            if detail:
                line += " -- " + detail
            print(line)

print()
sys.exit(0 if failed == 0 else 1)
