# Theme Dimensions Guide - Height Control

## Fields Responsible for Button and Field Heights

All dimension values are stored in the `ThemeDimensions` dataclass in `theme_config.py`.

---

## 📏 Height Fields

### 1. **`input_height`** - Input Field Height
**Controls:** Height of all input fields
- QLineEdit (text inputs)
- Search boxes
- Serial number fields
- Type/subtype fields

**Current Value:** `28` pixels

**Where it's used:**
```python
# In styles.py
def apply_input_style(widget, large=False):
    widget.setMinimumHeight(Dimensions.get_input_height())
```

**Example in theme_config.py:**
```python
dimensions=ThemeDimensions(
    input_height=28,  # ← THIS controls input field height
    button_height=25,
    ...
)
```

---

### 2. **`button_height`** - Button Height
**Controls:** Height of all buttons
- Primary buttons (Add, Save)
- Danger buttons (Delete, Cancel)
- Info buttons (Search)
- Secondary buttons (Clear, Close)

**Current Value:** `25` pixels

**Where it's used:**
```python
# In styles.py
def apply_button_style(button, style="primary"):
    button.setMinimumHeight(Dimensions.get_button_height())
```

**Example in theme_config.py:**
```python
dimensions=ThemeDimensions(
    input_height=28,
    button_height=25,  # ← THIS controls button height
    ...
)
```

---

## 🎯 Other Dimension Fields

### 3. **`button_min_width`** - Button Minimum Width
**Controls:** Minimum width of buttons
**Current Value:** `100` pixels

### 4. **`button_padding`** - Button Internal Padding
**Controls:** Space inside buttons around text
**Current Value:** `10` pixels

### 5. **`border_radius`** - Corner Rounding
**Controls:** How rounded the corners are
**Current Value:** `4` pixels

### 6. **`font_size`** - Normal Font Size
**Controls:** Default text size in inputs and buttons
**Current Value:** `13` pixels

### 7. **`font_size_large`** - Large Font Size
**Controls:** Large text size (when `large=True`)
**Current Value:** `14` pixels

---

## 📝 How to Change Heights

### Option 1: Edit theme_config.py Directly

```python
# In theme_config.py

LIGHT = ThemeParameters(
    name="Light",
    mode="light",
    qt_material_theme="light_blue.xml",
    colors=ThemeColors(...),
    dimensions=ThemeDimensions(
        input_height=36,        # ← CHANGE THIS (was 28)
        button_height=32,       # ← CHANGE THIS (was 25)
        button_min_width=120,   # ← CHANGE THIS (was 100)
        button_padding=12,      # ← CHANGE THIS (was 10)
        border_radius=6,        # ← CHANGE THIS (was 4)
        font_size=14,           # ← CHANGE THIS (was 13)
        font_size_large=16      # ← CHANGE THIS (was 14)
    )
)

DARK = ThemeParameters(
    # Same structure - change values here too
    ...
)
```

### Option 2: Create a New Theme with Different Sizes

```python
LARGE = ThemeParameters(
    name="Large",
    mode="light",
    qt_material_theme="light_blue.xml",
    colors=ThemeColors(...),
    dimensions=ThemeDimensions(
        input_height=40,        # Larger inputs
        button_height=36,       # Larger buttons
        button_min_width=140,   # Wider buttons
        button_padding=14,      # More padding
        border_radius=6,
        font_size=15,           # Bigger font
        font_size_large=17
    )
)
```

---

## 🔍 Current Values Summary

| Field | Light Theme | Dark Theme | Description |
|-------|-------------|------------|-------------|
| **input_height** | 28px | 28px | Input field height |
| **button_height** | 25px | 25px | Button height |
| button_min_width | 100px | 100px | Button minimum width |
| button_padding | 10px | 10px | Internal button padding |
| border_radius | 4px | 4px | Corner rounding |
| font_size | 13px | 13px | Normal text size |
| font_size_large | 14px | 14px | Large text size |

---

## 📍 Where These Are Applied

### Input Fields
```python
# styles.py - apply_input_style()
widget.setMinimumHeight(Dimensions.get_input_height())  # ← Uses input_height
widget.setStyleSheet(f"""
    QLineEdit {{
        font-size: {Dimensions.get_font_size()}px;  # ← Uses font_size
        padding: {Dimensions.INPUT_PADDING}px;
        border-radius: {Dimensions.get_border_radius()}px;  # ← Uses border_radius
        ...
    }}
""")
```

### Buttons
```python
# styles.py - apply_button_style()
button.setMinimumWidth(Dimensions.get_button_min_width())  # ← Uses button_min_width
button.setMinimumHeight(Dimensions.get_button_height())    # ← Uses button_height
button.setStyleSheet(f"""
    QPushButton {{
        padding: {Dimensions.get_button_padding()}px;      # ← Uses button_padding
        border-radius: {Dimensions.get_border_radius()}px; # ← Uses border_radius
        min-height: {Dimensions.get_button_height()}px;    # ← Uses button_height
        ...
    }}
""")
```

---

## 🎨 Visual Reference

```
┌─────────────────────────────────────┐
│  Input Field (QLineEdit)            │  ← input_height = 28px
│  font_size = 13px                   │
└─────────────────────────────────────┘

┌──────────────┐
│    Button    │  ← button_height = 25px
│  Save (13px) │  ← font_size = 13px
└──────────────┘
 ↑            ↑
 button_padding = 10px
 button_min_width = 100px
```

---

## 💡 Recommended Values

### For Comfortable UI (Current):
- input_height: 28-32px
- button_height: 25-28px

### For Large/Accessible UI:
- input_height: 36-40px
- button_height: 32-36px
- font_size: 14-15px

### For Compact UI:
- input_height: 24-26px
- button_height: 22-24px
- font_size: 12px

---

## ⚠️ Important Notes

1. **Changes take effect immediately** when you switch themes (after saving theme_config.py)
2. **Both Light and Dark themes** can have different dimension values
3. **All widgets automatically use** these values through the helper functions
4. **No need to modify individual dialogs** - dimensions are centralized

---

## 🔧 Quick Example: Making Everything Bigger

```python
# In theme_config.py - Light theme
dimensions=ThemeDimensions(
    input_height=36,        # +8px (was 28)
    button_height=32,       # +7px (was 25)
    button_min_width=120,   # +20px (was 100)
    button_padding=12,      # +2px (was 10)
    border_radius=6,        # +2px (was 4)
    font_size=14,           # +1px (was 13)
    font_size_large=16      # +2px (was 14)
)
```

Save, restart app, and all buttons and fields will be larger!
