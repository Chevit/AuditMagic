"""Tests for UI translation key completeness."""


def test_auto_update_translation_keys_present():
    from ui.translations import tr

    keys = [
        "update.install",
        "update.downloading",
        "update.error",
    ]
    for key in keys:
        assert tr(key) != key, f"Translation key missing: {key!r}"


def test_serialized_feature_translation_keys_present():
    from ui.translations import tr

    keys = [
        "label.serialized_badge",
        "label.non_serialized_badge",
        "label.is_serialized",
        "tooltip.serialized_locked",
        "tooltip.serialized_auto",
        "error.serialized_conflict",
        "message.type_exists_serialized",
        "message.type_exists_non_serialized",
    ]
    for key in keys:
        assert tr(key) != key, f"Translation key missing: {key!r}"
