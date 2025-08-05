from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from datetime import datetime, timedelta

from database.database import get_db
from database.models import (
    Document, BatchUpload, User, SystemMetrics, ModelPerformance,
    HumanFeedback, WorkflowAssignment, BusinessRuleViolation
)
from auth.dependencies import get_current_active_user, require_permission
from tasks.monitoring import generate_health_report, export_prometheus_metrics

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Pydantic models
class SystemHealth(BaseModel):
    status: str
    timestamp: str
    issues: List[str]
    recommendations: List[str]
    metrics_summary: Dict[str, Any]

class ProcessingStats(BaseModel):
    total_documents: int
    processed_today: int
    pending_documents: int
    failed_documents: int
    review_required: int
    average_processing_time: float
    throughput_per_hour: float

class UserPerformance(BaseModel):
    username: str
    full_name: str
    role: str
    documents_reviewed: int
    average_review_time: float
    accuracy_score: float
    active_assignments: int
    last_activity: datetime = None

class ModelMetrics(BaseModel):
    model_version: str
    field_name: str
    precision: float
    recall: float
    f1_score: float
    avg_confidence: float
    avg_reward: float
    total_predictions: int

@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    current_user: User = Depends(require_permission("view_system_metrics"))
):
    """Get comprehensive system health status"""
    
    try:
        # Generate health report using Celery task
        health_report = generate_health_report.delay()
        result = health_report.get(timeout=30)  # 30 second timeout
        
        return SystemHealth(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/stats/processing", response_model=ProcessingStats)
async def get_processing_stats(
    timeframe: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    current_user: User = Depends(require_permission("view_analytics")),
    db: Session = Depends(get_db)
):
    """Get document processing statistics"""
    
    try:
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "1h":
            start_time = now - timedelta(hours=1)
        elif timeframe == "24h":
            start_time = now - timedelta(days=1)
        elif timeframe == "7d":
            start_time = now - timedelta(days=7)
        elif timeframe == "30d":
            start_time = now - timedelta(days=30)
        
        # Get statistics
        total_documents = db.query(Document).count()
        
        processed_today = db.query(Document).filter(
            Document.extraction_timestamp >= start_time,
            Document.processing_status == "completed"
        ).count()
        
        pending_documents = db.query(Document).filter(
            Document.processing_status.in_(["pending", "processing"])
        ).count()
        
        failed_documents = db.query(Document).filter(
            Document.processing_status == "failed"
        ).count()
        
        review_required = db.query(Document).filter(
            Document.requires_review == True,
            Document.review_completed == False
        ).count()
        
        # Calculate average processing time
        processing_times = db.query(
            func.extract('epoch', Document.extraction_timestamp - Document.upload_timestamp)
        ).filter(
            Document.extraction_timestamp.isnot(None),
            Document.upload_timestamp >= start_time
        ).all()
        
        avg_processing_time = 0.0
        if processing_times:
            avg_processing_time = sum(t[0] for t in processing_times if t[0]) / len(processing_times)
        
        # Calculate throughput
        hours_in_timeframe = {
            "1h": 1, "24h": 24, "7d": 168, "30d": 720
        }[timeframe]
        
        throughput_per_hour = processed_today / hours_in_timeframe if hours_in_timeframe > 0 else 0
        
        return ProcessingStats(
            total_documents=total_documents,
            processed_today=processed_today,
            pending_documents=pending_documents,
            failed_documents=failed_documents,
            review_required=review_required,
            average_processing_time=avg_processing_time,
            throughput_per_hour=throughput_per_hour
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing stats: {str(e)}"
        )

@router.get("/stats/users", response_model=List[UserPerformance])
async def get_user_performance(
    timeframe: str = Query("7d", regex="^(24h|7d|30d)$"),
    current_user: User = Depends(require_permission("view_user_performance")),
    db: Session = Depends(get_db)
):
    """Get user performance statistics"""
    
    try:
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "24h":
            start_time = now - timedelta(days=1)
        elif timeframe == "7d":
            start_time = now - timedelta(days=7)
        elif timeframe == "30d":
            start_time = now - timedelta(days=30)
        
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        user_performance = []
        
        for user in users:
            # Count documents reviewed
            documents_reviewed = db.query(Document).filter(
                Document.reviewed_by == user.username,
                Document.review_timestamp >= start_time
            ).count()
            
            # Calculate average review time
            review_times = db.query(
                func.extract('epoch', Document.review_timestamp - Document.extraction_timestamp)
            ).filter(
                Document.reviewed_by == user.username,
                Document.review_timestamp >= start_time,
                Document.extraction_timestamp.isnot(None)
            ).all()
            
            avg_review_time = 0.0
            if review_times:
                avg_review_time = sum(t[0] for t in review_times if t[0]) / len(review_times)
            
            # Calculate accuracy score based on feedback
            feedback_records = db.query(HumanFeedback).filter(
                HumanFeedback.reviewer_id == user.username,
                HumanFeedback.review_timestamp >= start_time
            ).all()
            
            accuracy_score = 0.0
            if feedback_records:
                # Simple accuracy based on positive vs negative feedback
                positive_feedback = sum(1 for f in feedback_records if f.reward_score > 0)
                accuracy_score = positive_feedback / len(feedback_records)
            
            # Count active assignments
            active_assignments = db.query(WorkflowAssignment).filter(
                WorkflowAssignment.assigned_to == user.username,
                WorkflowAssignment.status.in_(["assigned", "in_progress"])
            ).count()
            
            user_performance.append(UserPerformance(
                username=user.username,
                full_name=user.full_name or user.username,
                role=user.role,
                documents_reviewed=documents_reviewed,
                average_review_time=avg_review_time,
                accuracy_score=accuracy_score,
                active_assignments=active_assignments,
                last_activity=user.last_login
            ))
        
        return user_performance
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user performance: {str(e)}"
        )

