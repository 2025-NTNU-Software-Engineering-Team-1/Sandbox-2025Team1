from .constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from typing import Dict, List, Optional
from pydantic import (
    BaseModel,
    Field,
    validator,
    conlist,
)


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
    customChecker: bool = False
    checkerAsset: Optional[str] = None
    scoringScript: bool = False
    scorerAsset: Optional[str] = None

    @validator('tasks')
    def validate_task(cls, v):
        if sum(t.taskScore for t in v) != 100:
            raise ValueError('sum of scores must be 100')
        return v
