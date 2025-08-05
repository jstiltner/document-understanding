from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import os
import json
import base64
from datetime import datetime
import tempfile

from database.database import get_db
from database.models import User, Document, FieldDefinition
from services.llm_service import LLMService
from services.ocr_service import OCRService
from services.field_service import FieldDefinitionService
from services.azure_auth_service import AzureEntraIDService
from auth.dependencies import dev_mode_only, get_dev_user

router = APIRouter(
    prefix="/dev",
    tags=["Development"],
    dependencies=[Depends(dev_mode_only)]
)

@router.get("/test-llm-providers")
async def test_llm_providers(db: Session = Depends(get_db)):
    """
    Test all configured LLM providers with a simple extraction task.
    
    Returns the results from each provider for comparison.
    """
    llm_service = LLMService(db)
    
    # Sample OCR text for testing
    sample_text = """
    AUTHORIZATION NOTICE
    
    Patient Name: John Smith
    Member ID: AB12345678
    Date of Birth: 01/15/1980
    
    Authorization Number: AUTH-2024-001
    Service: Physical Therapy
    Provider: ABC Medical Center
    
    Status: APPROVED
    Effective Date: 01/01/2024
    """
    
    results = {}
    providers = llm_service.get_available_providers()
    
    for provider in providers:
        try:
            models = llm_service.get_available_models(provider)
            if models:
                model = models[0]  # Use first available model
                result = llm_service.extract_fields(sample_text, provider, model)
                results[provider] = {
                    "model": model,
                    "success": True,
                    "extracted_fields": result.get("extracted_fields", {}),
                    "confidence_scores": result.get("confidence_scores", {}),
                    "processing_time": result.get("processing_time", 0),
                    "requires_review": result.get("requires_review", False)
                }
            else:
                results[provider] = {
                    "success": False,
                    "error": "No models available"
                }
        except Exception as e:
            results[provider] = {
                "success": False,
                "error": str(e)
            }
    
    return {
        "sample_text": sample_text,
        "providers_tested": len(providers),
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/test-ocr")
async def test_ocr(
    file: UploadFile = File(...),
    engine: str = Form("tesseract"),
    db: Session = Depends(get_db)
):
    """
    Test OCR processing with different engines.
    
    Upload a document and test OCR extraction with specified engine.
    """
    if not file.content_type.startswith(('image/', 'application/pdf')):
        raise HTTPException(status_code=400, detail="Only images and PDFs are supported")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Process with specified engine
        start_time = datetime.utcnow()
        
        if engine == "tesseract":
            result = ocr_service.extract_text_tesseract(temp_file_path)
        elif engine == "easyocr":
            result = ocr_service.extract_text_easyocr(temp_file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported OCR engine")
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return {
            "filename": file.filename,
            "engine": engine,
            "processing_time": processing_time,
            "text_length": len(result.get("text", "")),
            "confidence": result.get("confidence", 0),
            "extracted_text": result.get("text", ""),
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@router.post("/test-full-pipeline")
async def test_full_pipeline(
    file: UploadFile = File(...),
    provider: str = Form("anthropic"),
    model: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Test the complete document processing pipeline.
    
    Upload a document and process it through OCR -> LLM extraction -> validation.
    """
    if not file.content_type.startswith(('image/', 'application/pdf')):
        raise HTTPException(status_code=400, detail="Only images and PDFs are supported")
    
    pipeline_results = {
        "filename": file.filename,
        "provider": provider,
        "model": model,
        "steps": {},
        "overall_success": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Step 1: OCR Processing
        ocr_service = OCRService()
        ocr_start = datetime.utcnow()
        
        ocr_result = ocr_service.extract_text_tesseract(temp_file_path)
        ocr_time = (datetime.utcnow() - ocr_start).total_seconds()
        
        pipeline_results["steps"]["ocr"] = {
            "success": True,
            "processing_time": ocr_time,
            "text_length": len(ocr_result.get("text", "")),
            "confidence": ocr_result.get("confidence", 0)
        }
        
        # Step 2: LLM Field Extraction
        if ocr_result.get("text"):
            llm_service = LLMService(db)
            llm_start = datetime.utcnow()
            
            extraction_result = llm_service.extract_fields(
                ocr_result["text"], 
                provider=provider, 
                model=model
            )
            llm_time = (datetime.utcnow() - llm_start).total_seconds()
            
            pipeline_results["steps"]["llm_extraction"] = {
                "success": not extraction_result.get("error"),
                "processing_time": llm_time,
                "extracted_fields": extraction_result.get("extracted_fields", {}),
                "confidence_scores": extraction_result.get("confidence_scores", {}),
                "overall_confidence": extraction_result.get("overall_confidence", 0),
                "requires_review": extraction_result.get("requires_review", True),
                "error": extraction_result.get("error")
            }
            
            # Step 3: Field Validation
            field_service = FieldDefinitionService(db)
            validation_start = datetime.utcnow()
            
            required_fields = field_service.get_required_fields()
            extracted_fields = extraction_result.get("extracted_fields", {})
            
            missing_required = []
            for field in required_fields:
                field_name = field.name if hasattr(field, 'name') else field
                if field_name not in extracted_fields or not extracted_fields[field_name]:
                    missing_required.append(field_name)
            
            validation_time = (datetime.utcnow() - validation_start).total_seconds()
            
            pipeline_results["steps"]["validation"] = {
                "success": len(missing_required) == 0,
                "processing_time": validation_time,
                "missing_required_fields": missing_required,
                "total_fields_extracted": len(extracted_fields),
                "required_fields_count": len(required_fields)
            }
            
            pipeline_results["overall_success"] = (
                pipeline_results["steps"]["ocr"]["success"] and
                pipeline_results["steps"]["llm_extraction"]["success"] and
                pipeline_results["steps"]["validation"]["success"]
            )
        else:
            pipeline_results["steps"]["llm_extraction"] = {
                "success": False,
                "error": "No text extracted from OCR"
            }
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return pipeline_results
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        pipeline_results["error"] = str(e)
        return pipeline_results

@router.get("/test-azure-auth")
async def test_azure_auth():
    """
    Test Azure Entra ID authentication configuration.
    
    Returns the configuration status and connection test results.
    """
    try:
        azure_auth = AzureEntraIDService(db)
        config_status = azure_auth.get_configuration_status()
        
        # Test connection if configured
        connection_test = None
        if config_status.get("configured"):
            try:
                connection_test = azure_auth.test_connection()
            except Exception as e:
                connection_test = {
                    "status": "error",
                    "message": str(e)
                }
        
        return {
            "configuration": config_status,
            "connection_test": connection_test,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/generate-test-data")
async def generate_test_data(db: Session = Depends(get_db)):
    """
    Generate sample test data for development and testing.
    
    Creates sample field definitions, business rules, and mock documents.
    """
    try:
        field_service = FieldDefinitionService(db)
        
        # Sample field definitions
        sample_fields = [
            {
                "name": "patient_name",
                "display_name": "Patient Name",
                "description": "Full name of the patient",
                "field_type": "text",
                "is_required": True,
                "validation_pattern": "^[A-Za-z\\s]+$",
                "extraction_hints": {
                    "keywords": ["patient", "name", "patient name"],
                    "context": "Usually found at the top of the document"
                }
            },
            {
                "name": "member_id",
                "display_name": "Member ID",
                "description": "Insurance member identification number",
                "field_type": "text",
                "is_required": True,
                "validation_pattern": "^[A-Z]{2}\\d{8}$",
                "extraction_hints": {
                    "keywords": ["member id", "member number", "id number"],
                    "context": "Usually alphanumeric format"
                }
            },
            {
                "name": "date_of_birth",
                "display_name": "Date of Birth",
                "description": "Patient's date of birth",
                "field_type": "date",
                "is_required": True,
                "extraction_hints": {
                    "keywords": ["date of birth", "dob", "birth date"],
                    "context": "Date format MM/DD/YYYY"
                }
            },
            {
                "name": "authorization_number",
                "display_name": "Authorization Number",
                "description": "Medical authorization reference number",
                "field_type": "text",
                "is_required": False,
                "extraction_hints": {
                    "keywords": ["authorization", "auth number", "reference"],
                    "context": "Usually starts with AUTH- or similar prefix"
                }
            }
        ]
        
        created_fields = []
        for field_data in sample_fields:
            try:
                field = field_service.create_field_definition(field_data)
                created_fields.append(field.name)
            except Exception as e:
                # Field might already exist
                pass
        
        # Sample OCR text for testing
        sample_documents = [
            {
                "filename": "sample_authorization.pdf",
                "ocr_text": """
                MEDICAL AUTHORIZATION NOTICE
                
                Patient Information:
                Patient Name: Jane Doe
                Member ID: AB12345678
                Date of Birth: 03/15/1985
                
                Authorization Details:
                Authorization Number: AUTH-2024-001
                Service: Physical Therapy
                Provider: XYZ Medical Center
                
                Status: APPROVED
                Effective Date: 01/01/2024
                Expiration Date: 12/31/2024
                """,
                "document_type": "authorization"
            },
            {
                "filename": "sample_denial.pdf",
                "ocr_text": """
                CLAIM DENIAL NOTICE
                
                Patient: Robert Johnson
                Member ID: CD87654321
                DOB: 07/22/1970
                
                Claim Information:
                Claim Number: CLM-2024-002
                Service Date: 02/15/2024
                Provider: ABC Hospital
                
                DENIAL REASON: Prior authorization required
                Appeal Deadline: 03/15/2024
                """,
                "document_type": "denial"
            }
        ]
        
        return {
            "message": "Test data generated successfully",
            "created_fields": created_fields,
            "sample_documents": len(sample_documents),
            "field_definitions": sample_fields,
            "sample_ocr_texts": sample_documents,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test data: {str(e)}")

@router.get("/debug-info")
async def get_debug_info(db: Session = Depends(get_db)):
    """
    Get comprehensive debug information about the system state.
    
    Returns environment variables, service status, and configuration details.
    """
    try:
        # Environment variables (sanitized)
        env_vars = {
            "DEVELOPMENT_MODE": os.getenv("DEVELOPMENT_MODE", "false"),
            "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
            "REDIS_URL": bool(os.getenv("REDIS_URL")),
            "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            "AZURE_OPENAI_API_KEY": bool(os.getenv("AZURE_OPENAI_API_KEY")),
            "AZURE_CLIENT_ID": bool(os.getenv("AZURE_CLIENT_ID")),
            "AZURE_TENANT_ID": bool(os.getenv("AZURE_TENANT_ID")),
            "DEFAULT_LLM_PROVIDER": os.getenv("DEFAULT_LLM_PROVIDER", "anthropic"),
            "DEFAULT_LLM_MODEL": os.getenv("DEFAULT_LLM_MODEL", "claude-3-sonnet-20240229")
        }
        
        # Service status
        llm_service = LLMService(db)
        provider_status = llm_service.get_provider_status()
        
        # Database info
        try:
            db.execute("SELECT 1")
            db_status = "connected"
            
            # Count records in key tables
            table_counts = {}
            try:
                from database.models import User, Document, FieldDefinition
                table_counts["users"] = db.query(User).count()
                table_counts["documents"] = db.query(Document).count()
                table_counts["field_definitions"] = db.query(FieldDefinition).count()
            except Exception:
                table_counts = {"error": "Could not count records"}
                
        except Exception as e:
            db_status = f"error: {str(e)}"
            table_counts = {}
        
        # Field definitions
        field_service = FieldDefinitionService(db)
        try:
            field_definitions = field_service.get_all_fields()
            field_summary = {
                "total": len(field_definitions),
                "required": len([f for f in field_definitions if f.is_required]),
                "optional": len([f for f in field_definitions if not f.is_required])
            }
        except Exception as e:
            field_summary = {"error": str(e)}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": env_vars,
            "database": {
                "status": db_status,
                "table_counts": table_counts
            },
            "llm_providers": provider_status,
            "field_definitions": field_summary,
            "system_info": {
                "python_version": os.sys.version,
                "working_directory": os.getcwd(),
                "temp_directory": tempfile.gettempdir()
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/reset-test-data")
async def reset_test_data(
    confirm: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Reset test data (WARNING: This will delete test records).
    
    Use with caution - only for development environments.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must confirm reset by setting confirm=true"
        )
    
    try:
        # Only allow in development mode
        if os.getenv("DEVELOPMENT_MODE", "false").lower() != "true":
            raise HTTPException(
                status_code=403,
                detail="Reset only allowed in development mode"
            )
        
        # Reset field definitions (keep only defaults)
        field_service = FieldDefinitionService(db)
        
        # Get all fields and delete non-default ones
        all_fields = field_service.get_all_fields()
        deleted_fields = []
        
        for field in all_fields:
            # Keep essential fields, delete test fields
            if field.name.startswith("test_") or field.name in ["sample_field", "debug_field"]:
                try:
                    db.delete(field)
                    deleted_fields.append(field.name)
                except Exception:
                    pass
        
        db.commit()
        
        return {
            "message": "Test data reset completed",
            "deleted_fields": deleted_fields,
            "timestamp": datetime.utcnow().isoformat(),
            "warning": "This operation cannot be undone"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")