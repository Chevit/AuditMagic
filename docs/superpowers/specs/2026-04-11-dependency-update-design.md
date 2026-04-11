# Dependency Update Design

**Date:** 2026-04-11
**Scope:** Update all pinned dependencies in `requirements.txt` and `requirements-dev.txt` to latest stable versions.

---

## Approach

Phased update: runtime dependencies first, dev tools second. This isolates failures — if something breaks, it's immediately clear which group caused it.

---

## Phase 1 — Core Runtime Dependencies

**File:** `requirements.txt`

| Package | Current | Target |
|---|---|---|
| PyQt6 | 6.7.1 | 6.11.0 |
| SQLAlchemy | 2.0.31 | 2.0.49 |
| alembic | 1.13.2 | 1.18.4 |
| qt-material | 2.14 | 2.17 |
| requests | 2.32.3 | 2.33.1 |
| openpyxl | 3.1.5 | 3.1.5 (no change) |

**Steps:**
1. Update pins in `requirements.txt`
2. Reinstall: `pip install -r requirements.txt`
3. Run test suite: `pytest tests/ -v`
4. Manual smoke test: launch app and exercise main flows
   - Add item (serialized and non-serialized)
   - Edit item
   - Transfer items between locations
   - View transaction history
   - Toggle theme (light/dark)
   - Export to Excel
5. Commit: `chore: bump core runtime dependencies`

**Risk notes:**
- PyQt6 6.7 → 6.11 is the highest risk item — 4 minor versions, may have API deprecations or subtle UI/rendering changes. The manual smoke test is the primary guard here.
- SQLAlchemy, alembic, requests are patch/minor bumps within the same major — low risk.
- qt-material 2.14 → 2.17 — low risk, same major.

---

## Phase 2 — Dev Tools

**File:** `requirements-dev.txt`

| Package | Current | Target | Note |
|---|---|---|---|
| pytest | 8.1.1 | 9.0.3 | Major — removed deprecated features, new `pytest.toml` config |
| pytest-cov | 4.1.0 | 7.1.0 | Major — 3 version jump |
| pytest-mock | 3.12.0 | 3.15.1 | Minor |
| black | 24.3.0 | 26.3.1 | Major — will reformat source files |
| mypy | 1.9.0 | 1.20.0 | Minor |
| isort | 5.13.2 | 8.0.1 | Major — will re-sort imports |
| flake8 | 7.0.0 | 7.3.0 | Patch |
| Pillow | 12.1.1 | 12.2.0 | Patch |

**Steps:**
1. Update pins in `requirements-dev.txt`
2. Reinstall: `pip install -r requirements-dev.txt`
3. Run test suite: `pytest tests/ -v` — fix any pytest 9 breakage before proceeding
4. Run `black src/ tests/` — applies reformatting
5. Run `isort src/ tests/` — re-sorts imports
6. Run `flake8 src/` — verify no new lint errors introduced by reformatting
7. Single commit with all changes: `chore: bump dev dependencies and reformat with black/isort`

**Risk notes:**
- pytest 9 removes features deprecated in 8.x — if any test uses deprecated fixtures or config, it will fail. Fix before committing.
- black 26 style changes are typically minor (trailing comma handling, string quoting) but will touch many files — expected and intentional.
- isort 8 is a major version but existing config options are broadly compatible.
- pytest-cov 4 → 7 jumped 3 major versions — watch for CLI flag or config changes.

---

## Success Criteria

- All 9 test files pass (`tests/`) after each phase
- No new flake8 errors after phase 2
- Manual smoke test passes after phase 1
- CI pipeline (`build.yml`) passes on the updated branch

---

## Out of Scope

- Upgrading Python itself (currently 3.14)
- Changing any source code beyond what black/isort reformatting produces
- Adding new dependencies
