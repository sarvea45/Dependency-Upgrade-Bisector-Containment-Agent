"""FastAPI Application for Run Ledger API (:8080)."""
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from code.schemas.run import RunCreateSchema, RunResponseSchema
from code.database.connection import init_db, get_all_runs, insert_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Celesto Run Ledger API",
    description="Trusted Control Plane HTTP API managing AI agent runs inside Celesto sandboxes",
    version="1.0.0",
    lifespan=lifespan
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Override 422 to return 400 Bad Request per evaluation contract."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Bad Request: validation failed for request payload"}
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/runs", response_model=List[Dict[str, Any]])
def list_runs():
    return get_all_runs()


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(run_in: RunCreateSchema):
    if run_in.execution_target != "celesto_sandbox":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="execution_target must be exactly 'celesto_sandbox'"
        )
    return insert_run(run_in.model_dump())
