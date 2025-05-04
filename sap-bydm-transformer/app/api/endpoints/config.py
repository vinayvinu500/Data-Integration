from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.core.config import settings
from app.services.storage_service import StorageService
from app.api.dependencies import get_storage_service

router = APIRouter()

@router.get("/mappings", response_model=List[str])
async def list_mappings(
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    List all available mapping configurations.
    """
    try:
        mapping_files = storage_service.list_files(settings.MAPPINGS_FOLDER)
        return [f for f in mapping_files if f.endswith('.json')]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list mappings: {str(e)}"
        )

@router.get("/templates", response_model=List[str])
async def list_templates(
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    List all available BYDM templates.
    """
    try:
        template_files = storage_service.list_files(settings.TEMPLATE_FOLDER)
        return [f for f in template_files if f.endswith('.json')]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )

@router.get("/sources", response_model=List[str])
async def list_sources(
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    List all available source XML files.
    """
    try:
        source_files = storage_service.list_files(settings.SOURCE_FOLDER)
        return [f for f in source_files if f.endswith('.xml')]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sources: {str(e)}"
        )

@router.get("/mapping/{mapping_file}", response_model=Dict[str, Any])
async def get_mapping(
    mapping_file: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Get a specific mapping configuration.
    """
    try:
        # Add folder prefix if not included
        if not mapping_file.startswith(settings.MAPPINGS_FOLDER):
            mapping_path = f"{settings.MAPPINGS_FOLDER}/{mapping_file}"
        else:
            mapping_path = mapping_file
            
        # Add .json extension if not included
        if not mapping_path.endswith('.json'):
            mapping_path += '.json'
            
        return storage_service.load_json(mapping_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapping file not found or invalid: {str(e)}"
        )