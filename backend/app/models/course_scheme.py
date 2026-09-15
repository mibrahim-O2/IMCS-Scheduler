"""CourseScheme model: one row per Program + admission (scheme) year.

The course list lives in a JSONB `content` column so a new scheme year never
needs a migration; `is_active` soft-deletes schemes referenced by published
timetables. See docs/PROJECT_ARCHITECTURE.md §3.6 and §7.
"""
