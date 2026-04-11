# Dependency Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all pinned dependencies in `requirements.txt` and `requirements-dev.txt` to their latest stable versions without breaking the app or tests.

**Architecture:** Two-phase approach — runtime dependencies first (Phase 1), dev tools second (Phase 2). Each phase ends with a passing test suite and a clean commit, so failures are immediately attributable to one group.

**Tech Stack:** PyQt6, SQLAlchemy, alembic, qt-material, requests, openpyxl, pytest, black, isort, mypy, flake8, Pillow

---

## Files Modified

- Modify: `requirements.txt` — bump 5 runtime package pins
- Modify: `requirements-dev.txt` — bump 8 dev package pins
- Modify: `src/**/*.py`, `tests/**/*.py` — reformatted by black/isort (no manual edits)

---

## Task 1: Update Core Runtime Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update `requirements.txt` pins**

Replace the file content with:

```
# Core dependencies (pinned for reproducibility)
PyQt6==6.11.0
SQLAlchemy==2.0.49
alembic==1.18.4
qt-material==2.17
openpyxl==3.1.5
requests==2.33.1
```

- [ ] **Step 2: Reinstall runtime dependencies**

```bash
.venv/Scripts/pip install -r requirements.txt
```

Expected: pip resolves and installs updated packages without errors. If you see a conflict error about `PyQt6-Qt6` or `PyQt6-sip`, run:
```bash
.venv/Scripts/pip install --upgrade PyQt6 PyQt6-Qt6 PyQt6-sip
```
then re-run `pip install -r requirements.txt`.

- [ ] **Step 3: Run the test suite**

```bash
.venv/Scripts/pytest tests/ -v
```

Expected: all tests pass (green). The test runner sets `QT_QPA_PLATFORM=offscreen` automatically via CI; run locally with:
```bash
QT_QPA_PLATFORM=offscreen .venv/Scripts/pytest tests/ -v
```
(Windows CMD: `set QT_QPA_PLATFORM=offscreen && .venv\Scripts\pytest tests\ -v`)

If tests fail, check the error message — most likely a deprecated PyQt6 API. Look at the failing test's import or signal connection and cross-reference the PyQt6 changelog for the affected version.

- [ ] **Step 4: Manual smoke test**

Launch the app:
```bash
.venv/Scripts/python src/main.py
```

Work through each flow:
1. **Add non-serialized item** — click Add, fill in type/name/quantity/location, save. Confirm it appears in the list.
2. **Add serialized item** — click Add, tick "Serialized", fill in type/serial number/location, save. Confirm pill badge shows "Serialized".
3. **Edit item** — right-click an item → Edit, change a field, enter a reason, save. Confirm the change reflects.
4. **Transfer** — right-click an item → Transfer, pick a different location, save. Confirm the item moves.
5. **Transactions** — right-click an item → Transactions. Confirm the dialog opens and shows history.
6. **Theme toggle** — open the Theme menu, switch between Light and Dark. Confirm the UI updates.
7. **Export** — use the export function. Confirm an `.xlsx` file is created and opens in Excel.

If the app crashes on launch or a dialog fails to open, note the traceback — it will point to a PyQt6 API change.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: bump core runtime dependencies

PyQt6 6.7.1 -> 6.11.0
SQLAlchemy 2.0.31 -> 2.0.49
alembic 1.13.2 -> 1.18.4
qt-material 2.14 -> 2.17
requests 2.32.3 -> 2.33.1"
```

---

## Task 2: Update Dev Tool Dependencies

**Files:**
- Modify: `requirements-dev.txt`

- [ ] **Step 1: Update `requirements-dev.txt` pins**

Replace the file content with:

```
# Development dependencies (pinned for reproducibility)
-r requirements.txt
pytest==9.0.3
pytest-cov==7.1.0
pytest-mock==3.15.1
black==26.3.1
mypy==1.20.0
isort==8.0.1
flake8==7.3.0
pyinstaller
icnsutil==1.1.0
Pillow==12.2.0
```

- [ ] **Step 2: Reinstall all dependencies**

```bash
.venv/Scripts/pip install -r requirements-dev.txt
```

Expected: all packages install cleanly.

- [ ] **Step 3: Run the test suite with pytest 9**

```bash
.venv/Scripts/pytest tests/ -v
```

Expected: all tests pass. pytest 9 removes features that were deprecated in pytest 8. Common failures and fixes:

- **`pytest.warns(None)` used as context manager** — replace with `warnings.catch_warnings()` or just remove the assert
- **`@pytest.mark.foo` not registered** — add `markers = ["foo: description"]` to `pytest.ini` or `pyproject.toml`
- **Fixture yield after `return`** — pytest 9 errors on this; remove the unreachable `return`
- **`--strict` flag** — renamed to `--strict-markers`; update any `addopts` config that uses it

Check `tests/conftest.py` first — that's where shared fixtures live.

Do not proceed to the next step until all tests pass.

- [ ] **Step 4: Run black to reformat source files**

```bash
.venv/Scripts/black src/ tests/
```

Expected output shows which files were reformatted, e.g.:
```
reformatted src/ui/main_window.py
reformatted src/core/services.py
...
All done! ✨ 🍰 ✨
N files reformatted, M files left unchanged.
```

This is expected and intentional — black 26 may have slightly different style rules from 24. Do not manually revert any of these changes.

- [ ] **Step 5: Run isort to re-sort imports**

```bash
.venv/Scripts/isort src/ tests/
```

Expected: isort silently re-sorts any import blocks that don't match its new ordering rules. No output means nothing changed; file names printed means those files were updated.

- [ ] **Step 6: Verify no new flake8 errors**

```bash
.venv/Scripts/flake8 src/
```

Expected: no output (no errors). If errors appear, they are most likely caused by black's reformatting producing lines that flake8 disagrees with (rare but possible — usually E501 line-too-long). Fix each one:

- **E501 line too long** — black should handle this; if it doesn't, the line likely contains a long string or comment. Manually wrap it.
- **F401 unused import** — isort may have reordered imports exposing one that was previously hidden; remove it.
- **W503/W504 line break** — add `extend-ignore = W503,W504` to your flake8 config if these appear (they're style-only warnings).

Re-run `flake8 src/` after each fix until it reports nothing.

- [ ] **Step 7: Run tests one final time**

```bash
.venv/Scripts/pytest tests/ -v
```

Expected: all tests still pass after black/isort reformatting (they only change whitespace/style, never logic).

- [ ] **Step 8: Commit everything in a single commit**

```bash
git add requirements-dev.txt src/ tests/
git commit -m "chore: bump dev dependencies and reformat with black/isort

pytest 8.1.1 -> 9.0.3
pytest-cov 4.1.0 -> 7.1.0
pytest-mock 3.12.0 -> 3.15.1
black 24.3.0 -> 26.3.1 (reformat applied)
mypy 1.9.0 -> 1.20.0
isort 5.13.2 -> 8.0.1 (re-sort applied)
flake8 7.0.0 -> 7.3.0
Pillow 12.1.1 -> 12.2.0"
```

---

## Success Criteria

- [ ] All 9 test files pass after Task 1 (`tests/conftest.py`, `test_auto_updater.py`, `test_dto_models.py`, `test_export_service.py`, `test_export_transactions.py`, `test_repositories.py`, `test_serialized_feature.py`, `test_services.py`, `test_translations.py`)
- [ ] Manual smoke test passes after Task 1 (7 flows listed in Task 1 Step 4)
- [ ] All 9 test files pass after Task 2
- [ ] `flake8 src/` reports no errors after Task 2
- [ ] Two clean commits on the branch
