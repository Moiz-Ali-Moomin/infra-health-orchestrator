import uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class DBValidationRun(Base):
    __tablename__ = 'validation_runs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, nullable=False, index=True)
    correlation_id = Column(String, nullable=False, index=True)
    environment = Column(String, nullable=False)
    
    # Non-Repudiation Identity Tracking
    caller_identity = Column(String, nullable=False, default="anonymous")
    caller_role = Column(String, nullable=False, default="guest")
    caller_ip = Column(String, nullable=True)
    trigger_source = Column(String, nullable=False)
    
    status = Column(String, nullable=False)
    policy_decision = Column(String, nullable=False)
    policy_reason = Column(String, nullable=True)
    total_latency_sec = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    correlation_root_cause = Column(String, nullable=True)
    
    checks = relationship("DBCheckResult", back_populates="run", cascade="all, delete-orphan")

class DBCheckResult(Base):
    __tablename__ = 'check_results'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey('validation_runs.id', ondelete='CASCADE'), nullable=False)
    check_type = Column(String, nullable=False)
    cluster = Column(String, nullable=False)
    status = Column(String, nullable=False)
    latency_sec = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    error_message = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    run = relationship("DBValidationRun", back_populates="checks")
