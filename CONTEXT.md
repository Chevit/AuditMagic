# AuditMagic

Inventory management for tracked equipment: what exists, how much of it, where it is,
and an audit trail of every change.

## Language

### Things that exist

**ItemType**:
The definition of a kind of equipment — a name, a sub-type, and whether its units are
individually identified. Not a physical thing; a template that physical things belong to.
_Avoid_: category, product, model

**Item**:
A physical record of equipment: either one individually-identified unit, or a count of
interchangeable units of one ItemType at one Location.
_Avoid_: unit, entry, record, inventory item

**Location**:
A place that holds equipment. Every Item belongs to exactly one.
_Avoid_: site, warehouse, place

**Serialized**:
Said of an ItemType whose units are individually identified by serial number, so each unit
is its own Item. Fixed for the lifetime of an ItemType once it has any Items.
_Avoid_: tracked, unique, individual

**Non-serialized**:
Said of an ItemType whose units are interchangeable and counted rather than identified.
_Avoid_: bulk, countable, quantity-based

### Stock

**Stock**:
The equipment of one ItemType present at one Location — a count for a non-serialized
ItemType, a set of serial numbers for a serialized one. Stock is what a user sees in a row
of the inventory list and what they act on; it is not the same as the Item records that
happen to implement it.
_Avoid_: inventory, holding, quantity on hand

**StockRef**:
The pair (ItemType, Location) that identifies Stock. The address every change to Stock is
written to.
_Avoid_: key, item id, target

**Movement**:
A change to Stock: an amount added or removed, expressed as a count for non-serialized
Stock or as serial numbers for serialized Stock.
_Avoid_: adjustment, delta, change

**Transfer**:
A Movement of Stock out of one Location and into another, with no change to the total held.
_Avoid_: move, relocation

### Record-keeping

**Transaction**:
The permanent record of one change to Stock — what changed, by how much, where, when, and
why. Belongs to an ItemType, and survives the deletion of the Items it described.
_Avoid_: log entry, event, history record, audit entry
