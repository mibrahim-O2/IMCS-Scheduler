"""GA operators: selection, crossover (with clash repair), and mutation.

Mutation re-rolls only a gene's (room, day, start_time); the course/teacher
pairing is fixed by the Course Scheme. See docs/PROJECT_ARCHITECTURE.md §6.3.
"""
