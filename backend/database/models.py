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
    
    # Batch processing
    batch_upload_id = Column(Integer, ForeignKey("batch_uploads.id"))
    
    # Relationships
    extractions = relationship("FieldExtraction", back_populates="document")
    audit_logs = relationship("AuditLog", back_populates="document")
    human_feedback = relationship("HumanFeedback", back_populates="document")
    batch_upload = relationship("BatchUpload", back_populates="documents")
    quality_assessment = relationship("DocumentQuality", back_populates="document", uselist=False)
    rule_violations = relationship("BusinessRuleViolation", back_populates="document")
    workflow_assignments = relationship("WorkflowAssignment", back_populates="document")

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

class FieldDefinition(Base):
    __tablename__ = "field_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    field_type = Column(String, default="text")  # text, date, number, email, phone
    is_required = Column(Boolean, default=False)
    validation_pattern = Column(String)  # regex pattern for validation
    extraction_hints = Column(JSON)  # hints for LLM extraction
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class HumanFeedback(Base):
    __tablename__ = "human_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(Text)  # What the model extracted
    corrected_value = Column(Text)  # What the human corrected it to
    original_confidence = Column(Float)
    feedback_type = Column(String, nullable=False)  # correction, addition, removal, confirmation
    reviewer_id = Column(String)
    review_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # RL Training data
    reward_score = Column(Float)  # Calculated reward/penalty
    model_version = Column(String)  # Track which model version made the prediction
    ocr_context = Column(Text)  # OCR text context around the field
    
    # Relationships
    document = relationship("Document", back_populates="human_feedback")

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)  # Model found field, human said no
    false_negatives = Column(Integer, default=0)  # Model missed field, human found it
    avg_confidence = Column(Float, default=0.0)
    avg_reward = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Performance metrics
    precision = Column(Float, default=0.0)  # correct / (correct + false_positive)
    recall = Column(Float, default=0.0)     # correct / (correct + false_negative)
    f1_score = Column(Float, default=0.0)   # 2 * (precision * recall) / (precision + recall)

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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="reviewer")  # admin, supervisor, reviewer, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    reviewed_documents = relationship("Document", foreign_keys="Document.reviewed_by")
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.user_id")

class BatchUpload(Base):
    __tablename__ = "batch_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String, nullable=False)
    uploaded_by = Column(String, ForeignKey("users.username"), nullable=False)
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    documents = relationship("Document", back_populates="batch_upload")
    uploader = relationship("User", foreign_keys=[uploaded_by])

class DocumentQuality(Base):
    __tablename__ = "document_quality"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    image_dpi = Column(Integer)
    image_clarity_score = Column(Float)
    text_density_score = Column(Float)
    overall_quality_score = Column(Float)
    quality_issues = Column(JSON)  # List of detected issues
    recommendations = Column(JSON)  # Improvement recommendations
    assessed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="quality_assessment")

class BusinessRule(Base):
    __tablename__ = "business_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    rule_type = Column(String, nullable=False)  # field_validation, cross_field, business_logic
    rule_definition = Column(JSON, nullable=False)  # Rule configuration
    is_active = Column(Boolean, default=True)
    severity = Column(String, default="warning")  # error, warning, info
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BusinessRuleViolation(Base):
    __tablename__ = "business_rule_violations"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("business_rules.id"), nullable=False)
    violation_details = Column(JSON)
    severity = Column(String, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String, ForeignKey("users.username"))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="rule_violations")
    rule = relationship("BusinessRule")
    resolver = relationship("User", foreign_keys=[resolved_by])

class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String, nullable=False)  # counter, gauge, histogram
    labels = Column(JSON)  # Additional metric labels
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowAssignment(Base):
    __tablename__ = "workflow_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    assigned_to = Column(String, ForeignKey("users.username"), nullable=False)
    assignment_type = Column(String, nullable=False)  # review, quality_check, approval
    priority = Column(String, default="normal")  # urgent, high, normal, low
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    status = Column(String, default="assigned")  # assigned, in_progress, completed, reassigned
    
    # Relationships
    document = relationship("Document", back_populates="workflow_assignments")
    assignee = relationship("User", foreign_keys=[assigned_to])