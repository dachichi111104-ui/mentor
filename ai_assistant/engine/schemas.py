from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class TaskSuggestion(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(default="", max_length=1000)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    estimated_hours: float = Field(default=8.0, ge=0.5, le=80.0)
    milestone_id: Optional[int] = None
    labels: List[str] = Field(default_factory=list)
    depends_on: List[int] = Field(default_factory=list)
    rationale: str = Field(default="Đề xuất dựa trên tiến độ và thể loại đồ án.")

class BreakdownOut(BaseModel):
    tasks: List[TaskSuggestion] = Field(default_factory=list, max_length=10)

class RiskItem(BaseModel):
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"
    title: str
    evidence: List[str] = Field(..., min_length=1)
    recommendation: str
    task_id: Optional[int] = None
    milestone_id: Optional[int] = None

class RisksOut(BaseModel):
    summary: str
    risks: List[RiskItem] = Field(default_factory=list)

class WeeklyOut(BaseModel):
    done: List[str] = Field(default_factory=list)
    in_progress: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    next_week: List[str] = Field(default_factory=list)
    highlights: str
    rating: Literal["GOOD", "FAIR", "AT_RISK"] = "FAIR"
    comparison: str

class QuestionItem(BaseModel):
    question: str
    why: str
    related_task_id: Optional[int] = None

class QuestionsOut(BaseModel):
    questions: List[QuestionItem] = Field(default_factory=list)

class ChatOut(BaseModel):
    answer: str
    citations: List[str] = Field(default_factory=list)
    in_scope: bool = True
