from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db, init_db, Document, FieldExtraction, AuditLog
from services import OCRService, LLMService

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
llm_service = LLMService()

# Create upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Database initialized")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Document Extraction Pipeline API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
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
        for field_name, field_value in extraction_result['extracted_fields'].items():
            field_extraction = FieldExtraction(
                document_id=document_id,
                field_name=field_name,
                field_value=str(field_value),
                confidence_score=extraction_result['confidence_scores'].get(field_name, 0.0),
                is_required=field_name in llm_service.required_fields,
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
                "model": extraction_result['model']
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
async def get_llm_providers():
    """
    Get available LLM providers and models
    """
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)