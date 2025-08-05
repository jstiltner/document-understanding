from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from database import get_db, init_db, Document, FieldExtraction, AuditLog, FieldDefinition, HumanFeedback, ModelPerformance
from services import OCRService, LLMService, FieldDefinitionService, ReinforcementLearningService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document Extraction Pipeline API",
    description="End-to-end document extraction pipeline for insurance authorization/denial PDFs",
    version="1.0.0"
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ocr_service = OCRService()

# Create upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    init_db()
    logger.info("Database initialized")
    
    # Initialize field definitions with default values
    db = next(get_db())
    try:
        field_service = FieldDefinitionService(db)
        field_service.initialize_default_fields()
        logger.info("Field definitions initialized")
    except Exception as e:
        logger.error(f"Failed to initialize field definitions: {e}")
    finally:
        db.close()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Document Extraction Pipeline API", "version": "1.0.0"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    llm_service = LLMService(db)
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "ocr": ocr_service.ocr_engine,
            "llm_providers": llm_service.get_available_providers()
        }
    }

@app.post("/upload", response_model=dict)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for processing
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Check file size
        max_size = int(os.getenv("MAX_FILE_SIZE", "50000000"))  # 50MB default
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail=f"File size exceeds {max_size} bytes")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create database record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=file.content_type or "application/pdf",
            processing_status="pending"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Log upload
        audit_log = AuditLog(
            document_id=document.id,
            action="upload",
            details={"original_filename": file.filename, "file_size": len(file_content)}
        )
        db.add(audit_log)
        db.commit()
        
        # Start background processing
        background_tasks.add_task(process_document, document.id)
        
        return {
            "document_id": document.id,
            "filename": file.filename,
            "status": "uploaded",
            "message": "Document uploaded successfully and processing started"
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_document(document_id: int):
    """
    Background task to process document through OCR and LLM extraction
    """
    db = next(get_db())
    
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Initialize services with database connection
        llm_service = LLMService(db)
        field_service = FieldDefinitionService(db)
        
        # Update status
        document.processing_status = "processing"
        db.commit()
        
        # Log processing start
        audit_log = AuditLog(
            document_id=document_id,
            action="processing_start",
            details={}
        )
        db.add(audit_log)
        db.commit()
        
        # Step 1: OCR Processing
        logger.info(f"Starting OCR for document {document_id}")
        ocr_result = ocr_service.extract_text_from_pdf(document.file_path)
        
        # Update document with OCR results
        document.ocr_text = ocr_result['text']
        document.ocr_confidence = ocr_result['confidence']
        document.ocr_engine = ocr_result['engine']
        document.ocr_timestamp = datetime.utcnow()
        db.commit()
        
        # Log OCR completion
        audit_log = AuditLog(
            document_id=document_id,
            action="ocr_complete",
            details={
                "confidence": ocr_result['confidence'],
                "engine": ocr_result['engine'],
                "page_count": ocr_result.get('page_count', 0)
            }
        )
        db.add(audit_log)
        db.commit()
        
        # Step 2: Preprocess text
        preprocessed_text = ocr_service.preprocess_text(ocr_result['text'])
        
        # Step 3: LLM Field Extraction
        logger.info(f"Starting field extraction for document {document_id}")
        extraction_result = llm_service.extract_fields(preprocessed_text)
        
        # Update document with extraction results
        document.extracted_fields = extraction_result['extracted_fields']
        document.extraction_confidence = extraction_result['overall_confidence']
        document.llm_provider = extraction_result['provider']
        document.llm_model = extraction_result['model']
        document.extraction_timestamp = datetime.utcnow()
        document.requires_review = extraction_result['requires_review']
        
        # Set final status
        if extraction_result['requires_review']:
            document.processing_status = "review_required"
        else:
            document.processing_status = "completed"
        
        db.commit()
        
        # Store individual field extractions
        required_fields = field_service.get_required_fields()
        required_field_names = [f.name for f in required_fields]
        
        for field_name, field_value in extraction_result['extracted_fields'].items():
            field_extraction = FieldExtraction(
                document_id=document_id,
                field_name=field_name,
                field_value=str(field_value),
                confidence_score=extraction_result['confidence_scores'].get(field_name, 0.0),
                is_required=field_name in required_field_names,
                extraction_method="llm"
            )
            db.add(field_extraction)
        
        db.commit()
        
        # Log extraction completion
        audit_log = AuditLog(
            document_id=document_id,
            action="extraction_complete",
            details={
                "overall_confidence": extraction_result['overall_confidence'],
                "requires_review": extraction_result['requires_review'],
                "fields_extracted": len(extraction_result['extracted_fields']),
                "provider": extraction_result['provider'],
                "model": extraction_result['model'],
                "model_version": extraction_result.get('model_version')
            }
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Document {document_id} processing completed")
        
    except Exception as e:
        logger.error(f"Processing error for document {document_id}: {str(e)}")
        
        # Update document status to failed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = "failed"
            db.commit()
            
            # Log error
            audit_log = AuditLog(
                document_id=document_id,
                action="processing_error",
                details={"error": str(e)}
            )
            db.add(audit_log)
            db.commit()
    
    finally:
        db.close()

@app.get("/documents", response_model=List[dict])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List documents with optional filtering
    """
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.processing_status == status)
    
    documents = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.original_filename,
            "upload_timestamp": doc.upload_timestamp.isoformat(),
            "processing_status": doc.processing_status,
            "ocr_confidence": doc.ocr_confidence,
            "extraction_confidence": doc.extraction_confidence,
            "requires_review": doc.requires_review,
            "review_completed": doc.review_completed
        }
        for doc in documents
    ]

@app.get("/documents/{document_id}", response_model=dict)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get detailed document information
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get field extractions
    extractions = db.query(FieldExtraction).filter(
        FieldExtraction.document_id == document_id
    ).all()
    
    return {
        "id": document.id,
        "filename": document.original_filename,
        "upload_timestamp": document.upload_timestamp.isoformat(),
        "processing_status": document.processing_status,
        "ocr_confidence": document.ocr_confidence,
        "extraction_confidence": document.extraction_confidence,
        "requires_review": document.requires_review,
        "review_completed": document.review_completed,
        "extracted_fields": document.extracted_fields,
        "field_extractions": [
            {
                "field_name": ext.field_name,
                "field_value": ext.field_value,
                "confidence_score": ext.confidence_score,
                "is_required": ext.is_required
            }
            for ext in extractions
        ]
    }

@app.get("/documents/{document_id}/review")
async def get_document_for_review(document_id: int, db: Session = Depends(get_db)):
    """
    Get document data formatted for review interface
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.requires_review:
        raise HTTPException(status_code=400, detail="Document does not require review")
    
    # Get field extractions
    extractions = db.query(FieldExtraction).filter(
        FieldExtraction.document_id == document_id
    ).all()
    
    # Organize fields by required/optional
    required_fields = {}
    optional_fields = {}
    
    for ext in extractions:
        field_data = {
            "value": ext.field_value,
            "confidence": ext.confidence_score
        }
        
        if ext.is_required:
            required_fields[ext.field_name] = field_data
        else:
            optional_fields[ext.field_name] = field_data
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "ocr_text": document.ocr_text,
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "overall_confidence": document.extraction_confidence
    }

@app.get("/config/llm-providers")
async def get_llm_providers(db: Session = Depends(get_db)):
    """
    Get available LLM providers and models
    """
    llm_service = LLMService(db)
    providers = {}
    
    for provider in llm_service.get_available_providers():
        providers[provider] = {
            "models": llm_service.get_available_models(provider),
            "default_model": llm_service.default_model if provider == llm_service.default_provider else None
        }
    
    return {
        "providers": providers,
        "default_provider": llm_service.default_provider
    }

# Field Definition Management Endpoints

@app.get("/fields", response_model=List[dict])
async def get_field_definitions(db: Session = Depends(get_db)):
    """Get all active field definitions"""
    field_service = FieldDefinitionService(db)
    fields = field_service.get_active_fields()
    
    return [
        {
            "id": field.id,
            "name": field.name,
            "display_name": field.display_name,
            "description": field.description,
            "field_type": field.field_type,
            "is_required": field.is_required,
            "validation_pattern": field.validation_pattern,
            "extraction_hints": field.extraction_hints,
            "is_active": field.is_active
        }
        for field in fields
    ]

@app.post("/fields", response_model=dict)
async def create_field_definition(field_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new field definition"""
    field_service = FieldDefinitionService(db)
    
    try:
        field_def = field_service.create_field_definition(field_data)
        return {
            "id": field_def.id,
            "name": field_def.name,
            "display_name": field_def.display_name,
            "message": "Field definition created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/fields/{field_id}", response_model=dict)
async def update_field_definition(
    field_id: int,
    field_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update an existing field definition"""
    field_service = FieldDefinitionService(db)
    
    field_def = field_service.update_field_definition(field_id, field_data)
    if not field_def:
        raise HTTPException(status_code=404, detail="Field definition not found")
    
    return {
        "id": field_def.id,
        "name": field_def.name,
        "display_name": field_def.display_name,
        "message": "Field definition updated successfully"
    }

@app.delete("/fields/{field_id}")
async def delete_field_definition(field_id: int, db: Session = Depends(get_db)):
    """Delete (deactivate) a field definition"""
    field_service = FieldDefinitionService(db)
    
    success = field_service.delete_field_definition(field_id)
    if not success:
        raise HTTPException(status_code=404, detail="Field definition not found")
    
    return {"message": "Field definition deactivated successfully"}

# Human Feedback and RL Endpoints

@app.post("/documents/{document_id}/feedback")
async def submit_human_feedback(
    document_id: int,
    feedback_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Submit human feedback for RL training"""
    rl_service = ReinforcementLearningService(db)
    
    try:
        # Extract feedback data
        field_name = feedback_data.get("field_name")
        original_value = feedback_data.get("original_value")
        corrected_value = feedback_data.get("corrected_value")
        original_confidence = feedback_data.get("original_confidence", 0.0)
        feedback_type = feedback_data.get("feedback_type")  # correction, addition, removal, confirmation
        reviewer_id = feedback_data.get("reviewer_id", "anonymous")
        model_version = feedback_data.get("model_version", "unknown")
        ocr_context = feedback_data.get("ocr_context")
        
        if not field_name or not feedback_type:
            raise HTTPException(status_code=400, detail="field_name and feedback_type are required")
        
        feedback = rl_service.record_human_feedback(
            document_id=document_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            original_confidence=original_confidence,
            feedback_type=feedback_type,
            reviewer_id=reviewer_id,
            model_version=model_version,
            ocr_context=ocr_context
        )
        
        return {
            "feedback_id": feedback.id,
            "reward_score": feedback.reward_score,
            "message": "Feedback recorded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/documents/{document_id}/review/complete")
async def complete_document_review(
    document_id: int,
    review_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Complete document review and record all feedback"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    rl_service = ReinforcementLearningService(db)
    reviewer_id = review_data.get("reviewer_id", "anonymous")
    corrected_fields = review_data.get("corrected_fields", {})
    model_version = document.llm_model or "unknown"
    
    feedback_count = 0
    
    try:
        # Process each field correction
        for field_name, correction_data in corrected_fields.items():
            original_value = correction_data.get("original_value")
            corrected_value = correction_data.get("corrected_value")
            original_confidence = correction_data.get("original_confidence", 0.0)
            
            # Determine feedback type
            if original_value and corrected_value:
                if original_value.strip() == corrected_value.strip():
                    feedback_type = "confirmation"
                else:
                    feedback_type = "correction"
            elif not original_value and corrected_value:
                feedback_type = "addition"
            elif original_value and not corrected_value:
                feedback_type = "removal"
            else:
                continue  # Skip if both are empty
            
            rl_service.record_human_feedback(
                document_id=document_id,
                field_name=field_name,
                original_value=original_value,
                corrected_value=corrected_value,
                original_confidence=original_confidence,
                feedback_type=feedback_type,
                reviewer_id=reviewer_id,
                model_version=model_version,
                ocr_context=document.ocr_text
            )
            feedback_count += 1
        
        # Update document review status
        document.review_completed = True
        document.reviewed_by = reviewer_id
        document.review_timestamp = datetime.utcnow()
        document.review_notes = review_data.get("notes", "")
        document.processing_status = "completed"
        
        # Update extracted fields with corrected values
        for field_name, correction_data in corrected_fields.items():
            corrected_value = correction_data.get("corrected_value")
            if corrected_value:
                document.extracted_fields[field_name] = corrected_value
        
        db.commit()
        
        return {
            "message": "Review completed successfully",
            "feedback_records": feedback_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/analytics/model-performance")
async def get_model_performance(
    model_version: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get model performance analytics"""
    rl_service = ReinforcementLearningService(db)
    
    performance_data = rl_service.get_model_performance(model_version)
    summary = rl_service.get_performance_summary()
    
    return {
        "performance_by_field": [
            {
                "model_version": perf.model_version,
                "field_name": perf.field_name,
                "total_predictions": perf.total_predictions,
                "correct_predictions": perf.correct_predictions,
                "false_positives": perf.false_positives,
                "false_negatives": perf.false_negatives,
                "precision": perf.precision,
                "recall": perf.recall,
                "f1_score": perf.f1_score,
                "avg_reward": perf.avg_reward
            }
            for perf in performance_data
        ],
        "summary": summary
    }

@app.get("/analytics/feedback-data")
async def get_feedback_data(
    model_version: Optional[str] = None,
    field_name: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get human feedback data for analysis"""
    rl_service = ReinforcementLearningService(db)
    
    feedback_data = rl_service.get_feedback_for_training(model_version, field_name, limit)
    
    return [
        {
            "id": feedback.id,
            "document_id": feedback.document_id,
            "field_name": feedback.field_name,
            "original_value": feedback.original_value,
            "corrected_value": feedback.corrected_value,
            "original_confidence": feedback.original_confidence,
            "feedback_type": feedback.feedback_type,
            "reward_score": feedback.reward_score,
            "model_version": feedback.model_version,
            "review_timestamp": feedback.review_timestamp.isoformat()
        }
        for feedback in feedback_data
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)