@router.get("/stats/models", response_model=List[ModelMetrics])
async def get_model_performance(
    model_version: Optional[str] = None,
    current_user: User = Depends(require_permission("view_analytics")),
    db: Session = Depends(get_db)
):
    """Get model performance metrics"""
    
    try:
        query = db.query(ModelPerformance)
        
        if model_version:
            query = query.filter(ModelPerformance.model_version == model_version)
        
        performance_records = query.all()
        
        metrics = []
        for record in performance_records:
            metrics.append(ModelMetrics(
                model_version=record.model_version,
                field_name=record.field_name,
                precision=record.precision or 0.0,
                recall=record.recall or 0.0,
                f1_score=record.f1_score or 0.0,
                avg_confidence=record.avg_confidence or 0.0,
                avg_reward=record.avg_reward or 0.0,
                total_predictions=record.total_predictions
            ))
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model performance: {str(e)}"
        )

@router.get("/metrics/system")
async def get_system_metrics(
    metric_name: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(require_permission("view_system_metrics")),
    db: Session = Depends(get_db)
):
    """Get system metrics over time"""
    
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.query(SystemMetrics).filter(
            SystemMetrics.timestamp >= start_time
        )
        
        if metric_name:
            query = query.filter(SystemMetrics.metric_name == metric_name)
        
        metrics = query.order_by(SystemMetrics.timestamp.desc()).all()
        
        result = {}
        for metric in metrics:
            if metric.metric_name not in result:
                result[metric.metric_name] = []
            
            result[metric.metric_name].append({
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.metric_value,
                "labels": metric.labels
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.get("/alerts")
async def get_active_alerts(
    severity: Optional[str] = Query(None, regex="^(info|warning|error|critical)$"),
    current_user: User = Depends(require_permission("view_system_metrics")),
    db: Session = Depends(get_db)
):
    """Get active system alerts"""
    
    try:
        # Get unresolved business rule violations as alerts
        query = db.query(BusinessRuleViolation).filter(
            BusinessRuleViolation.resolved == False
        )
        
        if severity:
            query = query.filter(BusinessRuleViolation.severity == severity)
        
        violations = query.all()
        
        alerts = []
        for violation in violations:
            alerts.append({
                "id": violation.id,
                "type": "business_rule_violation",
                "severity": violation.severity,
                "message": f"Business rule violation in document {violation.document_id}",
                "details": violation.violation_details,
                "created_at": violation.created_at.isoformat(),
                "document_id": violation.document_id
            })
        
        # Add system health alerts
        try:
            health_report = generate_health_report.delay()
            health_result = health_report.get(timeout=10)
            
            if health_result["status"] in ["warning", "critical"]:
                for issue in health_result["issues"]:
                    alerts.append({
                        "id": f"system_{len(alerts)}",
                        "type": "system_health",
                        "severity": health_result["status"],
                        "message": issue,
                        "created_at": health_result["timestamp"]
                    })
        except Exception:
            pass  # Don't fail if health check fails
        
        return {
            "total_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_permission("view_analytics")),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard data"""
    
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        
        # Processing statistics
        total_documents = db.query(Document).count()
        processed_today = db.query(Document).filter(
            Document.extraction_timestamp >= today_start
        ).count()
        
        pending_queue = db.query(Document).filter(
            Document.processing_status.in_(["pending", "processing"])
        ).count()
        
        review_queue = db.query(Document).filter(
            Document.requires_review == True,
            Document.review_completed == False
        ).count()
        
        # Batch statistics
        active_batches = db.query(BatchUpload).filter(
            BatchUpload.status.in_(["pending", "processing"])
        ).count()
        
        completed_batches_today = db.query(BatchUpload).filter(
            BatchUpload.completed_at >= today_start
        ).count()
        
        # User activity
        active_users = db.query(User).filter(
            User.is_active == True,
            User.last_login >= week_start
        ).count()
        
        # Model performance summary
        avg_confidence = db.query(func.avg(Document.extraction_confidence)).filter(
            Document.extraction_confidence.isnot(None),
            Document.extraction_timestamp >= week_start
        ).scalar() or 0.0
        
        # Recent activity
        recent_documents = db.query(Document).filter(
            Document.upload_timestamp >= now - timedelta(hours=24)
        ).order_by(Document.upload_timestamp.desc()).limit(10).all()
        
        recent_activity = []
        for doc in recent_documents:
            recent_activity.append({
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.processing_status,
                "timestamp": doc.upload_timestamp.isoformat(),
                "confidence": doc.extraction_confidence
            })
        
        return {
            "summary": {
                "total_documents": total_documents,
                "processed_today": processed_today,
                "pending_queue": pending_queue,
                "review_queue": review_queue,
                "active_batches": active_batches,
                "completed_batches_today": completed_batches_today,
                "active_users": active_users,
                "avg_confidence": float(avg_confidence)
            },
            "recent_activity": recent_activity,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )

@router.get("/prometheus")
async def get_prometheus_metrics(
    current_user: User = Depends(require_permission("view_system_metrics"))
):
    """Get metrics in Prometheus format"""
    
    try:
        # Export metrics using Celery task
        export_task = export_prometheus_metrics.delay()
        metrics_data = export_task.get(timeout=30)
        
        return Response(
            content=metrics_data,
            media_type="text/plain"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export Prometheus metrics: {str(e)}"
        )

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(require_permission("resolve_violations")),
    db: Session = Depends(get_db)
):
    """Resolve an active alert"""
    
    try:
        # Try to resolve as business rule violation
        violation = db.query(BusinessRuleViolation).filter(
            BusinessRuleViolation.id == alert_id
        ).first()
        
        if violation:
            violation.resolved = True
            violation.resolved_by = current_user.username
            violation.resolved_at = datetime.utcnow()
            db.commit()
            
            return {"message": "Alert resolved successfully"}
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )