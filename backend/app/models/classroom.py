"""Classroom model: lecture rooms, labs, halls and multimedia rooms.

See docs/PROJECT_ARCHITECTURE.md §3.3.
"""

import enum
from typing import Any

from sqlalchemy import Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ClassroomType(str, enum.Enum):
    LECTURE = "lecture"
    LAB = "lab"
    HALL = "hall"
    MULTIMEDIA = "multimedia"


class Classroom(TimestampMixin, Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[ClassroomType] = mapped_column(
        Enum(ClassroomType, name="classroom_type", values_callable=lambda types: [x.value for x in types]),
        nullable=False,
    )
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-form room features (projector, AC, ...) kept flexible on purpose.
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
