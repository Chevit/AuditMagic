from enum import Enum
from typing import Dict

from config import config
from logger import logger


class Language(Enum):
    UKRAINIAN = "uk"
    ENGLISH = "en"


# Initialize language from config
_current_language: Language = Language(config.get("language", "uk"))


def set_language(language: Language) -> None:
    """Set the current application language and save to config."""
    global _current_language
    _current_language = language
    config.set("language", language.value)
    logger.info(f"Language changed to: {language.value}")


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
        "button.search": "Пошук",
        "button.clear": "Очистити",
        "button.add_quantity": "Додати кількість",
        "button.remove_quantity": "Зменшити кількість",
        "button.transactions": "Транзакції",
        "button.delete_selected": "Видалити вибраний",
        # Item fields
        "field.id": "ID",
        "field.type": "Тип",
        "field.subtype": "Підтип",
        "field.quantity": "Кількість",
        "field.serial_number": "Серійний номер",
        "field.details": "Деталі",
        "field.notes": "Нотатки",
        "field.created_at": "Створено",
        "field.updated_at": "Оновлено",
        "field.edit_reason": "Причина зміни",
        # Labels with colons
        "label.id": "ID:",
        "label.type": "Тип:",
        "label.subtype": "Підтип:",
        "label.quantity": "Кількість:",
        "label.serial_number": "Серійний номер:",
        "label.details": "Деталі:",
        "label.notes": "Нотатки:",
        "label.edit_reason": "Причина зміни:",
        "label.search": "Пошук:",
        "label.search_field": "Поле пошуку:",
        "label.recent_searches": "Останні пошуки:",
        "label.has_serial": "Серійний товар:",
        "label.has_serial_items": "Цей тип має серійні номери",
        "tooltip.has_serial": "Позначте, якщо цей тип товару має унікальні серійні номери. Кількість буде зафіксована на 1.",
        "error.serial.required": "Серійний номер обов'язковий для серійних товарів",
        "error.serial.not_allowed": "Серійний номер не дозволений для несерійних товарів",
        "error.generic.title": "Помилка",
        "error.generic.message": "Виникла помилка при виконанні операції:",
        # Placeholders
        "placeholder.quantity": "Введіть кількість...",
        "placeholder.type": "Введіть тип...",
        "placeholder.subtype": "Введіть підтип (необов'язково)...",
        "placeholder.serial_number": "Введіть серійний номер (необов'язково)...",
        "placeholder.details": "Введіть деталі (необов'язково)...",
        "placeholder.notes": "Введіть нотатки (необов'язково)...",
        "placeholder.edit_reason": "Вкажіть причину зміни (обов'язково)...",
        "label.initial_notes": "Початкові нотатки:",
        "placeholder.initial_notes": "Необов'язкові нотатки для першого запису…",
        "placeholder.search": "Введіть для пошуку...",
        # Dialog titles
        "dialog.add_item.title": "Додати новий елемент",
        "dialog.add_item.header": "Додати новий елемент інвентарю",
        "dialog.details.title": "Деталі елемента",
        "dialog.details.serial_numbers": "Серійні номери",
        "dialog.details.serial_count": "Всього серійних номерів: {count}",
        "dialog.edit.title": "Редагувати елемент",
        "dialog.edit.header": "Редагувати елемент інвентарю",
        "dialog.confirm_delete.title": "Підтвердження видалення",
        "dialog.transactions.title": "Історія транзакцій",
        "dialog.quantity.title": "Змінити кількість",
        "dialog.quantity.add_header": "Додати кількість",
        "dialog.quantity.remove_header": "Зменшити кількість",
        # Context menu
        "menu.edit": "Редагувати",
        "menu.details": "Переглянути деталі",
        "menu.delete": "Видалити",
        "menu.add_quantity": "Додати кількість",
        "menu.remove_quantity": "Зменшити кількість",
        "menu.transactions": "Переглянути транзакції",
        # Theme menu
        "menu.theme": "Тема",
        "menu.theme.mode": "Режим",
        "menu.theme.light": "Світла",
        "menu.theme.dark": "Темна",
        "menu.theme.variant": "Варіант кольору",
        "menu.theme.variant.default": "За замовчуванням (Синій)",
        "menu.theme.variant.teal": "Бірюзовий",
        "menu.theme.variant.cyan": "Блакитний",
        "menu.theme.variant.purple": "Фіолетовий",
        "menu.theme.variant.pink": "Рожевий",
        "menu.theme.variant.amber": "Бурштиновий",
        # Messages
        "message.confirm_delete": "Ви впевнені, що хочете видалити цей елемент?",
        "message.validation_error": "Помилка валідації",
        "message.fix_errors": "Будь ласка, виправте наступні помилки:",
        "message.type_required": "Тип є обов'язковим",
        "message.quantity_positive": "Кількість має бути більше нуля",
        "message.not_enough_quantity": "Недостатньо товару на складі",
        "message.no_results": "Нічого не знайдено",
        "message.theme.changed": "Тему змінено",
        "message.theme.changed.text": "Нова тема застосована успішно!",
        "menu.add_serial_number": "Додати серійний номер",
        "menu.remove_serial_number": "Видалити серійний номер",
        "dialog.add_serial.title": "Додати серійний номер",
        "dialog.add_serial.header": "Додати новий серійний номер",
        "dialog.remove_serial.title": "Видалити серійні номери",
        "dialog.remove_serial.header": "Оберіть серійні номери для видалення",
        "dialog.remove_serial.confirm": "Видалити вибрані ({count})?",
        "error.no_serial_selected": "Оберіть хоча б один серійний номер",
        "error.cannot_delete_all_serials": "Не можна видалити всі серійні номери. Використовуйте \"Видалити\" для повного видалення.",
        "label.notes_reason": "Причина / примітки",
        "message.select_serial_to_delete": "Виберіть серійний номер для видалення",
        "message.confirm_delete_serial": "Ви впевнені, що хочете видалити серійний номер {serial}?",
        "message.at_least_one_serial": "Повинен залишитись хоча б один серійний номер",
        "message.quantity_required": "Кількість є обов'язковою",
        "message.quantity_invalid": "Кількість має бути числом",
        # Main window
        "main.add_item": "Додати елемент",
        # Search
        "search.all_fields": "Всі поля",
        "search.field.item_type": "Тип",
        "search.field.sub_type": "Підтип",
        "search.field.details": "Деталі",
        "search.field.serial": "Серійний номер",
        "search.field.location": "Місцезнаходження",
        # Transactions
        "transaction.type.add": "Додавання",
        "transaction.type.remove": "Видалення",
        "transaction.type.edit": "Редагування",
        "transaction.column.date": "Дата",
        "transaction.column.type": "Тип",
        "transaction.column.change": "Зміна",
        "transaction.column.before": "До",
        "transaction.column.after": "Після",
        "transaction.column.notes": "Нотатки",
        "transaction.filter.start_date": "Дата початку:",
        "transaction.filter.end_date": "Дата кінця:",
        "transaction.filter.apply": "Застосувати фільтр",
        # Transaction notes
        "transaction.notes.initial": "Початковий інвентар",
        "transaction.notes.merged": "Додано через створення нового елемента",
        "transaction.notes.added_serial": "Додано серійний номер",
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
        "button.search": "Search",
        "button.clear": "Clear",
        "button.add_quantity": "Add Quantity",
        "button.remove_quantity": "Remove Quantity",
        "button.transactions": "Transactions",
        "button.delete_selected": "Delete Selected",
        # Item fields
        "field.id": "ID",
        "field.type": "Type",
        "field.subtype": "Sub-type",
        "field.quantity": "Quantity",
        "field.serial_number": "Serial Number",
        "field.details": "Details",
        "field.notes": "Notes",
        "field.created_at": "Created At",
        "field.updated_at": "Updated At",
        "field.edit_reason": "Reason for change",
        # Labels with colons
        "label.id": "ID:",
        "label.type": "Type:",
        "label.subtype": "Sub-type:",
        "label.quantity": "Quantity:",
        "label.serial_number": "Serial Number:",
        "label.details": "Details:",
        "label.notes": "Notes:",
        "label.edit_reason": "Reason for change:",
        "label.search": "Search:",
        "label.search_field": "Search field:",
        "label.has_serial": "Serialized Item:",
        "label.has_serial_items": "This type has serial numbers",
        "tooltip.has_serial": "Check if this item type has unique serial numbers. Quantity will be fixed at 1.",
        "error.serial.required": "Serial number required for serialized items",
        "error.serial.not_allowed": "Serial number not allowed for non-serialized items",
        "error.generic.title": "Error",
        "error.generic.message": "An error occurred while performing the operation:",
        "label.recent_searches": "Recent searches:",
        # Placeholders
        "placeholder.quantity": "Enter quantity...",
        "placeholder.type": "Enter item type...",
        "placeholder.subtype": "Enter item sub-type (optional)...",
        "placeholder.serial_number": "Enter serial number (optional)...",
        "placeholder.details": "Enter details (optional)...",
        "placeholder.notes": "Enter notes (optional)...",
        "placeholder.edit_reason": "Specify reason for change (required)...",
        "label.initial_notes": "Initial Notes:",
        "placeholder.initial_notes": "Optional notes for the first inventory record…",
        "placeholder.search": "Type to search...",
        # Dialog titles
        "dialog.add_item.title": "Add New Item",
        "dialog.add_item.header": "Add New Inventory Item",
        "dialog.details.title": "Item Details",
        "dialog.details.serial_numbers": "Serial Numbers",
        "dialog.details.serial_count": "Total Serial Numbers: {count}",
        "dialog.edit.title": "Edit Item",
        "dialog.edit.header": "Edit Inventory Item",
        "dialog.confirm_delete.title": "Confirm Delete",
        "dialog.transactions.title": "Transaction History",
        "dialog.quantity.title": "Change Quantity",
        "dialog.quantity.add_header": "Add Quantity",
        "dialog.quantity.remove_header": "Remove Quantity",
        # Context menu
        "menu.edit": "Edit",
        "menu.details": "See Details",
        "menu.delete": "Delete",
        "menu.add_quantity": "Add Quantity",
        "menu.remove_quantity": "Remove Quantity",
        "menu.transactions": "View Transactions",
        # Theme menu
        "menu.theme": "Theme",
        "menu.theme.mode": "Mode",
        "menu.theme.light": "Light",
        "menu.theme.dark": "Dark",
        "menu.theme.variant": "Color Variant",
        "menu.theme.variant.default": "Default (Blue)",
        "menu.theme.variant.teal": "Teal",
        "menu.theme.variant.cyan": "Cyan",
        "menu.theme.variant.purple": "Purple",
        "menu.theme.variant.pink": "Pink",
        "menu.theme.variant.amber": "Amber",
        # Messages
        "message.confirm_delete": "Are you sure you want to delete this item?",
        "message.validation_error": "Validation Error",
        "message.fix_errors": "Please fix the following errors:",
        "message.type_required": "Type is required",
        "message.quantity_positive": "Quantity must be greater than zero",
        "message.not_enough_quantity": "Not enough items in stock",
        "message.no_results": "No results found",
        "message.theme.changed": "Theme Changed",
        "message.theme.changed.text": "New theme applied successfully!",
        "menu.add_serial_number": "Add Serial Number",
        "menu.remove_serial_number": "Remove Serial Number",
        "dialog.add_serial.title": "Add Serial Number",
        "dialog.add_serial.header": "Add New Serial Number",
        "dialog.remove_serial.title": "Remove Serial Numbers",
        "dialog.remove_serial.header": "Select Serial Numbers to Remove",
        "dialog.remove_serial.confirm": "Delete selected ({count})?",
        "error.no_serial_selected": "Select at least one serial number",
        "error.cannot_delete_all_serials": "Cannot delete all serial numbers. Use \"Delete\" for complete removal.",
        "label.notes_reason": "Reason / Notes",
        "message.select_serial_to_delete": "Select a serial number to delete",
        "message.confirm_delete_serial": "Are you sure you want to delete serial number {serial}?",
        "message.at_least_one_serial": "At least one serial number must remain",
        "message.quantity_required": "Quantity is required",
        "message.quantity_invalid": "Quantity must be a number",
        # Main window
        "main.add_item": "Add Item",
        # Search
        "search.all_fields": "All fields",
        "search.field.item_type": "Type",
        "search.field.sub_type": "Sub-type",
        "search.field.details": "Details",
        "search.field.serial": "Serial Number",
        "search.field.location": "Location",
        # Transactions
        "transaction.type.add": "Add",
        "transaction.type.remove": "Remove",
        "transaction.type.edit": "Edit",
        "transaction.column.date": "Date",
        "transaction.column.type": "Type",
        "transaction.column.change": "Change",
        "transaction.column.before": "Before",
        "transaction.column.after": "After",
        "transaction.column.notes": "Notes",
        "transaction.filter.start_date": "Start date:",
        "transaction.filter.end_date": "End date:",
        "transaction.filter.apply": "Apply Filter",
        # Transaction notes
        "transaction.notes.initial": "Initial inventory",
        "transaction.notes.merged": "Added via new item entry",
        "transaction.notes.added_serial": "Added serial number",
    },
}
