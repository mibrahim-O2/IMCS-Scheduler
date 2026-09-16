"""Division (section) and LabBatch models.

A Division is Program + Part + Shift (+ PM/PE group) and is the unit a
timetable is generated for; it exists only for schedulable programs (BS level
today, see §3.1). LabBatch supports one lab running as N parallel sub-batches
with independent teachers and rooms. See docs/PROJECT_ARCHITECTURE.md §3.2.
"""
