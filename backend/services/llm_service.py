import os
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import openai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        
        # Initialize clients based on available API keys
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
        
        self.default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "anthropic")
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "claude-3-sonnet-20240229")
        
        # Define required and optional fields
        self.required_fields = [
            "Facility",
            "Reference Number", 
            "Patient Last Name",
            "Patient First Name",
            "Member ID",
            "Date of Birth",
            "Denial Reason"
        ]
        
        self.optional_fields = [
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
    
    def extract_fields(self, ocr_text: str, provider: str = None, model: str = None) -> Dict[str, Any]:
        """
        Extract fields from OCR text using LLM
        
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
            # Create extraction prompt
            prompt = self._create_extraction_prompt(ocr_text)
            
            # Extract using specified provider
            if provider == "anthropic" and self.anthropic_client:
                result = self._extract_with_anthropic(prompt, model)
            elif provider == "openai" and self.openai_client:
                result = self._extract_with_openai(prompt, model)
            else:
                raise ValueError(f"Provider {provider} not available or not configured")
            
            # Parse and validate results
            extracted_data = self._parse_extraction_result(result)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_data)
            
            return {
                'extracted_fields': extracted_data,
                'confidence_scores': confidence_scores,
                'overall_confidence': confidence_scores.get('overall', 0.0),
                'requires_review': self._requires_review(extracted_data, confidence_scores),
                'provider': provider,
                'model': model,
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
                'error': str(e)
            }
    
    def _create_extraction_prompt(self, ocr_text: str) -> str:
        """Create the extraction prompt for the LLM"""
        
        all_fields = self.required_fields + self.optional_fields
        fields_list = "\n".join([f"- {field}" for field in all_fields])
        
        prompt = f"""You are an expert at reading insurance authorization and denial documents in a medical workflow. Given OCR text from a multi-page faxed PDF, extract the following fields if present, and output a JSON object with only the found fields:

Required Fields (must be found for successful processing):
{chr(10).join([f"- {field}" for field in self.required_fields])}

Optional Fields (failing to find these does not result in the record moving to the review UI screen):
{chr(10).join([f"- {field}" for field in self.optional_fields])}

Instructions:
1. If a field is missing or cannot be found, omit it from the JSON
2. Use only valid JSON output, no extra explanation
3. Be precise with field names - use exactly the names listed above
4. For dates, use MM/DD/YYYY format if possible
5. For phone numbers, use standard formatting (XXX) XXX-XXXX if possible
6. Look for variations in field names (e.g., "Patient Name" might contain both first and last name)

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
    
    def _parse_extraction_result(self, result: str) -> Dict[str, Any]:
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
            
            # Validate field names
            valid_fields = self.required_fields + self.optional_fields
            validated_data = {}
            
            for key, value in extracted_data.items():
                if key in valid_fields:
                    validated_data[key] = value
                else:
                    # Try to find close matches
                    for valid_field in valid_fields:
                        if key.lower().replace(' ', '') == valid_field.lower().replace(' ', ''):
                            validated_data[valid_field] = value
                            break
            
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {result}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing extraction result: {str(e)}")
            return {}
    
    def _calculate_confidence_scores(self, extracted_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields"""
        confidence_scores = {}
        
        # Simple heuristic-based confidence scoring
        for field, value in extracted_data.items():
            if not value or str(value).strip() == "":
                confidence_scores[field] = 0.0
            else:
                # Base confidence on field completeness and format
                confidence = 0.8  # Base confidence
                
                # Adjust based on field type and format
                if field in ["Date of Birth"] and self._is_valid_date(str(value)):
                    confidence = 0.9
                elif field in ["Member ID", "Reference Number"] and len(str(value)) > 3:
                    confidence = 0.9
                elif field in ["Patient First Name", "Patient Last Name"] and len(str(value)) > 1:
                    confidence = 0.85
                elif len(str(value)) < 2:
                    confidence = 0.5
                
                confidence_scores[field] = confidence
        
        # Calculate overall confidence
        if confidence_scores:
            # Weight required fields more heavily
            required_scores = [confidence_scores.get(field, 0.0) for field in self.required_fields if field in confidence_scores]
            optional_scores = [confidence_scores.get(field, 0.0) for field in self.optional_fields if field in confidence_scores]
            
            if required_scores:
                required_avg = sum(required_scores) / len(required_scores)
                optional_avg = sum(optional_scores) / len(optional_scores) if optional_scores else 0.0
                overall_confidence = (required_avg * 0.8) + (optional_avg * 0.2)
            else:
                overall_confidence = 0.0
            
            confidence_scores['overall'] = overall_confidence
        else:
            confidence_scores['overall'] = 0.0
        
        return confidence_scores
    
    def _requires_review(self, extracted_data: Dict[str, Any], confidence_scores: Dict[str, float]) -> bool:
        """Determine if document requires manual review"""
        
        # Check if all required fields are present
        missing_required = []
        for field in self.required_fields:
            if field not in extracted_data or not extracted_data[field]:
                missing_required.append(field)
        
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
        
        for field in self.required_fields:
            if field in confidence_scores and confidence_scores[field] < required_threshold:
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