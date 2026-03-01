"""One-time script to update imports after src/ restructure."""
import os
import re

# Map: old import prefix → new import prefix
# Order matters: more specific patterns first
REPLACEMENTS = [
    # ui_entities submodules → new subdirectories
    (r"from ui_entities\.inventory_list_view\b", "from ui.widgets.inventory_list_view"),
    (r"from ui_entities\.inventory_delegate\b", "from ui.widgets.inventory_delegate"),
    (r"from ui_entities\.inventory_model\b", "from ui.models.inventory_model"),
    (r"from ui_entities\.inventory_item\b", "from ui.models.inventory_item"),
    (r"from ui_entities\.location_selector\b", "from ui.widgets.location_selector"),
    (r"from ui_entities\.search_widget\b", "from ui.widgets.search_widget"),
    (r"from ui_entities\.main_window\b", "from ui.main_window"),
    (r"from ui_entities\.translations\b", "from ui.translations"),
    # All remaining ui_entities.* → ui.dialogs.*
    (r"from ui_entities\.", "from ui.dialogs."),
    # Core backend
    (r"from models\b", "from core.models"),
    (r"from services\b", "from core.services"),
    (r"from repositories\b", "from core.repositories"),
    (r"from db\b", "from core.db"),
    (r"from config\b", "from core.config"),
    (r"from logger\b", "from core.logger"),
    (r"from export_service\b", "from core.export_service"),
    # UI helpers (were at root, now in src/ui/)
    (r"from styles\b", "from ui.styles"),
    (r"from theme_config\b", "from ui.theme_config"),
    (r"from theme_manager\b", "from ui.theme_manager"),
    (r"from translations\b", "from ui.translations"),
    (r"from validators\b", "from ui.validators"),
]

SEARCH_DIRS = ["src", "tests", "alembic"]
EXTENSIONS = {".py"}


def fix_file(path: str) -> bool:
    with open(path, encoding="utf-8") as f:
        original = f.read()
    updated = original
    for pattern, replacement in REPLACEMENTS:
        updated = re.sub(pattern, replacement, updated)
    if updated != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"  Updated: {path}")
        return True
    return False


changed = []
for search_dir in SEARCH_DIRS:
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if os.path.splitext(fname)[1] in EXTENSIONS:
                fpath = os.path.join(root, fname)
                if fix_file(fpath):
                    changed.append(fpath)

print(f"\nDone. {len(changed)} files updated.")
