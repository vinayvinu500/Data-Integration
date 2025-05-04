from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, status
from typing import List, Dict, Any, Optional
import uuid

from app.core.config import settings
from app.services.storage_service import StorageService
from app.services.transform_service import TransformService
from app.schemas.request import TransformRequest, BatchTransformRequest, UploadMappingRequest
from app.schemas.response import TransformResponse, BatchTransformResponse, MappingResponse
from app.api.dependencies import get_storage_service, get_transform_service
from app.utils.mapping_parser import load_mapping_from_excel, convert_mapping_to_json

router = APIRouter()

@router.post("/file", response_model=TransformResponse, status_code=status.HTTP_202_ACCEPTED)
async def transform_file(
    request: TransformRequest,
    background_tasks: BackgroundTasks,
    storage_service: StorageService = Depends(get_storage_service),
    transform_service: TransformService = Depends(get_transform_service)
):
    """
    Transform a single XML file to BYDM JSON format.
    
    The transformation is executed as a background task.
    """
    try:
        # Check if source file exists
        files = storage_service.list_files(request.source_file)
        if not request.source_file in files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file {request.source_file} not found"
            )
        
        # Generate a job ID
        job_id = f"job-{uuid.uuid4()}"
        
        # Use background task for processing
        background_tasks.add_task(
            transform_service.process_file,
            request.source_file,
            request.config_path,
            request.template_path
        )
        
        return {
            "status": "accepted",
            "message": f"Transformation of {request.source_file} started",
            "job_id": job_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start transformation: {str(e)}"
        )

@router.post("/batch", response_model=BatchTransformResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_transform(
    request: BatchTransformRequest,
    background_tasks: BackgroundTasks,
    storage_service: StorageService = Depends(get_storage_service),
    transform_service: TransformService = Depends(get_transform_service)
):
    """
    Transform multiple XML files in batch mode.
    
    The batch transformation is executed as a background task.
    """
    try:
        # Check if source folder exists and contains files
        files = storage_service.list_files(request.source_folder)
        xml_files = [f for f in files if f.endswith('.xml')]
        
        if not xml_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No XML files found in {request.source_folder}"
            )
        
        # Generate a job ID
        job_id = f"batch-{uuid.uuid4()}"
        
        # Use background task for processing
        background_tasks.add_task(
            transform_service.batch_process,
            request.source_folder,
            request.config_path,
            request.template_path
        )
        
        return {
            "status": "accepted",
            "message": f"Batch transformation of {len(xml_files)} files in {request.source_folder} started",
            "job_id": job_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch transformation: {str(e)}"
        )

@router.post("/mapping/upload", response_model=MappingResponse)
async def upload_mapping(
    sheet_name: str = "Data Mapping",
    file: UploadFile = File(...),
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Upload and process a mapping Excel sheet.
    
    The Excel sheet is parsed and converted to a JSON mapping configuration.
    """
    try:
        # Read the Excel file
        contents = await file.read()
        
        # Parse the mapping sheet
        mapping_rules = load_mapping_from_excel(contents, sheet_name)
        
        # Convert to structured JSON
        mapping_json = convert_mapping_to_json(mapping_rules)
        
        # Save to MinIO
        file_name = file.filename.replace(' ', '_').replace('.xlsx', '').replace('.xls', '')
        json_path = f"{settings.MAPPINGS_FOLDER}/{file_name}.json"
        saved_path = storage_service.save_json(mapping_json, json_path)
        
        return {
            "status": "success",
            "mapping_file": saved_path,
            "rule_count": len(mapping_rules)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process mapping sheet: {str(e)}"
        )