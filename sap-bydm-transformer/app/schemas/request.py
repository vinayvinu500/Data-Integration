from pydantic import BaseModel, Field
from typing import Optional

class TransformRequest(BaseModel):
    """
    Request model for single file transformation.
    """
    source_file: str = Field(..., description="Path to the source XML file")
    config_path: str = Field(..., description="Path to the mapping configuration file")
    template_path: str = Field(..., description="Path to the BYDM template file")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_file": "source/Location.xml",
                "config_path": "mappings/Location.json",
                "template_path": "templates/Location.json"
            }
        }
    }

class BatchTransformRequest(BaseModel):
    """
    Request model for batch file transformation.
    """
    source_folder: str = Field(..., description="Folder containing source XML files")
    config_path: str = Field(..., description="Path to the mapping configuration file")
    template_path: str = Field(..., description="Path to the BYDM template file")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_folder": "source/",
                "config_path": "mappings/Location.json",
                "template_path": "templates/Location.json"
            }
        }
    }

class UploadMappingRequest(BaseModel):
    """
    Request model for uploading mapping configuration.
    """
    sheet_name: Optional[str] = Field("Data Mapping", description="Name of the sheet containing mapping data")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sheet_name": "Data Mapping"
            }
        }
    }