"""Fitness function: aggregates penalties from scheduler/constraints/.

fitness = -(sum(hard_violations) * HARD_WEIGHT + sum(soft_violations) * SOFT_WEIGHT).
Individual constraints live in constraints/hard.py and constraints/soft.py,
never inline here. See docs/PROJECT_ARCHITECTURE.md §6.2.
"""
