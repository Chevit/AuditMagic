# AuditMagic

Inventory tracking for physical equipment held across locations. Some equipment is
tracked unit by unit (each with its own serial number), the rest by count. Every change
is recorded so the stock can be audited after the fact.

## Language

**Item Type**:
A category of equipment that items are instances of, identified by a name and an optional
sub-type. Decides, once and for all, whether its items are serialized.
_Avoid_: category, template, product, SKU

**Item**:
A physical unit or a counted batch of one Item Type at one Location.
_Avoid_: entry, record, stock, asset

**Serialized Type**:
An Item Type whose items are tracked individually, one item per serial number, quantity
always one. Its opposite is a non-serialized type, whose items are tracked by count and
carry no serial number. A type's serialization is fixed from the moment it has any items.
_Avoid_: unique, tracked, individual

**Grouped Item**:
Every Item of one Item Type at one Location, presented as a single row. What the user
sees in the list; not something that exists in the database.
_Avoid_: aggregate, roll-up, summary, bundle

**Target Item**:
The one Item an operation acts on when the user acted on a Grouped Item. For a
non-serialized type it is the type's single counted item; for a Serialized Type it is the
specific unit named by a serial number.
_Avoid_: selected item, current item, resolved item

**Serialization Conflict**:
The state reached when a user names an Item Type that already exists and whose
serialization disagrees with what they asked for. Blocks the save.
_Avoid_: mismatch, type clash, validation error

**Edit Reason**:
The explanation a user must give when changing an Item, recorded on the resulting
transaction. Distinct from an Item Type's details, which describe the type itself.
_Avoid_: note, comment, description
