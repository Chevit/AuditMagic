# Remove pytest-qt Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove `pytest-qt` from `requirements-dev.txt` to fix the `libEGL.so.1` CI crash.

**Architecture:** Single line deletion from `requirements-dev.txt`. No tests use `pytest-qt` — confirmed by grep. No other files change.

**Tech Stack:** pip, pytest

---

### Task 1: Remove `pytest-qt` from `requirements-dev.txt`

**Files:**
- Modify: `requirements-dev.txt:4`

**Step 1: Delete the `pytest-qt` line**

Open `requirements-dev.txt`. It currently looks like:

```
# Development dependencies (pinned for reproducibility)
-r requirements.txt
pytest==8.1.1
pytest-qt==4.4.0
pytest-cov==4.1.0
pytest-mock==3.12.0
black==24.3.0
mypy==1.9.0
isort==5.13.2
flake8==7.0.0
pyinstaller
icnsutil==1.1.0
Pillow==12.1.1
```

Remove the `pytest-qt==4.4.0` line. Result:

```
# Development dependencies (pinned for reproducibility)
-r requirements.txt
pytest==8.1.1
pytest-cov==4.1.0
pytest-mock==3.12.0
black==24.3.0
mypy==1.9.0
isort==5.13.2
flake8==7.0.0
pyinstaller
icnsutil==1.1.0
Pillow==12.1.1
```

**Step 2: Verify no test file uses pytest-qt**

Run:
```bash
grep -r "qtbot\|QApplication\|pytest_qt\|qt_app" tests/
```
Expected: no output (zero matches)

**Step 3: Run tests locally to confirm nothing broke**

Run:
```bash
.venv/Scripts/python -m pytest tests/ -q
```
Expected: `144 passed`

**Step 4: Commit**

```bash
git add requirements-dev.txt
git commit -m "fix: remove pytest-qt to fix libEGL.so.1 CI crash"
```
