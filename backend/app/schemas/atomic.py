from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.base import TaskType


class DimensionScore(BaseModel):
    score: int
    reasoning: str

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v < 0 or v > 2:
            raise ValueError("Dimension score must be 0-2")
        return v


class CommitCreate(BaseModel):
    commit_hash: str
    message: str | None = None
    author: str | None = None
    committed_at: datetime


class SizingRequest(BaseModel):
    scope_clarity: DimensionScore
    decision_points: DimensionScore
    context_window_demand: DimensionScore
    verification_complexity: DimensionScore
    domain_specificity: DimensionScore
    confidence: int
    risk_factors: list[str] | None = None
    breakdown_suggestions: str | None = None
    scored_by: str | None = None
    work_log_content: str
    author: str | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: int) -> int:
        if v < 0 or v > 5:
            raise ValueError("Confidence must be 0-5")
        return v


class BreakdownSubtask(BaseModel):
    name: str
    description: str | None = None
    context: str | None = None
    task_type: TaskType
    position: int | None = None


class BreakdownRequest(BaseModel):
    subtasks: list[BreakdownSubtask]
    parent_description_update: str | None = None
    work_log_content: str
    author: str | None = None

    @field_validator("subtasks")
    @classmethod
    def validate_subtasks(cls, v: list[BreakdownSubtask]) -> list[BreakdownSubtask]:
        if len(v) < 1:
            raise ValueError("At least one subtask is required")
        return v


class RefineRequest(BaseModel):
    description: str | None = None
    context: str | None = None
    context_captured_at: datetime | None = None
    work_log_content: str
    author: str | None = None


class FlagRefinementRequest(BaseModel):
    refinement_notes: str


class CompleteRequest(BaseModel):
    work_log_content: str
    author: str | None = None
    commits: list[CommitCreate] | None = None
