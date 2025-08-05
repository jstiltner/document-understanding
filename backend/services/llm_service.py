import os
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import openai
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .field_service import FieldDefinitionService

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, db: Session = None):
        self.anthropic_client = None
        self.openai_client = None
        self.db = db
        self.field_service = FieldDefinitionService(db) if db else None
        
        # Initialize clients based on available API keys
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
        
        self.default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "anthropic")
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "claude-3-sonnet-20240229")
        
        # Model version for RL tracking
        self.model_version = f"{self.default_provider}_{self.default_model}_v1.0"
    
    def extract_fields(self, ocr_text: str, provider: str = None, model: str = None) -> Dict[str, Any]:
        """
        Extract fields from OCR text using LLM with configurable field definitions
        
        Args:
            ocr_text: Text extracted from OCR
            provider: LLM provider to use (anthropic, openai)
            model: Specific model to use
            
        Returns:
            Dictionary containing extracted fields and metadata
        """
        provider = provider or self.default_provider
        model = model or self.default_model
        
        try:
            # Get field definitions from database
            if self.field_service:
                required_fields = self.field_service.get_required_fields()
                optional_fields = self.field_service.get_optional_fields()
            else:
                # Fallback to hardcoded fields if no database connection
                required_fields = self._get_fallback_required_fields()
                optional_fields = self._get_fallback_optional_fields()
            
            # Create extraction prompt with configurable fields
            prompt = self._create_extraction_prompt(ocr_text, required_fields, optional_fields)
            
            # Extract using specified provider
            if provider == "anthropic" and self.anthropic_client:
                result = self._extract_with_anthropic(prompt, model)
            elif provider == "openai" and self.openai_client:
                result = self._extract_with_openai(prompt, model)
            else:
                raise ValueError(f"Provider {provider} not available or not configured")
            
            # Parse and validate results
            extracted_data = self._parse_extraction_result(result, required_fields + optional_fields)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_data, required_fields)
            
            return {
                'extracted_fields': extracted_data,
                'confidence_scores': confidence_scores,
                'overall_confidence': confidence_scores.get('overall', 0.0),
                'requires_review': self._requires_review(extracted_data, confidence_scores, required_fields),
                'provider': provider,
                'model': model,
                'model_version': self.model_version,
                'raw_response': result
            }
            
        except Exception as e:
            logger.error(f"Field extraction failed: {str(e)}")
            return {
                'extracted_fields': {},
                'confidence_scores': {},
                'overall_confidence': 0.0,
                'requires_review': True,
                'provider': provider,
                'model': model,
                'model_version': self.model_version,
                'error': str(e)
            }
    
    def _create_extraction_prompt(self, ocr_text: str, required_fields: List, optional_fields: List) -> str:
        """Create the extraction prompt for the LLM using configurable field definitions"""
        
        # Build required fields section
        required_section = []
        for field in required_fields:
            field_name = field.display_name if hasattr(field, 'display_name') else field
            field_desc = field.description if hasattr(field, 'description') else ""
            if field_desc:
                required_section.append(f"- {field_name}: {field_desc}")
            else:
                required_section.append(f"- {field_name}")
        
        # Build optional fields section
        optional_section = []
        for field in optional_fields:
            field_name = field.display_name if hasattr(field, 'display_name') else field
            field_desc = field.description if hasattr(field, 'description') else ""
            if field_desc:
                optional_section.append(f"- {field_name}: {field_desc}")
            else:
                optional_section.append(f"- {field_name}")
        
        # Build extraction hints
        hints_section = []
        all_fields = required_fields + optional_fields
        for field in all_fields:
            if hasattr(field, 'extraction_hints') and field.extraction_hints:
                hints = field.extraction_hints
                field_name = field.display_name if hasattr(field, 'display_name') else field
                if 'keywords' in hints:
                    keywords = ', '.join(hints['keywords'])
                    hints_section.append(f"- {field_name}: Look for keywords like '{keywords}'")
        
        prompt = f"""You are an expert at reading insurance authorization and denial documents in a medical workflow. Given OCR text from a multi-page faxed PDF, extract the following fields if present, and output a JSON object with only the found fields:

Required Fields (must be found for successful processing):
{chr(10).join(required_section)}

Optional Fields (failing to find these does not result in the record moving to the review UI screen):
{chr(10).join(optional_section)}

Extraction Hints:
{chr(10).join(hints_section) if hints_section else "Use context clues and common document patterns."}

Instructions:
1. If a field is missing or cannot be found, omit it from the JSON
2. Use only valid JSON output, no extra explanation
3. Be precise with field names - use exactly the display names listed above
4. For dates, use MM/DD/YYYY format if possible
5. For phone numbers, use standard formatting (XXX) XXX-XXXX if possible
6. For email addresses, ensure proper email format
7. Look for variations in field names and synonyms
8. Consider the context and location of information in the document

OCR Text to analyze:
{ocr_text}

Output only valid JSON:"""
        
        return prompt
    
    def _extract_with_anthropic(self, prompt: str, model: str) -> str:
        """Extract using Anthropic Claude"""
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def _extract_with_openai(self, prompt: str, model: str) -> str:
        """Extract using OpenAI GPT"""
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from medical documents. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _parse_extraction_result(self, result: str, field_definitions: List) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        try:
            # Clean the response - remove any markdown formatting
            cleaned_result = result.strip()
            if cleaned_result.startswith('```json'):
                cleaned_result = cleaned_result[7:]
            if cleaned_result.endswith('```'):
                cleaned_result = cleaned_result[:-3]
            cleaned_result = cleaned_result.strip()
            
            # Parse JSON
            extracted_data = json.loads(cleaned_result)
            
            # Build valid field names from definitions
            valid_fields = []
            field_name_mapping = {}
            
            for field_def in field_definitions:
                if hasattr(field_def, 'display_name'):
                    display_name = field_def.display_name
                    internal_name = field_def.name
                    valid_fields.append(display_name)
                    field_name_mapping[display_name] = internal_name
                else:
                    # Fallback for string fields
                    valid_fields.append(field_def)
                    field_name_mapping[field_def] = field_def.lower().replace(' ', '_')
            
            validated_data = {}
            
            for key, value in extracted_data.items():
                if key in valid_fields:
                    internal_name = field_name_mapping.get(key, key)
                    validated_data[internal_name] = value
                else:
                    # Try to find close matches
                    for valid_field in valid_fields:
                        if key.lower().replace(' ', '') == valid_field.lower().replace(' ', ''):
                            internal_name = field_name_mapping.get(valid_field, valid_field)
                            validated_data[internal_name] = value
                            break
            
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {result}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing extraction result: {str(e)}")
            return {}
    
    def _calculate_confidence_scores(self, extracted_data: Dict[str, Any], required_fields: List) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields"""
        confidence_scores = {}
        
        # Simple heuristic-based confidence scoring
        for field, value in extracted_data.items():
            if not value or str(value).strip() == "":
                confidence_scores[field] = 0.0
            else:
                # Base confidence on field completeness and format
                confidence = 0.8  # Base confidence
                
                # Get field definition for validation
                field_def = None
                if self.field_service:
                    field_def = self.field_service.get_field_by_name(field)
                
                if field_def and hasattr(field_def, 'field_type'):
                    # Adjust confidence based on field type validation
                    if field_def.field_type == "date" and self._is_valid_date(str(value)):
                        confidence = 0.9
                    elif field_def.field_type == "email" and self._is_valid_email(str(value)):
                        confidence = 0.9
                    elif field_def.field_type == "phone" and self._is_valid_phone(str(value)):
                        confidence = 0.9
                    elif field_def.validation_pattern and self._matches_pattern(str(value), field_def.validation_pattern):
                        confidence = 0.9
                else:
                    # Fallback validation
                    if "date" in field.lower() and self._is_valid_date(str(value)):
                        confidence = 0.9
                    elif field in ["member_id", "reference_number"] and len(str(value)) > 3:
                        confidence = 0.9
                    elif "name" in field.lower() and len(str(value)) > 1:
                        confidence = 0.85
                
                if len(str(value)) < 2:
                    confidence = 0.5
                
                confidence_scores[field] = confidence
        
        # Calculate overall confidence
        if confidence_scores:
            # Get required field names
            required_field_names = []
            for field_def in required_fields:
                if hasattr(field_def, 'name'):
                    required_field_names.append(field_def.name)
                else:
                    required_field_names.append(field_def.lower().replace(' ', '_'))
            
            # Weight required fields more heavily
            required_scores = [confidence_scores.get(field, 0.0) for field in required_field_names if field in confidence_scores]
            all_scores = list(confidence_scores.values())
            
            if required_scores:
                required_avg = sum(required_scores) / len(required_scores)
                all_avg = sum(all_scores) / len(all_scores)
                overall_confidence = (required_avg * 0.8) + (all_avg * 0.2)
            else:
                overall_confidence = 0.0
            
            confidence_scores['overall'] = overall_confidence
        else:
            confidence_scores['overall'] = 0.0
        
        return confidence_scores
    
    def _requires_review(self, extracted_data: Dict[str, Any], confidence_scores: Dict[str, float], required_fields: List) -> bool:
        """Determine if document requires manual review"""
        
        # Get required field names
        required_field_names = []
        for field_def in required_fields:
            if hasattr(field_def, 'name'):
                required_field_names.append(field_def.name)
            else:
                required_field_names.append(field_def.lower().replace(' ', '_'))
        
        # Check if all required fields are present
        missing_required = []
        for field_name in required_field_names:
            if field_name not in extracted_data or not extracted_data[field_name]:
                missing_required.append(field_name)
        
        # Check confidence thresholds
        min_confidence = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.7"))
        required_threshold = float(os.getenv("REQUIRED_FIELDS_THRESHOLD", "0.8"))
        
        overall_confidence = confidence_scores.get('overall', 0.0)
        
        # Requires review if:
        # 1. Missing required fields
        # 2. Overall confidence below threshold
        # 3. Any required field has very low confidence
        if missing_required:
            return True
        
        if overall_confidence < min_confidence:
            return True
        
        for field_name in required_field_names:
            if field_name in confidence_scores and confidence_scores[field_name] < required_threshold:
                return True
        
        return False
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Simple date validation"""
        import re
        # Check for common date formats
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}'
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        providers = []
        if self.anthropic_client:
            providers.append("anthropic")
        if self.openai_client:
            providers.append("openai")
        return providers
    
    def get_available_models(self, provider: str) -> List[str]:
        """Get available models for a provider"""
        if provider == "anthropic":
            return [
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-3-opus-20240229"
            ]
        elif provider == "openai":
            return [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
        return []
    
    def _is_valid_email(self, email_str: str) -> bool:
        """Simple email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email_str.strip()))
    
    def _is_valid_phone(self, phone_str: str) -> bool:
        """Simple phone validation"""
        import re
        patterns = [
            r'^\(\d{3}\) \d{3}-\d{4}$',
            r'^\d{3}-\d{3}-\d{4}$',
            r'^\d{10}$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, phone_str.strip()):
                return True
        return False
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches regex pattern"""
        import re
        try:
            return bool(re.match(pattern, value.strip()))
        except re.error:
            return False
    
    def _get_fallback_required_fields(self) -> List[str]:
        """Fallback required fields when database is not available"""
        return [
            "Facility",
            "Reference Number",
            "Patient Last Name",
            "Patient First Name",
            "Member ID",
            "Date of Birth",
            "Denial Reason"
        ]
    
    def _get_fallback_optional_fields(self) -> List[str]:
        """Fallback optional fields when database is not available"""
        return [
            "Payer",
            "Authorization Number",
            "Account Number",
            "Working DRG",
            "3rd party reviewer",
            "Level of Care",
            "Service",
            "Clinical Care Guidelines",
            "Provider TIN",
            "Case Manager",
            "Peer to Peer email",
            "Peer to Peer phone",
            "Peer to peer fax"
        ]
    
    def get_field_definitions(self) -> Dict[str, List]:
        """Get current field definitions"""
        if self.field_service:
            required_fields = self.field_service.get_required_fields()
            optional_fields = self.field_service.get_optional_fields()
            return {
                "required": required_fields,
                "optional": optional_fields
            }
        else:
            return {
                "required": self._get_fallback_required_fields(),
                "optional": self._get_fallback_optional_fields()
            }