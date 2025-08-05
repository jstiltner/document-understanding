import logging
from typing import Dict, Any
from celery import current_task
from celery_app import celery_app
from database.database import get_db
from database.models import SystemMetrics, Document, BatchUpload, User, ProcessingQueue
from datetime import datetime, timedelta
import psutil
import redis
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, generate_latest
import json

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.monitoring.collect_metrics")
def collect_metrics(self) -> Dict[str, Any]:
    """
    Collect system metrics and store them in the database
    """
    db = next(get_db())
    
    try:
        metrics_collected = []
        
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = [
            {
                "metric_name": "cpu_usage_percent",
                "metric_value": cpu_usage,
                "metric_type": "gauge",
                "labels": {"component": "system"}
            },
            {
                "metric_name": "memory_usage_percent",
                "metric_value": memory.percent,
                "metric_type": "gauge",
                "labels": {"component": "system"}
            },
            {
                "metric_name": "memory_available_bytes",
                "metric_value": memory.available,
                "metric_type": "gauge",
                "labels": {"component": "system"}
            },
            {
                "metric_name": "disk_usage_percent",
                "metric_value": disk.percent,
                "metric_type": "gauge",
                "labels": {"component": "system"}
            },
            {
                "metric_name": "disk_free_bytes",
                "metric_value": disk.free,
                "metric_type": "gauge",
                "labels": {"component": "system"}
            }
        ]
        
        # Database metrics
        total_documents = db.query(Document).count()
        pending_documents = db.query(Document).filter(Document.processing_status == "pending").count()
        processing_documents = db.query(Document).filter(Document.processing_status == "processing").count()
        completed_documents = db.query(Document).filter(Document.processing_status == "completed").count()
        failed_documents = db.query(Document).filter(Document.processing_status == "failed").count()
        review_required = db.query(Document).filter(Document.requires_review == True).count()
        
        # Active batches
        active_batches = db.query(BatchUpload).filter(BatchUpload.status.in_(["pending", "processing"])).count()
        
        database_metrics = [
            {
                "metric_name": "documents_total",
                "metric_value": total_documents,
                "metric_type": "gauge",
                "labels": {"component": "database"}
            },
            {
                "metric_name": "documents_by_status",
                "metric_value": pending_documents,
                "metric_type": "gauge",
                "labels": {"component": "database", "status": "pending"}
            },
            {
                "metric_name": "documents_by_status",
                "metric_value": processing_documents,
                "metric_type": "gauge",
                "labels": {"component": "database", "status": "processing"}
            },
            {
                "metric_name": "documents_by_status",
                "metric_value": completed_documents,
                "metric_type": "gauge",
                "labels": {"component": "database", "status": "completed"}
            },
            {
                "metric_name": "documents_by_status",
                "metric_value": failed_documents,
                "metric_type": "gauge",
                "labels": {"component": "database", "status": "failed"}
            },
            {
                "metric_name": "documents_requiring_review",
                "metric_value": review_required,
                "metric_type": "gauge",
                "labels": {"component": "database"}
            },
            {
                "metric_name": "active_batches",
                "metric_value": active_batches,
                "metric_type": "gauge",
                "labels": {"component": "database"}
            }
        ]
        
        # Queue metrics (Redis/Celery)
        try:
            redis_client = redis.Redis.from_url(celery_app.conf.broker_url)
            
            # Get queue lengths
            document_queue_length = redis_client.llen("celery:document_processing")
            batch_queue_length = redis_client.llen("celery:batch_processing")
            monitoring_queue_length = redis_client.llen("celery:monitoring")
            
            queue_metrics = [
                {
                    "metric_name": "queue_length",
                    "metric_value": document_queue_length,
                    "metric_type": "gauge",
                    "labels": {"component": "queue", "queue": "document_processing"}
                },
                {
                    "metric_name": "queue_length",
                    "metric_value": batch_queue_length,
                    "metric_type": "gauge",
                    "labels": {"component": "queue", "queue": "batch_processing"}
                },
                {
                    "metric_name": "queue_length",
                    "metric_value": monitoring_queue_length,
                    "metric_type": "gauge",
                    "labels": {"component": "queue", "queue": "monitoring"}
                }
            ]
            
        except Exception as e:
            logger.warning(f"Could not collect queue metrics: {str(e)}")
            queue_metrics = []
        
        # Processing performance metrics (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_completed = db.query(Document).filter(
            Document.processing_status == "completed",
            Document.extraction_timestamp >= one_hour_ago
        ).count()
        
        avg_confidence = db.query(Document).filter(
            Document.extraction_confidence.isnot(None),
            Document.extraction_timestamp >= one_hour_ago
        ).with_entities(db.func.avg(Document.extraction_confidence)).scalar() or 0.0
        
        performance_metrics = [
            {
                "metric_name": "documents_processed_last_hour",
                "metric_value": recent_completed,
                "metric_type": "gauge",
                "labels": {"component": "performance"}
            },
            {
                "metric_name": "average_extraction_confidence",
                "metric_value": float(avg_confidence),
                "metric_type": "gauge",
                "labels": {"component": "performance", "timeframe": "last_hour"}
            }
        ]
        
        # Combine all metrics
        all_metrics = system_metrics + database_metrics + queue_metrics + performance_metrics
        
        # Store metrics in database
        for metric_data in all_metrics:
            metric = SystemMetrics(**metric_data)
            db.add(metric)
            metrics_collected.append(metric_data["metric_name"])
        
        db.commit()
        
        return {
            "status": "completed",
            "metrics_collected": len(all_metrics),
            "metric_names": metrics_collected,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.monitoring.cleanup_old_tasks")
def cleanup_old_tasks(self) -> Dict[str, Any]:
    """
    Clean up old task results and metrics
    """
    db = next(get_db())
    
    try:
        # Clean up old metrics (keep last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        old_metrics = db.query(SystemMetrics).filter(
            SystemMetrics.timestamp < seven_days_ago
        ).delete()
        
        # Clean up old processing queue entries
        old_queue_entries = db.query(ProcessingQueue).filter(
            ProcessingQueue.completed_at < seven_days_ago,
            ProcessingQueue.status == "completed"
        ).delete()
        
        db.commit()
        
        return {
            "status": "completed",
            "cleaned_metrics": old_metrics,
            "cleaned_queue_entries": old_queue_entries,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.monitoring.generate_health_report")
def generate_health_report(self) -> Dict[str, Any]:
    """
    Generate a comprehensive system health report
    """
    db = next(get_db())
    
    try:
        # Get recent metrics
        recent_metrics = db.query(SystemMetrics).filter(
            SystemMetrics.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        # Organize metrics by type
        metrics_by_name = {}
        for metric in recent_metrics:
            if metric.metric_name not in metrics_by_name:
                metrics_by_name[metric.metric_name] = []
            metrics_by_name[metric.metric_name].append(metric)
        
        # System health checks
        health_status = "healthy"
        issues = []
        
        # Check CPU usage
        cpu_metrics = metrics_by_name.get("cpu_usage_percent", [])
        if cpu_metrics:
            avg_cpu = sum(m.metric_value for m in cpu_metrics) / len(cpu_metrics)
            if avg_cpu > 80:
                health_status = "warning"
                issues.append(f"High CPU usage: {avg_cpu:.1f}%")
            elif avg_cpu > 95:
                health_status = "critical"
        
        # Check memory usage
        memory_metrics = metrics_by_name.get("memory_usage_percent", [])
        if memory_metrics:
            avg_memory = sum(m.metric_value for m in memory_metrics) / len(memory_metrics)
            if avg_memory > 85:
                health_status = "warning"
                issues.append(f"High memory usage: {avg_memory:.1f}%")
            elif avg_memory > 95:
                health_status = "critical"
        
        # Check disk usage
        disk_metrics = metrics_by_name.get("disk_usage_percent", [])
        if disk_metrics:
            avg_disk = sum(m.metric_value for m in disk_metrics) / len(disk_metrics)
            if avg_disk > 80:
                health_status = "warning"
                issues.append(f"High disk usage: {avg_disk:.1f}%")
            elif avg_disk > 90:
                health_status = "critical"
        
        # Check processing queues
        queue_metrics = [m for m in recent_metrics if m.metric_name == "queue_length"]
        total_queue_length = sum(m.metric_value for m in queue_metrics)
        
        if total_queue_length > 100:
            health_status = "warning"
            issues.append(f"High queue backlog: {total_queue_length} items")
        elif total_queue_length > 500:
            health_status = "critical"
        
        # Check failed documents
        failed_docs = db.query(Document).filter(Document.processing_status == "failed").count()
        total_docs = db.query(Document).count()
        
        if total_docs > 0:
            failure_rate = failed_docs / total_docs
            if failure_rate > 0.1:  # 10% failure rate
                health_status = "warning"
                issues.append(f"High failure rate: {failure_rate:.1%}")
            elif failure_rate > 0.2:  # 20% failure rate
                health_status = "critical"
        
        # Processing throughput check
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_processed = db.query(Document).filter(
            Document.processing_status == "completed",
            Document.extraction_timestamp >= one_hour_ago
        ).count()
        
        # Generate recommendations
        recommendations = []
        
        if health_status == "critical":
            recommendations.append("Immediate attention required - system performance is severely degraded")
        elif health_status == "warning":
            recommendations.append("Monitor system closely - performance issues detected")
        
        if total_queue_length > 50:
            recommendations.append("Consider scaling up worker processes to handle queue backlog")
        
        if failed_docs > 10:
            recommendations.append("Investigate failed document processing - check logs for common errors")
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": issues,
            "recommendations": recommendations,
            "metrics_summary": {
                "total_documents": total_docs,
                "failed_documents": failed_docs,
                "queue_backlog": total_queue_length,
                "processed_last_hour": recent_processed
            },
            "detailed_metrics": {
                name: [{"value": m.metric_value, "timestamp": m.timestamp.isoformat()} 
                       for m in metrics]
                for name, metrics in metrics_by_name.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating health report: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.monitoring.alert_on_issues")
def alert_on_issues(self, health_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send alerts based on health report issues
    """
    try:
        if health_report["status"] == "critical":
            # In a real implementation, this would send emails, Slack messages, etc.
            logger.critical(f"CRITICAL SYSTEM ALERT: {health_report['issues']}")
            
            # Could integrate with:
            # - Email notifications
            # - Slack/Teams webhooks
            # - PagerDuty
            # - SMS alerts
            
        elif health_report["status"] == "warning":
            logger.warning(f"System warning: {health_report['issues']}")
        
        return {
            "status": "alerts_processed",
            "alert_level": health_report["status"],
            "issues_count": len(health_report["issues"])
        }
        
    except Exception as e:
        logger.error(f"Error sending alerts: {str(e)}")
        raise

@celery_app.task(bind=True, name="tasks.monitoring.export_prometheus_metrics")
def export_prometheus_metrics(self) -> str:
    """
    Export metrics in Prometheus format
    """
    db = next(get_db())
    
    try:
        registry = CollectorRegistry()
        
        # Create Prometheus metrics
        cpu_gauge = Gauge('system_cpu_usage_percent', 'CPU usage percentage', registry=registry)
        memory_gauge = Gauge('system_memory_usage_percent', 'Memory usage percentage', registry=registry)
        documents_gauge = Gauge('documents_total', 'Total number of documents', ['status'], registry=registry)
        queue_gauge = Gauge('queue_length', 'Queue length', ['queue'], registry=registry)
        
        # Get latest metrics
        latest_metrics = db.query(SystemMetrics).filter(
            SystemMetrics.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        # Update Prometheus metrics
        for metric in latest_metrics:
            if metric.metric_name == "cpu_usage_percent":
                cpu_gauge.set(metric.metric_value)
            elif metric.metric_name == "memory_usage_percent":
                memory_gauge.set(metric.metric_value)
            elif metric.metric_name == "documents_by_status":
                status = metric.labels.get("status", "unknown")
                documents_gauge.labels(status=status).set(metric.metric_value)
            elif metric.metric_name == "queue_length":
                queue_name = metric.labels.get("queue", "unknown")
                queue_gauge.labels(queue=queue_name).set(metric.metric_value)
        
        # Generate Prometheus format
        return generate_latest(registry).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error exporting Prometheus metrics: {str(e)}")
        raise
    
    finally:
        db.close()