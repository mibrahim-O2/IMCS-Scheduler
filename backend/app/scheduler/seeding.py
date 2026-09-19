"""Constructive seeding: build starting timetables that already dodge the obvious
clashes, instead of scattering every session at random.

A pure-random start (chromosome.random_chromosome) begins with dozens of violations
and leaves the whole search to repair them. On the full BSCS Part-I to Part-IV problem
that stalls one or two violations short of zero — several teachers have exactly as many
sessions as their available days can hold (6 sessions on 2 days, at 3 per day), so the
last few fixes need a very specific arrangement that random repair rarely stumbles onto.

This builder places sessions one at a time, most-constrained first, and only takes a
slot that doesn't break a rule against what is already placed. It is greedy, so it is
NOT guaranteed to reach zero violations (a session can run out of clean slots, and then
it falls back to a random placement) — it only has to start the population much closer
to a good answer. The engine mixes these with random individuals to keep diversity.
"""

from __future__ import annotations

import random
from collections import defaultdict

from app.scheduler.chromosome import (
    DAYS,
    TIME_SLOTS,
    Chromosome,
    Gene,
    SessionRequirement,
    random_gene,
)
from app.scheduler.constraints.hard import MAX_SAME_SUBJECT_PER_DAY, MAX_TEACHER_SESSIONS_PER_DAY


def constructive_chromosome(
    rng: random.Random,
    requirements: list[SessionRequirement],
    teacher_availability: dict[int, set[str]],
) -> Chromosome:
    # Places every session greedily onto a slot that clashes with nothing placed so far,
    # falling back to a random placement only for a session that has no clean slot left.
    placed: dict[int, Gene] = {}

    teacher_busy: set[tuple[int, str, int]] = set()
    room_busy: set[tuple[int, str, int]] = set()
    division_busy: set[tuple[int, str, int]] = set()
    teacher_day_load: dict[tuple[int, str], int] = defaultdict(int)
    subject_day_count: dict[tuple[int, int, str], int] = defaultdict(int)

    # Sessions whose teacher has the fewest available days go first — they have the least
    # room to move, so they must claim their slots before easier sessions crowd them out.
    # The random key breaks ties differently for each individual, which is what keeps
    # the constructive individuals from all being the same timetable.
    order = sorted(
        range(len(requirements)),
        key=lambda i: (len(teacher_availability.get(requirements[i].teacher_id, ())), rng.random()),
    )

    for index in order:
        requirement = requirements[index]
        available_days = teacher_availability.get(requirement.teacher_id, set())

        # Every (day, slot, room) this session could go in, in a fresh random order so the
        # first clean one found is a random choice among the clean ones, not always Monday.
        candidates = [
            (day, slot_index, room_id)
            for day in DAYS
            if day in available_days
            for slot_index in range(len(TIME_SLOTS))
            for room_id in requirement.candidate_rooms
        ]
        rng.shuffle(candidates)

        chosen = None
        for day, slot_index, room_id in candidates:
            if (requirement.teacher_id, day, slot_index) in teacher_busy:
                continue
            if (room_id, day, slot_index) in room_busy:
                continue
            if any((d, day, slot_index) in division_busy for d in requirement.division_ids):
                continue
            if teacher_day_load[(requirement.teacher_id, day)] >= MAX_TEACHER_SESSIONS_PER_DAY:
                continue
            if not requirement.is_lab and any(
                subject_day_count[(d, requirement.course_id, day)] >= MAX_SAME_SUBJECT_PER_DAY
                for d in requirement.division_ids
            ):
                continue
            chosen = Gene(room_id, day, slot_index)
            break

        if chosen is None:
            # Nothing clean is left for this one — take a random placement and let the
            # evolutionary search repair it, rather than hiding the clash.
            chosen = random_gene(rng, requirement)

        placed[index] = chosen
        teacher_busy.add((requirement.teacher_id, chosen.day, chosen.slot_index))
        room_busy.add((chosen.room_id, chosen.day, chosen.slot_index))
        teacher_day_load[(requirement.teacher_id, chosen.day)] += 1
        for division_id in requirement.division_ids:
            division_busy.add((division_id, chosen.day, chosen.slot_index))
            if not requirement.is_lab:
                subject_day_count[(division_id, requirement.course_id, chosen.day)] += 1

    return [placed[index] for index in range(len(requirements))]
