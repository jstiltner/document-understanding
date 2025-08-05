import logging
from typing import Dict, Any, List, Optional
import openai
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Service for Azure OpenAI integration"""
    
    def __init__(self):
        # Azure OpenAI configuration
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # Model deployments
        self.gpt4_deployment = os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT", "gpt-4")
        self.gpt35_deployment = os.getenv("AZURE_OPENAI_GPT35_DEPLOYMENT", "gpt-35-turbo")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        
        # Initialize client
        self.client = None
        self.enabled = False
        
        if self.azure_endpoint and self.api_key:
            try:
                self.client = AzureOpenAI(
                    azure_endpoint=self.azure_endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version
                )
                self.enabled = True
                logger.info("Azure OpenAI service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        else:
            logger.warning("Azure OpenAI not configured - missing endpoint or API key")
    
    def extract_fields(self, ocr_text: str, field_definitions: List[Dict], model: str = None) -> Dict[str, Any]:
        """
        Extract fields from OCR text using Azure OpenAI
        
        Args:
            ocr_text: Text extracted from OCR
            field_definitions: List of field definitions to extract
            model: Model deployment to use (gpt-4 or gpt-35-turbo)
            
        Returns:
            Dictionary containing extracted fields and metadata
        """
        if not self.enabled:
            raise ValueError("Azure OpenAI service not configured")
        
        try:
            # Select model deployment
            deployment = model or self.gpt4_deployment
            
            # Create extraction prompt
            prompt = self._create_extraction_prompt(ocr_text, field_definitions)
            
            # Call Azure OpenAI
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from medical documents. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            
            # Parse response
            extracted_data = self._parse_response(response, field_definitions)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_data, field_definitions)
            
            return {
                'extracted_fields': extracted_data,
                'confidence_scores': confidence_scores,
                'overall_confidence': confidence_scores.get('overall', 0.0),
                'requires_review': self._requires_review(extracted_data, confidence_scores, field_definitions),
                'provider': 'azure_openai',
                'model': deployment,
                'model_version': f"azure_openai_{deployment}_v1.0",
                'processing_time': processing_time,
                'token_usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI field extraction failed: {str(e)}")
            return {
                'extracted_fields': {},
                'confidence_scores': {},
                'overall_confidence': 0.0,
                'requires_review': True,
                'provider': 'azure_openai',
                'model': deployment,
                'model_version': f"azure_openai_{deployment}_v1.0",
                'error': str(e)
            }
    
    def _create_extraction_prompt(self, ocr_text: str, field_definitions: List[Dict]) -> str:
        """Create extraction prompt for Azure OpenAI"""
        
        # Build field descriptions
        required_fields = []
        optional_fields = []
        
        for field_def in field_definitions:
            field_name = field_def.get('display_name', field_def.get('name', ''))
            field_desc = field_def.get('description', '')
            field_type = field_def.get('field_type', 'text')
            is_required = field_def.get('is_required', False)
            
            field_info = f"- {field_name}"
            if field_desc:
                field_info += f": {field_desc}"
            if field_type != 'text':
                field_info += f" (type: {field_type})"
            
            if is_required:
                required_fields.append(field_info)
            else:
                optional_fields.append(field_info)
        
        # Build extraction hints
        hints = []
        for field_def in field_definitions:
            if field_def.get('extraction_hints'):
                field_name = field_def.get('display_name', field_def.get('name', ''))
                extraction_hints = field_def['extraction_hints']
                
                if 'keywords' in extraction_hints:
                    keywords = ', '.join(extraction_hints['keywords'])
                    hints.append(f"- {field_name}: Look for keywords like '{keywords}'")
        
        prompt = f"""You are an expert at reading insurance authorization and denial documents. Extract the following fields from the OCR text and return a JSON object with only the found fields.

Required Fields (must be found for successful processing):
{chr(10).join(required_fields)}

Optional Fields (extract if present):
{chr(10).join(optional_fields)}

Extraction Hints:
{chr(10).join(hints) if hints else "Use context clues and common document patterns."}

Instructions:
1. Return ONLY valid JSON - no explanations or additional text
2. Use exact field names as shown above
3. If a field is missing or cannot be found, omit it from the JSON
4. For dates, use MM/DD/YYYY format if possible
5. For phone numbers, use (XXX) XXX-XXXX format if possible
6. For email addresses, ensure proper email format
7. Look for variations in field names and synonyms

OCR Text to analyze:
{ocr_text}

