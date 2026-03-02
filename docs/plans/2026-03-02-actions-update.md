# GitHub Actions Version Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update `actions/checkout` to v6 and `actions/setup-python` to v6 with `cache: 'pip'` across both workflow files.

**Architecture:** Pure find-and-replace across two YAML files — no logic changes, no new steps, no structural changes. `build-windows` has no `setup-python` so only its `checkout` is updated. `softprops/action-gh-release@v2` is already current and untouched.

**Tech Stack:** GitHub Actions YAML

---

### Task 1: Update `.github/workflows/test.yml`

**Files:**
- Modify: `.github/workflows/test.yml`

**Step 1: Update `actions/checkout` from v4 to v6**

Change line 13:
```yaml
        uses: actions/checkout@v4
```
to:
```yaml
        uses: actions/checkout@v6
```

**Step 2: Update `actions/setup-python` from v4 to v6 and add `cache: 'pip'`**

Change lines 16-18:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
```
to:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'
```

**Step 3: Verify YAML syntax**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"
```
Expected: `OK`

**Step 4: Verify the changes**

Run:
```bash
grep -n "checkout\|setup-python\|cache:" .github/workflows/test.yml
```
Expected output should show:
- `checkout@v6`
- `setup-python@v6`
- `cache: 'pip'`

**Step 5: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: bump checkout to v6, setup-python to v6 with pip cache in test.yml"
```

---

### Task 2: Update `.github/workflows/build.yml`

**Files:**
- Modify: `.github/workflows/build.yml`

There are 4 `checkout` occurrences and 3 `setup-python` occurrences (the `build-windows` job has no `setup-python`).

**Step 1: Update all 4 `actions/checkout@v4` to `actions/checkout@v6`**

The 4 occurrences are in: `test` job, `build-windows`, `build-macos`, `build-linux`.

Replace every instance of:
```yaml
        uses: actions/checkout@v4
```
with:
```yaml
        uses: actions/checkout@v6
```

**Step 2: Update `setup-python` in the `test` job (lines ~21-23)**

Change:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
```
to:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'
```

**Step 3: Update `setup-python` in `build-macos` (lines ~77-79)**

Change:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
```
to:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'
```

**Step 4: Update `setup-python` in `build-linux` (lines ~114-116)**

Change:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
```
to:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'
```

**Step 5: Verify YAML syntax**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('OK')"
```
Expected: `OK`

**Step 6: Verify all occurrences updated**

Run:
```bash
grep -n "checkout\|setup-python\|cache:" .github/workflows/build.yml
```
Expected:
- 4 lines with `checkout@v6` (none with `checkout@v4`)
- 3 lines with `setup-python@v6` (none with `setup-python@v4`)
- 3 lines with `cache: 'pip'`

Also confirm `build-windows` has NO `setup-python` (it should only have `checkout@v6`):
```bash
grep -A 30 "build-windows:" .github/workflows/build.yml | grep "setup-python"
```
Expected: no output

**Step 7: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: bump checkout to v6, setup-python to v6 with pip cache in build.yml"
```
