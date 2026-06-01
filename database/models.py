# database/models.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Influencer(Base):
    __tablename__ = "influencers"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_runs = relationship("AuditRun", back_populates="influencer")

class AuditRun(Base):
    __tablename__ = "audit_runs"
    
    id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False)
    status = Column(String, default="started") # e.g. started, success, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    influencer = relationship("Influencer", back_populates="audit_runs")
    raw_data = relationship("RawScraperData", back_populates="audit_run")
    normalized_metrics = relationship("NormalizedMetrics", back_populates="audit_run", uselist=False)
    report = relationship("Report", back_populates="audit_run", uselist=False)
    benchmark_reports = relationship("BenchmarkReport", back_populates="audit_run")

class RawScraperData(Base):
    __tablename__ = "raw_scraper_data"
    
    id = Column(Integer, primary_key=True)
    audit_run_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=False)
    source = Column(String, nullable=False) # e.g., 'nja', 'toolzu'
    raw_json = Column(JSON, nullable=False)
    
    audit_run = relationship("AuditRun", back_populates="raw_data")

class NormalizedMetrics(Base):
    __tablename__ = "normalized_metrics"
    
    id = Column(Integer, primary_key=True)
    audit_run_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=False)
    followers = Column(Float)
    following = Column(Float)
    posts_count = Column(Float)
    avg_likes = Column(Float)
    avg_comments = Column(Float)
    engagement_rate = Column(Float)
    growth_rate = Column(Float)
    authenticity_score = Column(Float)
    
    audit_run = relationship("AuditRun", back_populates="normalized_metrics")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True)
    audit_run_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=False)
    ai_report = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    audit_run = relationship("AuditRun", back_populates="report")

class BenchmarkReport(Base):
    __tablename__ = "benchmark_reports"
    
    id = Column(Integer, primary_key=True)
    audit_run_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=False)
    employee_username = Column(String, nullable=True)
    model_used = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    raw_report = Column(Text, nullable=False)
    raw_model_response = Column(Text, nullable=True)
    compressed_report = Column(LargeBinary, nullable=False)
    latency = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    
    audit_run = relationship("AuditRun", back_populates="benchmark_reports")


# Setup PostgreSQL Database
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:DWIPAVI@localhost:5432/audit_db")
engine = create_engine(db_url)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
