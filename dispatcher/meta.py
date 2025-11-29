from .constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from typing import Dict, List, Optional
from pydantic import (
    BaseModel,
    Field,
    validator,
    conlist,
)


class Sidecar(BaseModel):
    image: str
    name: str  # Hostname for the sidecar container ex: "mysql"
    env: Dict[str, str] = Field(default_factory=dict)
    args: List[str] = Field(default_factory=list)


class Task(BaseModel):
    taskScore: int
    memoryLimit: int
    timeLimit: int
    caseCount: int


class Meta(BaseModel):
    language: Language
    tasks: conlist(Task, min_items=1)
    submissionMode: SubmissionMode = SubmissionMode.CODE
    executionMode: ExecutionMode = ExecutionMode.GENERAL
    buildStrategy: BuildStrategy = BuildStrategy.COMPILE
    assetPaths: Dict[str, str] = Field(default_factory=dict)
    teacherFirst: bool = False
    networkAccessRestriction: Optional[dict] = None
    sidecars: List[Sidecar] = Field(default_factory=list)

    @validator("tasks")
    def validate_task(cls, v):
        if sum(t.taskScore for t in v) != 100:
            raise ValueError("sum of scores must be 100")
        return v
