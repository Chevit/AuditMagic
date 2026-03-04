# Design: Theme Switch — Re-apply Widget Styles

**Date:** 2026-03-04

## Problem

When the user switches themes via the 🎨 Theme menu, `MainWindow._on_theme_changed` calls `apply_stylesheet()` (qt-material) to repaint the app globally, then calls `_reapply_search_widget_styles()` to fix the search widgets.

However, the following main-window widgets retain the stylesheet string that was baked in at construction time, so they keep the old theme's colors:

- `LocationSelectorWidget.combo` (location dropdown)
- `LocationSelectorWidget.manage_btn` (Manage button)
- `self.addButton` (Add Item button)
- `self.all_transactions_btn` (All Transactions button)

Additionally, a `QMessageBox.information("Theme changed…")` popup interrupts the user after every theme switch, which is disruptive — theme changes should be instant and silent.

## Decision

1. Add `LocationSelectorWidget.reapply_styles()` — re-calls `apply_combo_box_style` / `apply_button_style` on its own widgets using the now-current theme colors.
2. Rename `MainWindow._reapply_search_widget_styles` → `_reapply_all_styles` and expand it to also cover the location selector and the two action buttons.
3. Remove the `QMessageBox.information("Theme changed…")` call from `_on_theme_changed`.

## Changes

### `src/ui/widgets/location_selector.py`

Add one new public method after `_on_index_changed`:

```python
def reapply_styles(self):
    """Re-apply theme-aware styles after a theme switch."""
    apply_combo_box_style(self.combo)
    apply_button_style(self.manage_btn, "secondary")
```

### `src/ui/main_window.py`

**Rename** `_reapply_search_widget_styles` → `_reapply_all_styles` (two call sites:
`_setup_inventory_list` and `_on_theme_changed`).

**Expand** `_reapply_all_styles` to also call:
```python
self.location_selector.reapply_styles()
if hasattr(self, "addButton"):
    apply_button_style(self.addButton, "primary")
if hasattr(self, "all_transactions_btn"):
    apply_button_style(self.all_transactions_btn, "info")
```

**Remove** from `_on_theme_changed`:
```python
QMessageBox.information(
    self,
    tr("message.theme.changed"),
    tr("message.theme.changed.text"),
)
```

## What does NOT change

- `theme_config.py`, `theme_manager.py`, `styles.py` — untouched
- Dialog widgets — they construct fresh on each open, inheriting current-theme colors automatically
- Business logic, tests — no changes needed

## Scope

Two files, ~15 lines net change. No new tests required.
