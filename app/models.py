"""Pydantic validation models for Run Ledger API."""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RunCreate(BaseModel):
    run_id: str = Field(..., min_length=1, description="Unique identifier for the run")
    sandbox_name: str = Field(..., description="Sandbox identifier matching ^sbx-[a-z0-9]{8,}$")
    problem_id: str = Field(..., min_length=1, description="Problem/benchmark task identifier")
    state: str = Field(..., description="Lifecycle state")
    execution_target: str = Field(..., description="Execution environment target")

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not re.match(r"^sbx-[a-z0-9]{8,}$", v):
            raise ValueError("sandbox_name must match regex ^sbx-[a-z0-9]{8,}$")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        allowed_states = {"created", "ready", "running", "succeeded", "failed", "deleted"}
        if v not in allowed_states:
            raise ValueError(f"state must be one of: {', '.join(sorted(allowed_states))}")
        return v

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError("execution_target must be exactly 'celesto_sandbox'")
        return v


class RunResponse(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str
    created_at: Optional[str] = None
