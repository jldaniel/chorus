import enum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TaskType(str, enum.Enum):
    feature = "feature"
    bug = "bug"
    tech_debt = "tech_debt"


class Status(str, enum.Enum):
    todo = "todo"
    doing = "doing"
    done = "done"
    wont_do = "wont_do"


class LockPurpose(str, enum.Enum):
    sizing = "sizing"
    breakdown = "breakdown"
    refinement = "refinement"
    implementation = "implementation"


class Operation(str, enum.Enum):
    sizing = "sizing"
    breakdown = "breakdown"
    refinement = "refinement"
    implementation = "implementation"
    note = "note"


task_type_enum = Enum(TaskType, name="task_type_enum", native_enum=True, create_constraint=False)
status_enum = Enum(Status, name="status_enum", native_enum=True, create_constraint=False)
lock_purpose_enum = Enum(LockPurpose, name="lock_purpose_enum", native_enum=True, create_constraint=False)
operation_enum = Enum(Operation, name="operation_enum", native_enum=True, create_constraint=False)
