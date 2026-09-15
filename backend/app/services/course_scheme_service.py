"""Parse uploaded PDF/Word course schemes into CourseScheme.content (JSONB).

Also materializes Course rows and checks whether a scheme is referenced by a
published timetable before deletion. See docs/PROJECT_ARCHITECTURE.md §7.
"""
