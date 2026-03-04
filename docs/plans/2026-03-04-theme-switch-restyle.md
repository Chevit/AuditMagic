# Theme Switch — Re-apply Widget Styles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the location dropdown (and other main-window widgets) not re-styling when the user switches themes, and remove the disruptive "Theme changed" popup.

**Architecture:** Custom stylesheets are strings baked in at widget construction time. When qt-material's global theme changes, widgets with explicit stylesheets retain the old colors. The fix adds a `reapply_styles()` method to `LocationSelectorWidget` and consolidates all main-window re-apply calls into a renamed `_reapply_all_styles()` method in `MainWindow`.

**Tech Stack:** Python 3.11+, PyQt6, `apply_combo_box_style` / `apply_button_style` / `apply_input_style` helpers from `src/ui/styles.py`.

---

### Task 1: Add `reapply_styles()` to `LocationSelectorWidget`

**Files:**
- Modify: `src/ui/widgets/location_selector.py` (append after `_on_index_changed`, around line 88)

No unit tests needed — pure UI styling, no logic to assert.

**Step 1: Read the file to confirm current state**

Read `src/ui/widgets/location_selector.py` lines 86–89 to see the end of `_on_index_changed`.

**Step 2: Add `reapply_styles` method**

At the end of the class (after `_on_index_changed`), add:

```python
    def reapply_styles(self):
        """Re-apply theme-aware styles after a theme switch."""
        apply_combo_box_style(self.combo)
        apply_button_style(self.manage_btn, "secondary")
```

Both `apply_combo_box_style` and `apply_button_style` are already imported on line 7 of that file — no new imports needed.

**Step 3: Run the test suite to confirm nothing broke**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -5
```

Expected: all tests pass.

**Step 4: Commit**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && git add src/ui/widgets/location_selector.py && git commit -m "feat: add reapply_styles to LocationSelectorWidget"
```

---

### Task 2: Update `MainWindow` — consolidate re-apply and fix theme switch

**Files:**
- Modify: `src/ui/main_window.py` (~lines 235–266, 386–418)

**Step 1: Read the two relevant sections**

Read `src/ui/main_window.py` lines 235–266 (`_on_theme_changed`) and lines 386–395 (`_reapply_search_widget_styles`).

**Step 2: Rename `_reapply_search_widget_styles` → `_reapply_all_styles` and expand it**

Replace the entire `_reapply_search_widget_styles` method (lines 386–394) with:

```python
    def _reapply_all_styles(self):
        """Re-apply theme-aware styles to all main-window widgets after a theme switch."""
        from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style

        # Search widget
        apply_combo_box_style(self.search_widget.field_combo)
        apply_input_style(self.search_widget.search_input)
        apply_button_style(self.search_widget.search_button, "info")
        apply_button_style(self.search_widget.clear_button, "secondary")

        # Location selector
        self.location_selector.reapply_styles()

        # Main action buttons
        if hasattr(self, "addButton"):
            apply_button_style(self.addButton, "primary")
        if hasattr(self, "all_transactions_btn"):
            apply_button_style(self.all_transactions_btn, "info")
```

**Step 3: Update the call site in `_setup_inventory_list`**

In `_setup_inventory_list` (around line 418), change:
```python
                        self._reapply_search_widget_styles()
```
to:
```python
                        self._reapply_all_styles()
```

**Step 4: Update `_on_theme_changed` — new call site + remove QMessageBox**

Replace the entire body of the `if theme_manager:` → `try:` block in `_on_theme_changed` (lines 242–259):

Current:
```python
                theme = Theme.get_by_name(theme_name)
                theme_manager.apply_theme(theme)

                # Save to config
                config.set("theme", theme_name)

                # Refresh search widget styles to match new theme
                if hasattr(self, "search_widget"):
                    self._reapply_search_widget_styles()

                logger.info(f"Theme changed to: {theme_name}")

                # Show message
                QMessageBox.information(
                    self,
                    tr("message.theme.changed"),
                    tr("message.theme.changed.text"),
                )
```

Replace with:
```python
                theme = Theme.get_by_name(theme_name)
                theme_manager.apply_theme(theme)

                # Save to config
                config.set("theme", theme_name)

                # Re-apply custom styles (they are baked as strings and don't auto-update)
                if hasattr(self, "search_widget"):
                    self._reapply_all_styles()

                logger.info(f"Theme changed to: {theme_name}")
```

Key changes:
- `_reapply_search_widget_styles()` → `_reapply_all_styles()` (covers location selector + buttons too)
- Removed the `QMessageBox.information(...)` block entirely — theme switch is now silent

**Step 5: Run the test suite**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -5
```

Expected: all tests pass.

**Step 6: Commit**

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && git add src/ui/main_window.py && git commit -m "fix: re-apply all widget styles on theme switch, remove theme-changed popup"
```

---

### Task 3: Manual smoke test

Launch the app:

```bash
cd /c/Users/chevi/PycharmProjects/AuditMagic && .venv/Scripts/python.exe src/main.py
```

Verify:

1. **Location dropdown** — Switch theme via 🎨 Theme menu. The location dropdown (combo) immediately shows the new theme's background/border/text colors.
2. **Manage button** — Same switch: the Manage button updates its outline and text color.
3. **Add Item button** — Stays green (primary color is constant across themes) but ensure it doesn't go stale/white on switch.
4. **All Transactions button** — Same as above for the info (blue) button.
5. **Search widgets** — Continue to update as before.
6. **No popup** — Switching theme shows no "Theme changed" message box.
7. **Switch back** — Toggle back to original theme; all widgets revert correctly.
