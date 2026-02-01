from enum import Enum
from typing import Dict


class Language(Enum):
    UKRAINIAN = "uk"
    ENGLISH = "en"


# Current application language - Ukrainian is primary
_current_language: Language = Language.UKRAINIAN


def set_language(language: Language) -> None:
    """Set the current application language."""
    global _current_language
    _current_language = language


def get_language() -> Language:
    """Get the current application language."""
    return _current_language


def tr(key: str) -> str:
    """Translate a key to the current language."""
    translations = _TRANSLATIONS.get(_current_language, _TRANSLATIONS[Language.ENGLISH])
    return translations.get(key, _TRANSLATIONS[Language.ENGLISH].get(key, key))


# Translation dictionaries
_TRANSLATIONS: Dict[Language, Dict[str, str]] = {
    Language.UKRAINIAN: {
        # Common
        "app.title": "Менеджер інвентарю",
        "button.add": "Додати",
        "button.cancel": "Скасувати",
        "button.close": "Закрити",
        "button.save": "Зберегти",
        "button.delete": "Видалити",
        "button.edit": "Редагувати",
        "button.yes": "Так",
        "button.no": "Ні",

        # Item fields
        "field.id": "ID",
        "field.type": "Тип",
        "field.subtype": "Підтип",
        "field.quantity": "Кількість",
        "field.serial_number": "Серійний номер",

        # Labels with colons
        "label.id": "ID:",
        "label.type": "Тип:",
        "label.subtype": "Підтип:",
        "label.quantity": "Кількість:",
        "label.serial_number": "Серійний номер:",

        # Placeholders
        "placeholder.type": "Введіть тип...",
        "placeholder.subtype": "Введіть підтип (необов'язково)...",
        "placeholder.serial_number": "Введіть серійний номер (необов'язково)...",

        # Dialog titles
        "dialog.add_item.title": "Додати новий елемент",
        "dialog.add_item.header": "Додати новий елемент інвентарю",
        "dialog.details.title": "Деталі елемента",
        "dialog.edit.title": "Редагувати елемент",
        "dialog.confirm_delete.title": "Підтвердження видалення",

        # Context menu
        "menu.edit": "Редагувати",
        "menu.details": "Переглянути деталі",
        "menu.delete": "Видалити",

        # Messages
        "message.confirm_delete": "Ви впевнені, що хочете видалити цей елемент?",
        "message.validation_error": "Помилка валідації",
        "message.fix_errors": "Будь ласка, виправте наступні помилки:",
        "message.type_required": "Тип є обов'язковим",

        # Main window
        "main.add_item": "Додати елемент",
    },

    Language.ENGLISH: {
        # Common
        "app.title": "Inventory Manager",
        "button.add": "Add",
        "button.cancel": "Cancel",
        "button.close": "Close",
        "button.save": "Save",
        "button.delete": "Delete",
        "button.edit": "Edit",
        "button.yes": "Yes",
        "button.no": "No",

        # Item fields
        "field.id": "ID",
        "field.type": "Type",
        "field.subtype": "Sub-type",
        "field.quantity": "Quantity",
        "field.serial_number": "Serial Number",

        # Labels with colons
        "label.id": "ID:",
        "label.type": "Type:",
        "label.subtype": "Sub-type:",
        "label.quantity": "Quantity:",
        "label.serial_number": "Serial Number:",

        # Placeholders
        "placeholder.type": "Enter item type...",
        "placeholder.subtype": "Enter item sub-type (optional)...",
        "placeholder.serial_number": "Enter serial number (optional)...",

        # Dialog titles
        "dialog.add_item.title": "Add New Item",
        "dialog.add_item.header": "Add New Inventory Item",
        "dialog.details.title": "Item Details",
        "dialog.edit.title": "Edit Item",
        "dialog.confirm_delete.title": "Confirm Delete",

        # Context menu
        "menu.edit": "Edit",
        "menu.details": "See Details",
        "menu.delete": "Delete",

        # Messages
        "message.confirm_delete": "Are you sure you want to delete this item?",
        "message.validation_error": "Validation Error",
        "message.fix_errors": "Please fix the following errors:",
        "message.type_required": "Type is required",

        # Main window
        "main.add_item": "Add Item",
    }
}