JSON Response:"""
        
        return prompt
    
    def _parse_response(self, response, field_definitions: List[Dict]) -> Dict[str, Any]:
        """Parse Azure OpenAI response"""
        
        try:
            content = response.choices[0].message.content
            
            # Clean and parse JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            extracted_data = json.loads(content)
            
            # Map display names to internal names
            field_mapping = {}
            for field_def in field_definitions:
                display_name = field_def.get('display_name', field_def.get('name', ''))
                internal_name = field_def.get('name', display_name)
                field_mapping[display_name] = internal_name
            
            # Convert to internal field names
            validated_data = {}
            for key, value in extracted_data.items():
                internal_name = field_mapping.get(key, key.lower().replace(' ', '_'))
                validated_data[internal_name] = value
            
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Azure OpenAI JSON response: {str(e)}")
            logger.error(f"Raw response: {response.choices[0].message.content}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing Azure OpenAI response: {str(e)}")
            return {}
    
    def _calculate_confidence_scores(self, extracted_data: Dict[str, Any], field_definitions: List[Dict]) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields"""
        
        confidence_scores = {}
        
        for field_name, value in extracted_data.items():
            if not value or str(value).strip() == "":
                confidence_scores[field_name] = 0.0
            else:
                # Base confidence for Azure OpenAI
                confidence = 0.85  # Higher base confidence for structured output
                
                # Find field definition
                field_def = None
                for fd in field_definitions:
                    if fd.get('name') == field_name or fd.get('display_name') == field_name:
                        field_def = fd
                        break
                
                if field_def:
                    field_type = field_def.get('field_type', 'text')
                    validation_pattern = field_def.get('validation_pattern')
                    
                    # Adjust confidence based on field type validation
                    if field_type == "date" and self._is_valid_date(str(value)):
                        confidence = 0.9
                    elif field_type == "email" and self._is_valid_email(str(value)):
                        confidence = 0.9
                    elif field_type == "phone" and self._is_valid_phone(str(value)):
                        confidence = 0.9
                    elif validation_pattern and self._matches_pattern(str(value), validation_pattern):
                        confidence = 0.9
                
                # Adjust based on value length and content
                if len(str(value)) < 2:
                    confidence = 0.6
                elif len(str(value)) > 100:
                    confidence = 0.8  # Very long values might be less accurate
                
                confidence_scores[field_name] = confidence
        
        # Calculate overall confidence
        if confidence_scores:
            # Get required field names
            required_fields = [fd.get('name', fd.get('display_name', '')) for fd in field_definitions if fd.get('is_required')]
            
            # Weight required fields more heavily
            required_scores = [confidence_scores.get(field, 0.0) for field in required_fields if field in confidence_scores]
            all_scores = list(confidence_scores.values())
            
            if required_scores:
                required_avg = sum(required_scores) / len(required_scores)
                all_avg = sum(all_scores) / len(all_scores)
                overall_confidence = (required_avg * 0.8) + (all_avg * 0.2)
            else:
                overall_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            confidence_scores['overall'] = overall_confidence
        else:
            confidence_scores['overall'] = 0.0
        
        return confidence_scores
    
    def _requires_review(self, extracted_data: Dict[str, Any], confidence_scores: Dict[str, float], field_definitions: List[Dict]) -> bool:
        """Determine if document requires manual review"""
        
        # Get required field names
        required_fields = [fd.get('name', fd.get('display_name', '')) for fd in field_definitions if fd.get('is_required')]
        
        # Check if all required fields are present
        missing_required = [field for field in required_fields if field not in extracted_data or not extracted_data[field]]
        
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
        
        for field_name in required_fields:
            if field_name in confidence_scores and confidence_scores[field_name] < required_threshold:
                return True
        
        return False
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Simple date validation"""
        import re
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}'
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False
    
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
    
    def get_available_models(self) -> List[str]:
        """Get available Azure OpenAI model deployments"""
        
        models = []
        if self.gpt4_deployment:
            models.append(self.gpt4_deployment)
        if self.gpt35_deployment:
            models.append(self.gpt35_deployment)
        
        return models
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings using Azure OpenAI"""
        
        if not self.enabled:
            raise ValueError("Azure OpenAI service not configured")
        
        try:
            response = self.client.embeddings.create(
                model=self.embedding_deployment,
                input=texts
            )
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            logger.error(f"Azure OpenAI embedding creation failed: {str(e)}")
            raise
    
    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured"""
        return self.enabled
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get Azure OpenAI configuration status"""
        
        return {
            "enabled": self.enabled,
            "endpoint": bool(self.azure_endpoint),
            "api_key": bool(self.api_key),
            "api_version": self.api_version,
            "deployments": {
                "gpt4": self.gpt4_deployment,
                "gpt35": self.gpt35_deployment,
                "embedding": self.embedding_deployment
            }
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Azure OpenAI connection"""
        
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Azure OpenAI not configured"
            }
        
        try:
            # Test with a simple completion
            response = self.client.chat.completions.create(
                model=self.gpt35_deployment,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            return {
                "status": "connected",
                "message": "Azure OpenAI connection successful",
                "model": self.gpt35_deployment,
                "response_id": response.id
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Azure OpenAI connection failed: {str(e)}"
            }