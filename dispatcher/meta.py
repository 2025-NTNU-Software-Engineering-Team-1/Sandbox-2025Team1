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
    artifactCollection: list[str] = Field(default_factory=list)

    @validator("executionMode", pre=True)
    def _coerce_execution_mode(cls, v):
        if isinstance(v, str):
            mapping = {
                "general": ExecutionMode.GENERAL,
                "functionOnly": ExecutionMode.FUNCTION_ONLY,
                "interactive": ExecutionMode.INTERACTIVE,
            }
            v = mapping.get(v, v)
        return v

    @validator("buildStrategy", pre=True)
    def _coerce_build_strategy(cls, v):
        if isinstance(v, str):
            mapping = {
                "compile": BuildStrategy.COMPILE,
                "makeNormal": BuildStrategy.MAKE_NORMAL,
                "makeFunctionOnly": BuildStrategy.MAKE_FUNCTION_ONLY,
                "makeInteractive": BuildStrategy.MAKE_INTERACTIVE,
            }
            v = mapping.get(v, v)
        return v

    @validator('tasks')
    def validate_task(cls, v):
        if sum(t.taskScore for t in v) != 100:
            raise ValueError('sum of scores must be 100')
        return v
