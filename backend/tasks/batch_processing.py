import logging
from typing import Dict, Any, List
from celery import current_task, group
from celery_app import celery_app
from database.database import get_db
from database.models import BatchUpload, Document
from tasks.document_processing import process_document, split_document
from datetime import datetime
import os
import traceback

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.batch_processing.process_batch")
def process_batch(self, batch_id: int) -> Dict[str, Any]:
    """
    Process all documents in a batch upload
    """
    db = next(get_db())
    
    try:
        # Update task status
        current_task.update_state(
            state="PROCESSING",
            meta={"stage": "starting", "batch_id": batch_id}
        )
        
        # Get batch
        batch = db.query(BatchUpload).filter(BatchUpload.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Update batch status
        batch.status = "processing"
        db.commit()
        
        # Get all documents in batch
        documents = db.query(Document).filter(Document.batch_upload_id == batch_id).all()
        
        if not documents:
            batch.status = "completed"
            batch.completed_at = datetime.utcnow()
            db.commit()
            return {
                "status": "completed",
                "batch_id": batch_id,
                "message": "No documents to process"
            }
        
        # Update batch total count
        batch.total_documents = len(documents)
        db.commit()
        
        # Create processing tasks for each document
        processing_tasks = []
        
        for i, document in enumerate(documents):
            # Check if document needs splitting first
            if should_split_document(document.file_path):
                # Queue splitting task first
                split_task = split_document.apply_async(
                    args=[document.id],
                    countdown=i * 2  # Stagger tasks
                )
                processing_tasks.append(split_task)
            else:
                # Queue regular processing
                process_task = process_document.apply_async(
                    args=[document.id, batch_id],
                    countdown=i * 2  # Stagger tasks
                )
                processing_tasks.append(process_task)
        
        # Update task status
        current_task.update_state(
            state="PROCESSING",
            meta={
                "stage": "documents_queued",
                "batch_id": batch_id,
                "total_documents": len(documents),
                "queued_tasks": len(processing_tasks)
            }
        )
        
        # Wait for all tasks to complete (with timeout)
        results = []
        completed_count = 0
        failed_count = 0
        
        for task in processing_tasks:
            try:
                result = task.get(timeout=1800)  # 30 minutes timeout per document
                results.append(result)
                if result.get("status") == "completed":
                    completed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Task failed: {str(e)}")
                failed_count += 1
                results.append({"status": "failed", "error": str(e)})
        
        # Update final batch status
        batch = db.query(BatchUpload).filter(BatchUpload.id == batch_id).first()
        if failed_count == 0:
            batch.status = "completed"
        elif completed_count > 0:
            batch.status = "partially_completed"
        else:
            batch.status = "failed"
        
        batch.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": batch.status,
            "batch_id": batch_id,
            "total_documents": len(documents),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update batch status
        if 'batch' in locals():
            batch.status = "failed"
            batch.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.batch_processing.create_batch_from_upload")
def create_batch_from_upload(self, file_paths: List[str], batch_name: str, uploaded_by: str) -> Dict[str, Any]:
    """
    Create a batch upload from a list of file paths
    """
    db = next(get_db())
    
    try:
        # Create batch record
        batch = BatchUpload(
            batch_name=batch_name,
            uploaded_by=uploaded_by,
            status="pending"
        )
        db.add(batch)
        db.flush()
        
        # Create document records
        created_documents = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Determine MIME type
            mime_type = "application/pdf"  # Default for now
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                mime_type = f"image/{filename.split('.')[-1].lower()}"
            
            document = Document(
                filename=filename,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                batch_upload_id=batch.id,
                processing_status="pending"
            )
            db.add(document)
            db.flush()
            
            created_documents.append({
                "document_id": document.id,
                "filename": filename,
                "file_size": file_size
            })
        
        batch.total_documents = len(created_documents)
        db.commit()
        
        # Queue batch processing
        if created_documents:
            process_batch.apply_async(args=[batch.id], countdown=5)
        
        return {
            "status": "created",
            "batch_id": batch.id,
            "batch_name": batch_name,
            "total_documents": len(created_documents),
            "documents": created_documents
        }
        
    except Exception as e:
        logger.error(f"Error creating batch: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.batch_processing.retry_failed_documents")
def retry_failed_documents(self, batch_id: int) -> Dict[str, Any]:
    """
    Retry processing failed documents in a batch
    """
    db = next(get_db())
    
    try:
        # Get failed documents
        failed_documents = db.query(Document).filter(
            Document.batch_upload_id == batch_id,
            Document.processing_status == "failed"
        ).all()
        
        if not failed_documents:
            return {
                "status": "no_failed_documents",
                "batch_id": batch_id,
                "message": "No failed documents to retry"
            }
        
        # Reset document status and queue for reprocessing
        retry_tasks = []
        
        for document in failed_documents:
            document.processing_status = "pending"
            db.commit()
            
            # Queue for reprocessing
            task = process_document.apply_async(args=[document.id, batch_id])
            retry_tasks.append(task)
        
        return {
            "status": "retry_queued",
            "batch_id": batch_id,
            "retry_count": len(failed_documents),
            "task_ids": [task.id for task in retry_tasks]
        }
        
    except Exception as e:
        logger.error(f"Error retrying failed documents: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.batch_processing.get_batch_status")
def get_batch_status(self, batch_id: int) -> Dict[str, Any]:
    """
    Get detailed status of a batch processing job
    """
    db = next(get_db())
    
    try:
        batch = db.query(BatchUpload).filter(BatchUpload.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Get document status counts
        documents = db.query(Document).filter(Document.batch_upload_id == batch_id).all()
        
        status_counts = {}
        for doc in documents:
            status = doc.processing_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate progress
        total = len(documents)
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        processing = status_counts.get("processing", 0)
        pending = status_counts.get("pending", 0)
        
        progress_percentage = (completed + failed) / total * 100 if total > 0 else 0
        
        return {
            "batch_id": batch_id,
            "batch_name": batch.batch_name,
            "status": batch.status,
            "uploaded_by": batch.uploaded_by,
            "created_at": batch.created_at.isoformat(),
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "total_documents": total,
            "processed_documents": batch.processed_documents,
            "failed_documents": batch.failed_documents,
            "progress_percentage": progress_percentage,
            "status_breakdown": {
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "pending": pending,
                "review_required": status_counts.get("review_required", 0),
                "quality_failed": status_counts.get("quality_failed", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise
    
    finally:
        db.close()

def should_split_document(file_path: str) -> bool:
    """
    Determine if a document should be split based on file characteristics
    """
    try:
        # Simple heuristic: split if file is large (>5MB) or has many pages
        file_size = os.path.getsize(file_path)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return True
        
        # Could add more sophisticated logic here:
        # - Check number of pages in PDF
        # - Analyze document structure
        # - Look for page break indicators
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if document should be split: {str(e)}")
        return False