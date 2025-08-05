import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database.models import (
    Document, BusinessRule, BusinessRuleViolation, WorkflowAssignment, 
    User, FieldDefinition
)
from datetime import datetime, timedelta
import re
import json

logger = logging.getLogger(__name__)

class WorkflowService:
    """Service for managing workflow assignments and business rule validation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_business_rules(self, document_id: int) -> Dict[str, Any]:
        """
        Validate document against all active business rules
        
        Args:
            document_id: ID of the document to validate
            
        Returns:
            Dictionary containing validation results and violations
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get all active business rules
            active_rules = self.db.query(BusinessRule).filter(BusinessRule.is_active == True).all()
            
            violations = []
            warnings = []
            
            for rule in active_rules:
                try:
                    violation = self._validate_single_rule(document, rule)
                    if violation:
                        # Store violation in database
                        rule_violation = BusinessRuleViolation(
                            document_id=document_id,
                            rule_id=rule.id,
                            violation_details=violation,
                            severity=rule.severity
                        )
                        self.db.add(rule_violation)
                        
                        if rule.severity == "error":
                            violations.append(violation)
                        else:
                            warnings.append(violation)
                
                except Exception as e:
                    logger.error(f"Error validating rule {rule.id}: {str(e)}")
                    continue
            
            self.db.commit()
            
            return {
                "has_violations": len(violations) > 0,
                "has_warnings": len(warnings) > 0,
                "violations": violations,
                "warnings": warnings,
                "total_rules_checked": len(active_rules)
            }
            
        except Exception as e:
            logger.error(f"Error validating business rules for document {document_id}: {str(e)}")
            return {
                "has_violations": False,
                "has_warnings": False,
                "violations": [],
                "warnings": [],
                "error": str(e)
            }
    
    def _validate_single_rule(self, document: Document, rule: BusinessRule) -> Optional[Dict[str, Any]]:
        """Validate a single business rule against a document"""
        
        rule_def = rule.rule_definition
        rule_type = rule.rule_type
        
        if rule_type == "field_validation":
            return self._validate_field_rule(document, rule, rule_def)
        elif rule_type == "cross_field":
            return self._validate_cross_field_rule(document, rule, rule_def)
        elif rule_type == "business_logic":
            return self._validate_business_logic_rule(document, rule, rule_def)
        
        return None
    
    def _validate_field_rule(self, document: Document, rule: BusinessRule, rule_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate field-specific rules"""
        
        field_name = rule_def.get("field_name")
        validation_type = rule_def.get("validation_type")
        expected_value = rule_def.get("expected_value")
        pattern = rule_def.get("pattern")
        
        if not field_name or not document.extracted_fields:
            return None
        
        field_value = document.extracted_fields.get(field_name)
        
        if validation_type == "required" and not field_value:
            return {
                "rule_name": rule.name,
                "rule_type": "field_validation",
                "field_name": field_name,
                "issue": f"Required field '{field_name}' is missing",
                "severity": rule.severity
            }
        
        if validation_type == "pattern" and field_value and pattern:
            if not re.match(pattern, str(field_value)):
                return {
                    "rule_name": rule.name,
                    "rule_type": "field_validation",
                    "field_name": field_name,
                    "issue": f"Field '{field_name}' does not match required pattern",
                    "current_value": field_value,
                    "expected_pattern": pattern,
                    "severity": rule.severity
                }
        
        if validation_type == "value_check" and field_value and expected_value:
            if str(field_value).lower() != str(expected_value).lower():
                return {
                    "rule_name": rule.name,
                    "rule_type": "field_validation",
                    "field_name": field_name,
                    "issue": f"Field '{field_name}' has unexpected value",
                    "current_value": field_value,
                    "expected_value": expected_value,
                    "severity": rule.severity
                }
        
        return None
    
    def _validate_cross_field_rule(self, document: Document, rule: BusinessRule, rule_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate rules that involve multiple fields"""
        
        if not document.extracted_fields:
            return None
        
        rule_logic = rule_def.get("logic")
        fields = rule_def.get("fields", [])
        
        # Example cross-field validations
        if rule_logic == "denial_no_auth_number":
            denial_reason = document.extracted_fields.get("denial_reason")
            auth_number = document.extracted_fields.get("authorization_number")
            
            if denial_reason and auth_number:
                return {
                    "rule_name": rule.name,
                    "rule_type": "cross_field",
                    "issue": "Denied documents should not have authorization numbers",
                    "fields_involved": ["denial_reason", "authorization_number"],
                    "current_values": {
                        "denial_reason": denial_reason,
                        "authorization_number": auth_number
                    },
                    "severity": rule.severity
                }
        
        elif rule_logic == "age_service_mismatch":
            # Calculate age from date of birth
            dob = document.extracted_fields.get("date_of_birth")
            service = document.extracted_fields.get("service", "").lower()
            
            if dob and service:
                try:
                    # Simple age calculation (would need more robust date parsing)
                    if "pediatric" in service or "child" in service:
                        # Check if patient might be adult based on service type
                        return {
                            "rule_name": rule.name,
                            "rule_type": "cross_field",
                            "issue": "Potential age/service mismatch detected",
                            "fields_involved": ["date_of_birth", "service"],
                            "current_values": {
                                "date_of_birth": dob,
                                "service": service
                            },
                            "severity": rule.severity
                        }
                except Exception:
                    pass
        
        elif rule_logic == "custom_expression":
            # Allow custom Python expressions for complex rules
            expression = rule_def.get("expression")
            if expression:
                try:
                    # Create safe evaluation context
                    context = {
                        "fields": document.extracted_fields,
                        "re": re,
                        "len": len,
                        "str": str,
                        "int": int,
                        "float": float
                    }
                    
                    # Evaluate expression (in production, use a safer evaluator)
                    result = eval(expression, {"__builtins__": {}}, context)
                    
                    if result:  # Rule violation detected
                        return {
                            "rule_name": rule.name,
                            "rule_type": "cross_field",
                            "issue": rule_def.get("violation_message", "Custom rule violation"),
                            "fields_involved": fields,
                            "severity": rule.severity
                        }
                        
                except Exception as e:
                    logger.error(f"Error evaluating custom expression: {str(e)}")
        
        return None
    
    def _validate_business_logic_rule(self, document: Document, rule: BusinessRule, rule_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate business logic rules"""
        
        if not document.extracted_fields:
            return None
        
        logic_type = rule_def.get("logic_type")
        
        if logic_type == "insurance_coverage_check":
            # Check if insurance information is consistent
            payer = document.extracted_fields.get("payer")
            member_id = document.extracted_fields.get("member_id")
            
            if payer and not member_id:
                return {
                    "rule_name": rule.name,
                    "rule_type": "business_logic",
                    "issue": "Payer specified but member ID is missing",
                    "fields_involved": ["payer", "member_id"],
                    "severity": rule.severity
                }
        
        elif logic_type == "authorization_consistency":
            # Check authorization-related field consistency
            auth_number = document.extracted_fields.get("authorization_number")
            denial_reason = document.extracted_fields.get("denial_reason")
            
            if auth_number and denial_reason:
                return {
                    "rule_name": rule.name,
                    "rule_type": "business_logic",
                    "issue": "Document has both authorization number and denial reason",
                    "fields_involved": ["authorization_number", "denial_reason"],
                    "severity": rule.severity
                }
        
        return None
    
    def assign_for_review(self, document_id: int, priority: str = "normal", assigned_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Assign a document for review based on confidence and business rules
        
        Args:
            document_id: ID of the document to assign
            priority: Priority level (urgent, high, normal, low)
            assigned_to: Specific user to assign to (optional)
            
        Returns:
            Assignment details
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Determine assignment type based on document status
            assignment_type = "review"
            
            # Check for business rule violations
            violations = self.db.query(BusinessRuleViolation).filter(
                BusinessRuleViolation.document_id == document_id,
                BusinessRuleViolation.resolved == False
            ).all()
            
            if violations:
                error_violations = [v for v in violations if v.severity == "error"]
                if error_violations:
                    assignment_type = "quality_check"
                    priority = "high"
            
            # Auto-assign if not specified
            if not assigned_to:
                assigned_to = self._auto_assign_reviewer(assignment_type, priority)
            
            # Calculate due date based on priority
            due_date = self._calculate_due_date(priority)
            
            # Create assignment
            assignment = WorkflowAssignment(
                document_id=document_id,
                assigned_to=assigned_to,
                assignment_type=assignment_type,
                priority=priority,
                due_date=due_date
            )
            
            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(assignment)
            
            return {
                "assignment_id": assignment.id,
                "document_id": document_id,
                "assigned_to": assigned_to,
                "assignment_type": assignment_type,
                "priority": priority,
                "due_date": due_date.isoformat() if due_date else None,
                "violations_count": len(violations)
            }
            
        except Exception as e:
            logger.error(f"Error assigning document for review: {str(e)}")
            raise
    
    def _auto_assign_reviewer(self, assignment_type: str, priority: str) -> str:
        """Auto-assign to the best available reviewer"""
        
        # Get available reviewers based on assignment type
        if assignment_type == "quality_check":
            # Assign quality checks to supervisors
            available_users = self.db.query(User).filter(
                User.role.in_(["supervisor", "admin"]),
                User.is_active == True
            ).all()
        else:
            # Regular reviews can go to reviewers
            available_users = self.db.query(User).filter(
                User.role.in_(["reviewer", "supervisor", "admin"]),
                User.is_active == True
            ).all()
        
        if not available_users:
            # Fallback to any active user
            available_users = self.db.query(User).filter(User.is_active == True).all()
        
        if not available_users:
            return "system"  # Fallback assignment
        
        # Simple round-robin assignment (could be more sophisticated)
        # Count current assignments for each user
        user_workloads = {}
        for user in available_users:
            active_assignments = self.db.query(WorkflowAssignment).filter(
                WorkflowAssignment.assigned_to == user.username,
                WorkflowAssignment.status.in_(["assigned", "in_progress"])
            ).count()
            user_workloads[user.username] = active_assignments
        
        # Assign to user with lowest workload
        assigned_user = min(user_workloads.keys(), key=lambda u: user_workloads[u])
        return assigned_user
    
    def _calculate_due_date(self, priority: str) -> Optional[datetime]:
        """Calculate due date based on priority"""
        
        now = datetime.utcnow()
        
        if priority == "urgent":
            return now + timedelta(hours=4)
        elif priority == "high":
            return now + timedelta(hours=24)
        elif priority == "normal":
            return now + timedelta(days=3)
        elif priority == "low":
            return now + timedelta(days=7)
        
        return now + timedelta(days=3)  # Default
    
    def get_user_workload(self, username: str) -> Dict[str, Any]:
        """Get current workload for a user"""
        
        try:
            # Get active assignments
            active_assignments = self.db.query(WorkflowAssignment).filter(
                WorkflowAssignment.assigned_to == username,
                WorkflowAssignment.status.in_(["assigned", "in_progress"])
            ).all()
            
            # Group by priority and type
            workload_summary = {
                "total_assignments": len(active_assignments),
                "by_priority": {},
                "by_type": {},
                "overdue_count": 0
            }
            
            now = datetime.utcnow()
            
            for assignment in active_assignments:
                # Count by priority
                priority = assignment.priority
                workload_summary["by_priority"][priority] = workload_summary["by_priority"].get(priority, 0) + 1
                
                # Count by type
                assignment_type = assignment.assignment_type
                workload_summary["by_type"][assignment_type] = workload_summary["by_type"].get(assignment_type, 0) + 1
                
                # Count overdue
                if assignment.due_date and assignment.due_date < now:
                    workload_summary["overdue_count"] += 1
            
            return workload_summary
            
        except Exception as e:
            logger.error(f"Error getting user workload: {str(e)}")
            return {
                "total_assignments": 0,
                "by_priority": {},
                "by_type": {},
                "overdue_count": 0,
                "error": str(e)
            }
    
    def complete_assignment(self, assignment_id: int, completed_by: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Mark an assignment as completed"""
        
        try:
            assignment = self.db.query(WorkflowAssignment).filter(WorkflowAssignment.id == assignment_id).first()
            if not assignment:
                raise ValueError(f"Assignment {assignment_id} not found")
            
            assignment.status = "completed"
            assignment.completed_at = datetime.utcnow()
            
            # Update document review status
            document = self.db.query(Document).filter(Document.id == assignment.document_id).first()
            if document:
                document.review_completed = True
                document.reviewed_by = completed_by
                document.review_timestamp = datetime.utcnow()
                if notes:
                    document.review_notes = notes
            
            self.db.commit()
            
            return {
                "assignment_id": assignment_id,
                "document_id": assignment.document_id,
                "completed_by": completed_by,
                "completed_at": assignment.completed_at.isoformat(),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error completing assignment: {str(e)}")
            raise
    
    def get_pending_assignments(self, username: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending assignments for a user or all users"""
        
        try:
            query = self.db.query(WorkflowAssignment).filter(
                WorkflowAssignment.status.in_(["assigned", "in_progress"])
            )
            
            if username:
                query = query.filter(WorkflowAssignment.assigned_to == username)
            
            assignments = query.order_by(
                WorkflowAssignment.priority.desc(),
                WorkflowAssignment.assigned_at.asc()
            ).limit(limit).all()
            
            result = []
            for assignment in assignments:
                document = self.db.query(Document).filter(Document.id == assignment.document_id).first()
                
                result.append({
                    "assignment_id": assignment.id,
                    "document_id": assignment.document_id,
                    "document_filename": document.filename if document else "Unknown",
                    "assigned_to": assignment.assigned_to,
                    "assignment_type": assignment.assignment_type,
                    "priority": assignment.priority,
                    "assigned_at": assignment.assigned_at.isoformat(),
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "status": assignment.status,
                    "is_overdue": assignment.due_date and assignment.due_date < datetime.utcnow()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pending assignments: {str(e)}")
            return []