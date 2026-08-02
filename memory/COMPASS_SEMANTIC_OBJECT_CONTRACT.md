# COMPASS_SEMANTIC_OBJECT_CONTRACT.md

This document defines the permanent architectural contract governing semantic
objects throughout Compass.

--------------------------------------------------
## COMPASS SEMANTIC OBJECT CONTRACT
--------------------------------------------------

The Meaning Workspace owns the canonical semantic objects in Compass.

A Meaning Object represents the learner's meaning.

Every later workspace presents, organizes, annotates, or realizes those meanings.

No later workspace owns or duplicates the semantic objects themselves.

--------------------------------------------------
## SEMANTIC OBJECT INVARIANTS
--------------------------------------------------

Each Meaning Object has immutable identity.

The following properties are immutable for the lifetime of the object:
- object_id
- creation timestamp
- creator (reserved for future multi-user support)
- lineage (reserved for future versions)

The following properties may change:
- text
- notes
- color
- position
- relationships
- group membership

--------------------------------------------------
## ONE SEMANTIC OBJECT, MANY REPRESENTATIONS
--------------------------------------------------

Future Compass workspaces must never duplicate Meaning Objects.

Instead, every workspace references the Meaning Object by immutable object_id and
stores only workspace-specific metadata.

Meaning remains canonical.
Representations may differ.

--------------------------------------------------
## OVERLAY PRINCIPLE
--------------------------------------------------

Future workspaces own only their own overlay information.

Examples:

Writing Plan overlay:
- meaning_object_id
- paragraph assignment
- paragraph role
- ordering

Draft overlay:
- meaning_object_id
- sentence references
- realization status

Revision overlay:
- meaning_object_id
- revision history
- revision comments

Teacher overlay:
- meaning_object_id
- annotations
- assessment notes
- instructional observations

Analytics overlay:
- meaning_object_id
- process metrics
- learning analytics

None of these workspaces owns the semantic object.

--------------------------------------------------
## REFERENTIAL INTEGRITY
--------------------------------------------------

Future versions must preserve referential integrity.

Deleting a Meaning Object must never silently orphan overlays.

Future implementations may either:
- prevent deletion while references exist, or
- archive the object rather than permanently deleting it.

Do not implement this behavior now.
Document the architectural requirement only.

--------------------------------------------------
## ARCHITECTURAL PRINCIPLE
--------------------------------------------------

Compass is organized around meaning rather than documents.

Meaning Objects are the canonical intellectual entities of the system.

Writing Plans, Drafts, Revisions, Teacher tools, and Analytics are different
representations of the same underlying organization of meaning.

This principle is foundational and should guide all future development.

--------------------------------------------------
## IMPLEMENTATION STATUS (as of Meaning Workspace V1, 2026-06)
--------------------------------------------------

Implemented now:
- object_id / group_id / connection_id are globally unique (`crypto.randomUUID()`
  with readable `obj_`/`grp_`/`edge_` prefixes) and immutable for the object's
  lifetime (assigned once, never regenerated or migrated; legacy ids preserved).
- Relationships stored by reference: `connection.from_id`/`to_id` → object ids;
  `object.group_id` → group id; `event.data.id` → the entity acted on.
- Canonical store = `meaning_maps` (objects/groups/connections/events) keyed by
  `session_id`.

Reserved / documented-only (NOT implemented yet — do not build until scheduled):
- `creation timestamp`, `creator`, and `lineage` fields on each Meaning Object.
- Overlay stores for Writing Plan / Draft / Revision / Teacher / Analytics.
- Referential-integrity enforcement (prevent-delete-while-referenced OR archive).

_Last updated: 2026-06._
