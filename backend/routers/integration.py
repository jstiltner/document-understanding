from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import csv
import json
import io

from database.database import get_db
from database.models import Document, FieldExtraction, BatchUpload, User
from auth.dependencies import get_current_active_user, require_permission
from services.auth_service import AuthService

router = APIRouter(prefix="/integration", tags=["integration"])

# Pydantic models
class DocumentExport(BaseModel):
    id: int
    filename: str
    processing_status: str
    extracted_fields: Dict[str, Any] = {}
    extraction_confidence: float = None
    requires_review: bool = False
    upload_timestamp: datetime
    extraction_timestamp: datetime = None
    reviewed_by: str = None
    review_timestamp: datetime = None

class BatchExport(BaseModel):
    id: int
    batch_name: str
    uploaded_by: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    status: str
    created_at: datetime
    completed_at: datetime = None

class ExportRequest(BaseModel):
    format: str = "json"  # json, csv, xml
    date_from: datetime = None
    date_to: datetime = None
    status_filter: List[str] = []
    include_fields: List[str] = []
    batch_id: int = None

class WebhookConfig(BaseModel):
    url: str
    events: List[str]  # document_completed, batch_completed, review_completed
    secret: str = None
    active: bool = True

@router.get("/export/documents")
async def export_documents(
    format: str = Query("json", regex="^(json|csv|xml)$"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    status: Optional[List[str]] = Query(None),
    batch_id: Optional[int] = None,
    include_review_data: bool = True,
    current_user: User = Depends(require_permission("view_documents")),
    db: Session = Depends(get_db)
):
    """Export documents in various formats"""
    
    try:
        # Build query
        query = db.query(Document)
        
        # Apply filters
        if date_from:
            query = query.filter(Document.upload_timestamp >= date_from)
        
        if date_to:
            query = query.filter(Document.upload_timestamp <= date_to)
        
        if status:
            query = query.filter(Document.processing_status.in_(status))
        
        if batch_id:
            query = query.filter(Document.batch_upload_id == batch_id)
        
        # Execute query
        documents = query.all()
        
        if format == "json":
            return _export_documents_json(documents, include_review_data)
        elif format == "csv":
            return _export_documents_csv(documents, include_review_data)
        elif format == "xml":
            return _export_documents_xml(documents, include_review_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

@router.get("/export/batches")
async def export_batches(
    format: str = Query("json", regex="^(json|csv)$"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_permission("manage_batches")),
    db: Session = Depends(get_db)
):
    """Export batch information"""
    
    try:
        query = db.query(BatchUpload)
        
        if date_from:
            query = query.filter(BatchUpload.created_at >= date_from)
        
        if date_to:
            query = query.filter(BatchUpload.created_at <= date_to)
        
        batches = query.all()
        
        if format == "json":
            return _export_batches_json(batches)
        elif format == "csv":
            return _export_batches_csv(batches)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch export failed: {str(e)}"
        )

@router.get("/api/documents/{document_id}")
async def get_document_api(
    document_id: int,
    include_extractions: bool = True,
    current_user: User = Depends(require_permission("view_documents")),
    db: Session = Depends(get_db)
):
    """Get single document via REST API"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    result = {
        "id": document.id,
        "filename": document.filename,
        "processing_status": document.processing_status,
        "upload_timestamp": document.upload_timestamp.isoformat(),
        "extraction_confidence": document.extraction_confidence,
        "requires_review": document.requires_review,
        "review_completed": document.review_completed
    }
    
    if include_extractions and document.extracted_fields:
        result["extracted_fields"] = document.extracted_fields
    
    if document.extraction_timestamp:
        result["extraction_timestamp"] = document.extraction_timestamp.isoformat()
    
    if document.review_timestamp:
        result["review_timestamp"] = document.review_timestamp.isoformat()
        result["reviewed_by"] = document.reviewed_by
    
    return result

@router.get("/api/documents")
async def list_documents_api(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    batch_id: Optional[int] = None,
    current_user: User = Depends(require_permission("view_documents")),
    db: Session = Depends(get_db)
):
    """List documents via REST API with pagination"""
    
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.processing_status == status)
    
    if batch_id:
        query = query.filter(Document.batch_upload_id == batch_id)
    
    total = query.count()
    documents = query.offset(offset).limit(limit).all()
    
    result = {
        "total": total,
        "limit": limit,
        "offset": offset,
        "documents": []
    }
    
    for doc in documents:
        doc_data = {
            "id": doc.id,
            "filename": doc.filename,
            "processing_status": doc.processing_status,
            "upload_timestamp": doc.upload_timestamp.isoformat(),
            "extraction_confidence": doc.extraction_confidence,
            "requires_review": doc.requires_review
        }
        
        if doc.extracted_fields:
            doc_data["extracted_fields"] = doc.extracted_fields
        
        result["documents"].append(doc_data)
    
    return result

@router.post("/webhooks/register")
async def register_webhook(
    webhook_config: WebhookConfig,
    current_user: User = Depends(require_permission("manage_system_config")),
    db: Session = Depends(get_db)
):
    """Register a webhook for system events"""
    
    # In a real implementation, this would store webhook configs in database
    # For now, return success
    
    return {
        "message": "Webhook registered successfully",
        "webhook_id": "webhook_123",
        "url": webhook_config.url,
        "events": webhook_config.events,
        "active": webhook_config.active
    }

@router.get("/health")
async def integration_health():
    """Health check endpoint for integration services"""
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "export": "available",
            "api": "available",
            "webhooks": "available"
        }
    }

@router.get("/schema/document")
async def get_document_schema(
    current_user: User = Depends(require_permission("view_documents"))
):
    """Get document data schema for integration"""
    
    return {
        "document": {
            "id": "integer",
            "filename": "string",
            "processing_status": "string (pending|processing|completed|failed|review_required)",
            "extracted_fields": "object",
            "extraction_confidence": "float (0.0-1.0)",
            "requires_review": "boolean",
            "upload_timestamp": "datetime (ISO 8601)",
            "extraction_timestamp": "datetime (ISO 8601)",
            "review_timestamp": "datetime (ISO 8601)",
            "reviewed_by": "string"
        },
        "extracted_fields": {
            "facility": "string",
            "reference_number": "string",
            "patient_last_name": "string",
            "patient_first_name": "string",
            "member_id": "string",
            "date_of_birth": "string (MM/DD/YYYY)",
            "denial_reason": "string",
            "payer": "string",
            "authorization_number": "string"
        }
    }

def _export_documents_json(documents: List[Document], include_review_data: bool) -> Dict[str, Any]:
    """Export documents as JSON"""
    
    result = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "total_documents": len(documents),
        "documents": []
    }
    
    for doc in documents:
        doc_data = {
            "id": doc.id,
            "filename": doc.filename,
            "processing_status": doc.processing_status,
            "extracted_fields": doc.extracted_fields or {},
            "extraction_confidence": doc.extraction_confidence,
            "requires_review": doc.requires_review,
            "upload_timestamp": doc.upload_timestamp.isoformat()
        }
        
        if doc.extraction_timestamp:
            doc_data["extraction_timestamp"] = doc.extraction_timestamp.isoformat()
        
        if include_review_data:
            if doc.review_timestamp:
                doc_data["review_timestamp"] = doc.review_timestamp.isoformat()
            if doc.reviewed_by:
                doc_data["reviewed_by"] = doc.reviewed_by
            if doc.review_notes:
                doc_data["review_notes"] = doc.review_notes
        
        result["documents"].append(doc_data)
    
    return result

def _export_documents_csv(documents: List[Document], include_review_data: bool) -> StreamingResponse:
    """Export documents as CSV"""
    
    output = io.StringIO()
    
    # Define CSV headers
    headers = [
        "id", "filename", "processing_status", "extraction_confidence",
        "requires_review", "upload_timestamp", "extraction_timestamp"
    ]
    
    # Add extracted field headers (get from first document with fields)
    field_headers = set()
    for doc in documents:
        if doc.extracted_fields:
            field_headers.update(doc.extracted_fields.keys())
    
    field_headers = sorted(list(field_headers))
    headers.extend(field_headers)
    
    if include_review_data:
        headers.extend(["reviewed_by", "review_timestamp", "review_notes"])
    
    writer = csv.writer(output)
    writer.writerow(headers)
    
    # Write data rows
    for doc in documents:
        row = [
            doc.id,
            doc.filename,
            doc.processing_status,
            doc.extraction_confidence,
            doc.requires_review,
            doc.upload_timestamp.isoformat(),
            doc.extraction_timestamp.isoformat() if doc.extraction_timestamp else ""
        ]
        
        # Add extracted field values
        for field_name in field_headers:
            value = ""
            if doc.extracted_fields and field_name in doc.extracted_fields:
                value = str(doc.extracted_fields[field_name])
            row.append(value)
        
        if include_review_data:
            row.extend([
                doc.reviewed_by or "",
                doc.review_timestamp.isoformat() if doc.review_timestamp else "",
                doc.review_notes or ""
            ])
        
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=documents_export.csv"}
    )

def _export_documents_xml(documents: List[Document], include_review_data: bool) -> Response:
    """Export documents as XML"""
    
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_content.append('<documents>')
    xml_content.append(f'  <export_timestamp>{datetime.utcnow().isoformat()}</export_timestamp>')
    xml_content.append(f'  <total_documents>{len(documents)}</total_documents>')
    
    for doc in documents:
        xml_content.append('  <document>')
        xml_content.append(f'    <id>{doc.id}</id>')
        xml_content.append(f'    <filename><![CDATA[{doc.filename}]]></filename>')
        xml_content.append(f'    <processing_status>{doc.processing_status}</processing_status>')
        xml_content.append(f'    <extraction_confidence>{doc.extraction_confidence}</extraction_confidence>')
        xml_content.append(f'    <requires_review>{doc.requires_review}</requires_review>')
        xml_content.append(f'    <upload_timestamp>{doc.upload_timestamp.isoformat()}</upload_timestamp>')
        
        if doc.extraction_timestamp:
            xml_content.append(f'    <extraction_timestamp>{doc.extraction_timestamp.isoformat()}</extraction_timestamp>')
        
        if doc.extracted_fields:
            xml_content.append('    <extracted_fields>')
            for field_name, field_value in doc.extracted_fields.items():
                xml_content.append(f'      <{field_name}><![CDATA[{field_value}]]></{field_name}>')
            xml_content.append('    </extracted_fields>')
        
        if include_review_data:
            if doc.reviewed_by:
                xml_content.append(f'    <reviewed_by><![CDATA[{doc.reviewed_by}]]></reviewed_by>')
            if doc.review_timestamp:
                xml_content.append(f'    <review_timestamp>{doc.review_timestamp.isoformat()}</review_timestamp>')
            if doc.review_notes:
                xml_content.append(f'    <review_notes><![CDATA[{doc.review_notes}]]></review_notes>')
        
        xml_content.append('  </document>')
    
    xml_content.append('</documents>')
    
    return Response(
        content='\n'.join(xml_content),
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=documents_export.xml"}
    )

def _export_batches_json(batches: List[BatchUpload]) -> Dict[str, Any]:
    """Export batches as JSON"""
    
    result = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "total_batches": len(batches),
        "batches": []
    }
    
    for batch in batches:
        batch_data = {
            "id": batch.id,
            "batch_name": batch.batch_name,
            "uploaded_by": batch.uploaded_by,
            "total_documents": batch.total_documents,
            "processed_documents": batch.processed_documents,
            "failed_documents": batch.failed_documents,
            "status": batch.status,
            "created_at": batch.created_at.isoformat()
        }
        
        if batch.completed_at:
            batch_data["completed_at"] = batch.completed_at.isoformat()
        
        result["batches"].append(batch_data)
    
    return result

def _export_batches_csv(batches: List[BatchUpload]) -> StreamingResponse:
    """Export batches as CSV"""
    
    output = io.StringIO()
    
    headers = [
        "id", "batch_name", "uploaded_by", "total_documents",
        "processed_documents", "failed_documents", "status",
        "created_at", "completed_at"
    ]
    
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for batch in batches:
        row = [
            batch.id,
            batch.batch_name,
            batch.uploaded_by,
            batch.total_documents,
            batch.processed_documents,
            batch.failed_documents,
            batch.status,
            batch.created_at.isoformat(),
            batch.completed_at.isoformat() if batch.completed_at else ""
        ]
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=batches_export.csv"}
    )