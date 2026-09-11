"""Shared helper to make a QCompleter's popup behave on selection.

QCompleter's popup is supposed to close as soon as the user picks a
suggestion (click or Enter), but two things around it can leave it open:

1. A field's own refetch handler reacting to the resulting text change
   (``textChanged`` -> ``setModel()``) races with Qt's own close.
2. A *later*, debounced side effect of that same text change -- e.g. a
   status label that goes from empty to populated and resizes the dialog
   -- can leave the popup visible again well after the selection.

This helper removes both races: it force-hides the popup on every
selection, and hands the caller two independent guards so both the
immediate refetch handler and any later debounced handler can tell
"this text is a fresh, unedited selection" and react accordingly.

It also closes a third gap that isn't a race at all: QCompleter's
``activated`` signal -- the one that means "selection committed" -- only
fires on a real *activation*, and whether a single click counts as one is
governed by the platform style's ``SH_ItemView_ActivateItemOnSingleClick``
hint (Qt docs, QAbstractItemView). On styles where a single click doesn't
count (observed on macOS), the click still fires the popup's own
``clicked`` and (via Qt's built-in QLineEdit/QCompleter wiring) the
completer's ``highlighted`` signal -- so the line edit's text updates, but
``activated`` -- and therefore any popup-hiding tied to it -- waits for a
second click or Enter. Connecting our hide logic to the popup's `clicked`
as well makes a single click commit, matching what every other completer
field already does.
"""

from typing import Callable, NamedTuple

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QCompleter, QLineEdit


class SelectionGuard(NamedTuple):
    """Two views onto the same "was this a selection, not typing" state.

    ``consume_refetch_guard``: one-shot, for the field's own refetch
    handler (its ``textChanged`` slot). True exactly once, right after a
    selection, so that handler can skip its redundant ``setModel()`` call.

    ``consume_recent_selection``: also cleared by genuine typing (the
    line edit's ``textEdited``), for a handler that runs *later* (e.g.
    behind a debounce timer) and needs to know whether the field's
    current text still reflects an unedited selection, so it can
    defensively re-hide a popup a delayed side effect might otherwise
    leave visible.
    """

    consume_refetch_guard: Callable[[], bool]
    consume_recent_selection: Callable[[], bool]


def hide_popup(completer: QCompleter) -> None:
    """Hide ``completer``'s popup, if it has one. Safe to call anytime."""
    popup = completer.popup()
    if popup is not None:
        popup.hide()


def install_selection_hiding(
    completer: QCompleter, line_edit: QLineEdit
) -> SelectionGuard:
    """Force-hide ``completer``'s popup whenever the user picks a suggestion.

    Wire this once per QCompleter, right after it's created, passing the
    QLineEdit it's attached to.
    """
    state = {"refetch": False, "recent": False}

    def _on_commit(*_args: object) -> None:
        state["refetch"] = True
        state["recent"] = True
        hide_popup(completer)
        # Deferred to the next event-loop turn too: guards against any
        # same-turn setModel()/refetch (ours or Qt's own) re-showing the
        # popup after this handler returns.
        QTimer.singleShot(0, lambda: hide_popup(completer))

    def _on_text_edited(_text: str = "") -> None:
        state["recent"] = False  # real typing, not a leftover selection

    completer.activated[str].connect(_on_commit)  # Enter, or a real click-activation
    popup = completer.popup()
    if popup is not None:
        # Fires on every single click regardless of the platform's
        # activate-on-single-click style hint -- see module docstring.
        popup.clicked.connect(_on_commit)
    line_edit.textEdited.connect(_on_text_edited)

    def consume_refetch_guard() -> bool:
        if state["refetch"]:
            state["refetch"] = False
            return True
        return False

    def consume_recent_selection() -> bool:
        if state["recent"]:
            state["recent"] = False
            return True
        return False

    return SelectionGuard(consume_refetch_guard, consume_recent_selection)
