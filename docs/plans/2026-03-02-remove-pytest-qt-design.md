# Remove pytest-qt Design

**Date:** 2026-03-02

## Problem

CI test job crashes on startup with:
```
ImportError: libEGL.so.1: cannot open shared object file: No such file or directory
```

`pytest-qt` auto-loads at pytest startup and immediately imports `QtGui` from PyQt6, which requires `libEGL.so.1` — a system graphics library not present on `ubuntu-latest` runners.

## Root Cause

`pytest-qt==4.4.0` is in `requirements-dev.txt` but no test in the suite uses any `pytest-qt` features (`qtbot`, `QApplication`, etc.). It was added speculatively and is unused.

## Fix

Remove `pytest-qt==4.4.0` from `requirements-dev.txt`. Single line deletion, no other changes needed.

## What Does NOT Change

- No workflow file edits
- No `conftest.py` changes
- No `pytest.ini` needed
- No system library installs
