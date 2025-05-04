from fastapi import Depends
from typing import Annotated

from app.services.storage_service import StorageService
from app.services.transform_service import TransformService

def get_storage_service() -> StorageService:
    """
    Dependency to get an instance of the StorageService.
    
    Returns:
        StorageService instance
    """
    return StorageService()

def get_transform_service(
    storage_service: Annotated[StorageService, Depends(get_storage_service)]
) -> TransformService:
    """
    Dependency to get an instance of the TransformService.
    
    Args:
        storage_service: Storage service instance
        
    Returns:
        TransformService instance
    """
    return TransformService(storage_service)