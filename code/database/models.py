"""SQLAlchemy ORM model for Run Ledger."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunLedgerModel(Base):
    """PostgreSQL Run Ledger Table."""
    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    sandbox_name = Column(String, nullable=False, unique=True, index=True)
    problem_id = Column(String, nullable=False)
    state = Column(String, nullable=False)
    execution_target = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
