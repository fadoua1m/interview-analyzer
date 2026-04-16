# app/models/enums.py
import enum


class SeniorityLevel(enum.Enum):
    junior = "junior"
    mid    = "mid"
    senior = "senior"
    lead   = "lead"


class InterviewType(enum.Enum):
    behavioral = "behavioral"
    technical  = "technical"
    hr         = "hr"
    mixed      = "mixed"