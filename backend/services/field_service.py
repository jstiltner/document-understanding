import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import FieldDefinition, HumanFeedback, ModelPerformance
from datetime import datetime

logger = logging.getLogger(__name__)

class FieldDefinitionService:
    """Service for managing configurable field definitions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_fields(self) -> List[FieldDefinition]:
        """Get all active field definitions"""
        return self.db.query(FieldDefinition).filter(FieldDefinition.is_active == True).all()
    
    def get_required_fields(self) -> List[FieldDefinition]:
        """Get all required field definitions"""
        return self.db.query(FieldDefinition).filter(
            FieldDefinition.is_active == True,
            FieldDefinition.is_required == True
        ).all()
    
    def get_optional_fields(self) -> List[FieldDefinition]:
        """Get all optional field definitions"""
        return self.db.query(FieldDefinition).filter(
            FieldDefinition.is_active == True,
            FieldDefinition.is_required == False
        ).all()
    
    def create_field_definition(self, field_data: Dict[str, Any]) -> FieldDefinition:
        """Create a new field definition"""
        field_def = FieldDefinition(**field_data)
        self.db.add(field_def)
        self.db.commit()
        self.db.refresh(field_def)
        return field_def
    
    def update_field_definition(self, field_id: int, field_data: Dict[str, Any]) -> Optional[FieldDefinition]:
        """Update an existing field definition"""
        field_def = self.db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
        if field_def:
            for key, value in field_data.items():
                setattr(field_def, key, value)
            field_def.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(field_def)
        return field_def
    
    def delete_field_definition(self, field_id: int) -> bool:
        """Soft delete a field definition by setting is_active to False"""
        field_def = self.db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
        if field_def:
            field_def.is_active = False
            field_def.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def get_field_by_name(self, name: str) -> Optional[FieldDefinition]:
        """Get field definition by name"""
        return self.db.query(FieldDefinition).filter(
            FieldDefinition.name == name,
            FieldDefinition.is_active == True
        ).first()
    
    def initialize_default_fields(self):
        """Initialize default field definitions if none exist"""
        existing_count = self.db.query(FieldDefinition).count()
        if existing_count > 0:
            return
        
        default_fields = [
            # Required fields
            {
                "name": "facility",
                "display_name": "Facility",
                "description": "Healthcare facility name",
                "field_type": "text",
                "is_required": True,
                "extraction_hints": {"keywords": ["facility", "hospital", "clinic"], "context": "header"}
            },
            {
                "name": "reference_number",
                "display_name": "Reference Number",
                "description": "Document reference or case number",
                "field_type": "text",
                "is_required": True,
                "extraction_hints": {"keywords": ["reference", "case number", "ref"], "context": "header"}
            },
            {
                "name": "patient_last_name",
                "display_name": "Patient Last Name",
                "description": "Patient's last name",
                "field_type": "text",
                "is_required": True,
                "extraction_hints": {"keywords": ["last name", "surname"], "context": "patient_info"}
            },
            {
                "name": "patient_first_name",
                "display_name": "Patient First Name",
                "description": "Patient's first name",
                "field_type": "text",
                "is_required": True,
                "extraction_hints": {"keywords": ["first name", "given name"], "context": "patient_info"}
            },
            {
                "name": "member_id",
                "display_name": "Member ID",
                "description": "Insurance member identification number",
                "field_type": "text",
                "is_required": True,
                "validation_pattern": r"^[A-Z0-9]{6,20}$",
                "extraction_hints": {"keywords": ["member id", "member number", "id"], "context": "insurance"}
            },
            {
                "name": "date_of_birth",
                "display_name": "Date of Birth",
                "description": "Patient's date of birth",
                "field_type": "date",
                "is_required": True,
                "validation_pattern": r"^\d{1,2}/\d{1,2}/\d{4}$",
                "extraction_hints": {"keywords": ["dob", "date of birth", "birth date"], "context": "patient_info"}
            },
            {
                "name": "denial_reason",
                "display_name": "Denial Reason",
                "description": "Reason for authorization denial",
                "field_type": "text",
                "is_required": True,
                "extraction_hints": {"keywords": ["denial", "denied", "reason"], "context": "decision"}
            },
            
            # Optional fields
            {
                "name": "payer",
                "display_name": "Payer",
                "description": "Insurance payer/company name",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["payer", "insurance", "plan"], "context": "insurance"}
            },
            {
                "name": "authorization_number",
                "display_name": "Authorization Number",
                "description": "Prior authorization number",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["authorization", "auth number"], "context": "insurance"}
            },
            {
                "name": "account_number",
                "display_name": "Account Number",
                "description": "Patient account number",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["account", "acct"], "context": "patient_info"}
            },
            {
                "name": "working_drg",
                "display_name": "Working DRG",
                "description": "Diagnosis Related Group code",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["drg", "diagnosis"], "context": "medical"}
            },
            {
                "name": "third_party_reviewer",
                "display_name": "3rd Party Reviewer",
                "description": "Third party review organization",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["reviewer", "review organization"], "context": "review"}
            },
            {
                "name": "level_of_care",
                "display_name": "Level of Care",
                "description": "Required level of care",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["level of care", "care level"], "context": "medical"}
            },
            {
                "name": "service",
                "display_name": "Service",
                "description": "Medical service or procedure",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["service", "procedure"], "context": "medical"}
            },
            {
                "name": "clinical_care_guidelines",
                "display_name": "Clinical Care Guidelines",
                "description": "Applied clinical guidelines",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["guidelines", "clinical"], "context": "medical"}
            },
            {
                "name": "provider_tin",
                "display_name": "Provider TIN",
                "description": "Provider Tax Identification Number",
                "field_type": "text",
                "is_required": False,
                "validation_pattern": r"^\d{2}-\d{7}$",
                "extraction_hints": {"keywords": ["tin", "tax id"], "context": "provider"}
            },
            {
                "name": "case_manager",
                "display_name": "Case Manager",
                "description": "Assigned case manager name",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {"keywords": ["case manager", "manager"], "context": "contact"}
            },
            {
                "name": "peer_to_peer_email",
                "display_name": "Peer to Peer Email",
                "description": "Email for peer-to-peer review",
                "field_type": "email",
                "is_required": False,
                "validation_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "extraction_hints": {"keywords": ["peer", "email"], "context": "contact"}
            },
            {
                "name": "peer_to_peer_phone",
                "display_name": "Peer to Peer Phone",
                "description": "Phone number for peer-to-peer review",
                "field_type": "phone",
                "is_required": False,
                "validation_pattern": r"^\(\d{3}\) \d{3}-\d{4}$",
                "extraction_hints": {"keywords": ["peer", "phone"], "context": "contact"}
            },
            {
                "name": "peer_to_peer_fax",
                "display_name": "Peer to Peer Fax",
                "description": "Fax number for peer-to-peer review",
                "field_type": "phone",
                "is_required": False,
                "validation_pattern": r"^\(\d{3}\) \d{3}-\d{4}$",
                "extraction_hints": {"keywords": ["peer", "fax"], "context": "contact"}
            }
        ]
        
        for field_data in default_fields:
            field_def = FieldDefinition(**field_data)
            self.db.add(field_def)
        
        self.db.commit()
        logger.info(f"Initialized {len(default_fields)} default field definitions")


class ReinforcementLearningService:
    """Service for managing RL feedback and model performance tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_human_feedback(
        self,
        document_id: int,
        field_name: str,
        original_value: Optional[str],
        corrected_value: Optional[str],
        original_confidence: float,
        feedback_type: str,
        reviewer_id: str,
        model_version: str,
        ocr_context: str = None
    ) -> HumanFeedback:
        """Record human feedback for RL training"""
        
        # Calculate reward score based on feedback type
        reward_score = self._calculate_reward_score(
            feedback_type, original_value, corrected_value, original_confidence
        )
        
        feedback = HumanFeedback(
            document_id=document_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            original_confidence=original_confidence,
            feedback_type=feedback_type,
            reviewer_id=reviewer_id,
            model_version=model_version,
            ocr_context=ocr_context,
            reward_score=reward_score
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        # Update model performance metrics
        self._update_model_performance(model_version, field_name, feedback_type, reward_score)
        
        return feedback
    
    def _calculate_reward_score(
        self,
        feedback_type: str,
        original_value: Optional[str],
        corrected_value: Optional[str],
        original_confidence: float
    ) -> float:
        """Calculate reward score for RL training"""
        
        if feedback_type == "confirmation":
            # Model was correct - positive reward scaled by confidence
            return 1.0 * original_confidence
        
        elif feedback_type == "correction":
            # Model found field but value was wrong - negative reward
            if original_value and corrected_value:
                # Partial credit if values are similar
                similarity = self._calculate_similarity(original_value, corrected_value)
                return -0.5 * (1 - similarity)
            return -1.0
        
        elif feedback_type == "addition":
            # Model missed a field that human found - strong negative reward
            return -2.0
        
        elif feedback_type == "removal":
            # Model found field that shouldn't exist - negative reward scaled by confidence
            return -1.5 * original_confidence
        
        return 0.0
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (simple implementation)"""
        if not str1 or not str2:
            return 0.0
        
        # Simple character-based similarity
        str1_lower = str1.lower().strip()
        str2_lower = str2.lower().strip()
        
        if str1_lower == str2_lower:
            return 1.0
        
        # Calculate Jaccard similarity on character level
        set1 = set(str1_lower)
        set2 = set(str2_lower)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _update_model_performance(
        self,
        model_version: str,
        field_name: str,
        feedback_type: str,
        reward_score: float
    ):
        """Update model performance metrics"""
        
        # Get or create performance record
        performance = self.db.query(ModelPerformance).filter(
            ModelPerformance.model_version == model_version,
            ModelPerformance.field_name == field_name
        ).first()
        
        if not performance:
            performance = ModelPerformance(
                model_version=model_version,
                field_name=field_name
            )
            self.db.add(performance)
        
        # Update counters
        performance.total_predictions += 1
        
        if feedback_type == "confirmation":
            performance.correct_predictions += 1
        elif feedback_type == "correction":
            # Model found field but wrong value - not counted as false positive
            pass
        elif feedback_type == "addition":
            performance.false_negatives += 1
        elif feedback_type == "removal":
            performance.false_positives += 1
        
        # Update average reward
        current_total_reward = performance.avg_reward * (performance.total_predictions - 1)
        performance.avg_reward = (current_total_reward + reward_score) / performance.total_predictions
        
        # Calculate precision, recall, F1
        if performance.correct_predictions + performance.false_positives > 0:
            performance.precision = performance.correct_predictions / (
                performance.correct_predictions + performance.false_positives
            )
        
        if performance.correct_predictions + performance.false_negatives > 0:
            performance.recall = performance.correct_predictions / (
                performance.correct_predictions + performance.false_negatives
            )
        
        if performance.precision + performance.recall > 0:
            performance.f1_score = 2 * (performance.precision * performance.recall) / (
                performance.precision + performance.recall
            )
        
        performance.last_updated = datetime.utcnow()
        self.db.commit()
    
    def get_model_performance(self, model_version: str = None) -> List[ModelPerformance]:
        """Get model performance metrics"""
        query = self.db.query(ModelPerformance)
        if model_version:
            query = query.filter(ModelPerformance.model_version == model_version)
        return query.all()
    
    def get_feedback_for_training(
        self,
        model_version: str = None,
        field_name: str = None,
        limit: int = 1000
    ) -> List[HumanFeedback]:
        """Get human feedback data for RL training"""
        query = self.db.query(HumanFeedback)
        
        if model_version:
            query = query.filter(HumanFeedback.model_version == model_version)
        if field_name:
            query = query.filter(HumanFeedback.field_name == field_name)
        
        return query.order_by(HumanFeedback.review_timestamp.desc()).limit(limit).all()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        total_feedback = self.db.query(HumanFeedback).count()
        avg_reward = self.db.query(HumanFeedback).with_entities(
            self.db.func.avg(HumanFeedback.reward_score)
        ).scalar() or 0.0
        
        feedback_types = self.db.query(
            HumanFeedback.feedback_type,
            self.db.func.count(HumanFeedback.id)
        ).group_by(HumanFeedback.feedback_type).all()
        
        return {
            "total_feedback_records": total_feedback,
            "average_reward": float(avg_reward),
            "feedback_distribution": {ft: count for ft, count in feedback_types}
        }