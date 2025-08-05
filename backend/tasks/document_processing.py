import logging
from typing import Dict, Any, Optional
from celery import current_task
from celery_app import celery_app
from database.database import get_db
from database.models import Document, BatchUpload, DocumentQuality, AuditLog
from services.ocr_service import OCRService
from services.llm_service import LLMService
from services.quality_service import DocumentQualityService
from services.workflow_service import WorkflowService
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.document_processing.process_document")
def process_document(self, document_id: int, batch_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Process a single document through the complete pipeline
    """
    db = next(get_db())
    
    try:
        # Update task status
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "starting", "document_id": document_id}
        )
        
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Update document status
        document.processing_status = "processing"
        db.commit()
        
        # Log processing start
        audit_log = AuditLog(
            document_id=document_id,
            action="processing_started",
            details={"task_id": self.request.id, "batch_id": batch_id}
        )
        db.add(audit_log)
        db.commit()
        
        # Stage 1: Document Quality Assessment
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "quality_assessment", "document_id": document_id}
        )
        
        quality_service = DocumentQualityService()
        quality_result = quality_service.assess_document_quality(document.file_path)
        
        # Store quality assessment
        quality_assessment = DocumentQuality(
            document_id=document_id,
            **quality_result
        )
        db.add(quality_assessment)
        db.commit()
        
        # Check if document quality is acceptable
        if quality_result["overall_quality_score"] < 0.5:
            document.processing_status = "quality_failed"
            document.requires_review = True
            db.commit()
            
            return {
                "status": "quality_failed",
                "document_id": document_id,
                "quality_score": quality_result["overall_quality_score"],
                "recommendations": quality_result.get("recommendations", [])
            }
        
        # Stage 2: OCR Processing
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "ocr", "document_id": document_id}
        )
        
        ocr_service = OCRService()
        ocr_result = ocr_service.extract_text(document.file_path)
        
        # Update document with OCR results
        document.ocr_text = ocr_result["text"]
        document.ocr_confidence = ocr_result["confidence"]
        document.ocr_engine = ocr_result["engine"]
        document.ocr_timestamp = datetime.utcnow()
        db.commit()
        
        # Stage 3: LLM Field Extraction
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "extraction", "document_id": document_id}
        )
        
        llm_service = LLMService(db)
        extraction_result = llm_service.extract_fields(ocr_result["text"])
        
        # Update document with extraction results
        document.extracted_fields = extraction_result["extracted_fields"]
        document.extraction_confidence = extraction_result["overall_confidence"]
        document.llm_provider = extraction_result["provider"]
        document.llm_model = extraction_result["model"]
        document.extraction_timestamp = datetime.utcnow()
        document.requires_review = extraction_result["requires_review"]
        db.commit()
        
        # Stage 4: Business Rules Validation
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "validation", "document_id": document_id}
        )
        
        workflow_service = WorkflowService(db)
        validation_result = workflow_service.validate_business_rules(document_id)
        
        # Stage 5: Workflow Assignment
        if document.requires_review or validation_result["has_violations"]:
            workflow_service.assign_for_review(
                document_id=document_id,
                priority="high" if validation_result["has_violations"] else "normal"
            )
        
        # Update final status
        document.processing_status = "completed"
        db.commit()
        
        # Update batch progress if applicable
        if batch_id:
            batch = db.query(BatchUpload).filter(BatchUpload.id == batch_id).first()
            if batch:
                batch.processed_documents += 1
                if batch.processed_documents >= batch.total_documents:
                    batch.status = "completed"
                    batch.completed_at = datetime.utcnow()
                db.commit()
        
        # Log completion
        audit_log = AuditLog(
            document_id=document_id,
            action="processing_completed",
            details={
                "task_id": self.request.id,
                "requires_review": document.requires_review,
                "extraction_confidence": document.extraction_confidence,
                "quality_score": quality_result["overall_quality_score"]
            }
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "status": "completed",
            "document_id": document_id,
            "requires_review": document.requires_review,
            "extraction_confidence": document.extraction_confidence,
            "quality_score": quality_result["overall_quality_score"],
            "validation_violations": validation_result.get("violations", [])
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update document status
        if 'document' in locals():
            document.processing_status = "failed"
            db.commit()
        
        # Update batch if applicable
        if batch_id:
            batch = db.query(BatchUpload).filter(BatchUpload.id == batch_id).first()
            if batch:
                batch.failed_documents += 1
                db.commit()
        
        # Log error
        audit_log = AuditLog(
            document_id=document_id,
            action="processing_failed",
            details={
                "task_id": self.request.id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        db.add(audit_log)
        db.commit()
        
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.document_processing.reprocess_document")
def reprocess_document(self, document_id: int, stage: str = "ocr") -> Dict[str, Any]:
    """
    Reprocess a document from a specific stage
    """
    db = next(get_db())
    
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Reset document status based on stage
        if stage == "ocr":
            document.ocr_text = None
            document.ocr_confidence = None
            document.extracted_fields = None
            document.extraction_confidence = None
        elif stage == "extraction":
            document.extracted_fields = None
            document.extraction_confidence = None
        
        document.processing_status = "processing"
        db.commit()
        
        # Call main processing task
        return process_document.apply_async(args=[document_id]).get()
        
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.document_processing.split_document")
def split_document(self, document_id: int) -> Dict[str, Any]:
    """
    Split a multi-document file into individual documents
    """
    db = next(get_db())
    
    try:
        from services.document_splitter import DocumentSplitterService
        
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        splitter_service = DocumentSplitterService()
        split_result = splitter_service.split_document(document.file_path)
        
        created_documents = []
        
        for i, split_doc in enumerate(split_result["documents"]):
            # Create new document record
            new_doc = Document(
                filename=f"{document.filename}_part_{i+1}",
                original_filename=f"{document.original_filename}_part_{i+1}",
                file_path=split_doc["file_path"],
                file_size=split_doc["file_size"],
                mime_type=document.mime_type,
                batch_upload_id=document.batch_upload_id,
                processing_status="pending"
            )
            db.add(new_doc)
            db.flush()
            
            created_documents.append({
                "document_id": new_doc.id,
                "filename": new_doc.filename,
                "confidence": split_doc.get("confidence", 0.0)
            })
            
            # Queue for processing
            process_document.apply_async(
                args=[new_doc.id, document.batch_upload_id],
                countdown=i * 5  # Stagger processing
            )
        
        # Mark original document as split
        document.processing_status = "split"
        db.commit()
        
        return {
            "status": "split_completed",
            "original_document_id": document_id,
            "created_documents": created_documents,
            "total_parts": len(created_documents)
        }
        
    except Exception as e:
        logger.error(f"Error splitting document {document_id}: {str(e)}")
        raise
    
    finally:
        db.close()