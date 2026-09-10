# Split Add Item into two mode-specific dialogs, chosen upfront

`AddItemDialog` handled both Serialized and non-serialized Item Types in one form,
toggled by a checkbox that also auto-locked itself (and silently overrode the user's
choice) when the typed Item Type already existed with the other serialization. We
replaced it with an upfront chooser ("With Serial Number" / "Without Serial Number")
that opens one of two fixed-mode dialogs, each showing only the fields relevant to
that mode (no checkbox, no dead "quantity = 1" widget).

We considered keeping the single adaptive dialog and just fixing the auto-lock
UX. We rejected it: showing a serial-number field to a user adding a non-serialized
item (or vice versa) is exactly the "wrong fields" problem being fixed, and an
adaptive form can't avoid it without the mode being decided first.

Consequence: a **Serialization Conflict** (Item Type name+sub-type exists with the
other serialization than the chooser mode selected) now blocks the save with a red
label + disabled Add button, instead of silently switching the mode for the user.
This is a deliberate behavior change from the old auto-lock, consistent with the
existing glossary definition of Serialization Conflict ("blocks the save").

Note: this is a third, narrower "add serial" dialog alongside the existing
`AddSerialNumberDialog` (which adds one more unit to an *already-known* serialized
type from the inventory list, not from "Add New Item") — don't conflate the two.
