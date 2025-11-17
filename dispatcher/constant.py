from enum import IntEnum


class Language(IntEnum):
    C = 0
    CPP = 1
    PY = 2


class SubmissionMode(IntEnum):
    CODE = 0
    ZIP = 1


class ExecutionMode(IntEnum):
    GENERAL = 0
    FUNCTION_ONLY = 1
    INTERACTIVE = 2
