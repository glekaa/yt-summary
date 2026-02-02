from enum import Enum as PyEnum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.types import String

from .session import Base


class StatusEnum(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String())
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum), default=StatusEnum.PENDING
    )
    result: Mapped[str | None] = mapped_column(String(), nullable=True)
