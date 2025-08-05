from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed, review_required
    
    # OCR Results
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    ocr_engine = Column(String)
    ocr_timestamp = Column(DateTime(timezone=True))
    
    # LLM Extraction Results
    extracted_fields = Column(JSON)
    extraction_confidence = Column(Float)
    llm_provider = Column(String)
    llm_model = Column(String)
    extraction_timestamp = Column(DateTime(timezone=True))
    
    # Review Status
    requires_review = Column(Boolean, default=False)
    review_completed = Column(Boolean, default=False)
    reviewed_by = Column(String)
    review_timestamp = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Relationships
    extractions = relationship("FieldExtraction", back_populates="document")
    audit_logs = relationship("AuditLog", back_populates="document")

class FieldExtraction(Base):
    __tablename__ = "field_extractions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_value = Column(Text)
    confidence_score = Column(Float)
    is_required = Column(Boolean, default=False)
    extraction_method = Column(String)  # llm, manual_review, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="extractions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    action = Column(String, nullable=False)  # upload, ocr_start, ocr_complete, extraction_start, etc.
    details = Column(JSON)
    user_id = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="audit_logs")

class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    task_type = Column(String, nullable=False)  # ocr, extraction
    status = Column(String, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)