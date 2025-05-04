from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TransformResponse(BaseModel):
    """
    Response model for transformation requests.
    """
    status: str = Field(..., description="Status of the transformation request")
    message: str = Field(..., description="Descriptive message")
    job_id: Optional[str] = Field(None, description="Job identifier for tracking")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "accepted",
                "message": "Transformation of source/Location.xml started",
                "job_id": "job-Location.xml"
            }
        }
    }

class BatchTransformResponse(BaseModel):
    """
    Response model for batch transformation requests.
    """
    status: str = Field(..., description="Status of the batch transformation request")
    message: str = Field(..., description="Descriptive message")
    job_id: Optional[str] = Field(None, description="Job identifier for tracking")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "accepted",
                "message": "Batch transformation of files in source/ started",
                "job_id": "batch-source"
            }
        }
    }

class MappingResponse(BaseModel):
    """
    Response model for mapping configuration operations.
    """
    status: str = Field(..., description="Status of the operation")
    mapping_file: Optional[str] = Field(None, description="Path to the saved mapping file")
    rule_count: Optional[int] = Field(None, description="Number of mapping rules extracted")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "mapping_file": "mappings/Location.json",
                "rule_count": 25
            }
        }
    }

class TransformResultResponse(BaseModel):
    """
    Response model for transformation result.
    """
    source_file: str = Field(..., description="Path to the source file")
    status: str = Field(..., description="Status of the transformation")
    output_file: Optional[str] = Field(None, description="Path to the output file if successful")
    log_file: Optional[str] = Field(None, description="Path to the log file")
    error: Optional[str] = Field(None, description="Error message if transformation failed")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_file": "source/Location.xml",
                "status": "success",
                "output_file": "target/Location_20250504_123456.json",
                "log_file": "logs/transform_20250504_123456.log",
                "error": None
            }
        }
    }

class BatchResultResponse(BaseModel):
    """
    Response model for batch transformation results.
    """
    results: List[TransformResultResponse] = Field(..., description="List of transformation results")
    success_count: int = Field(..., description="Number of successful transformations")
    failure_count: int = Field(..., description="Number of failed transformations")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "source_file": "source/Location1.xml",
                        "status": "success",
                        "output_file": "target/Location1_20250504_123456.json",
                        "log_file": "logs/transform_20250504_123456.log",
                        "error": None
                    },
                    {
                        "source_file": "source/Location2.xml",
                        "status": "failed",
                        "output_file": None,
                        "log_file": "logs/transform_20250504_123457.log",
                        "error": "Invalid XML format"
                    }
                ],
                "success_count": 1,
                "failure_count": 1
            }
        }
    }