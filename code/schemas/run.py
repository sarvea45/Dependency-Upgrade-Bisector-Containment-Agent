"""Pydantic v2 schemas for Run Ledger validation."""
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RunCreateSchema(BaseModel):
    run_id: str = Field(..., min_length=1)
    sandbox_name: str
    problem_id: str = Field(..., min_length=1)
    state: str
    execution_target: str

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not re.match(r"^sbx-[a-z0-9]{8,}$", v):
            raise ValueError("sandbox_name must match regex ^sbx-[a-z0-9]{8,}$")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        allowed = {"created", "ready", "running", "succeeded", "failed", "deleted"}
        if v not in allowed:
            raise ValueError(f"state must be one of: {allowed}")
        return v

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError("execution_target must be strictly 'celesto_sandbox'")
        return v


class RunResponseSchema(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str
    created_at: Optional[str] = None
