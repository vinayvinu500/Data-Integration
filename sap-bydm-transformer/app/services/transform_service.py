import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.core.config import settings
from app.services.storage_service import StorageService
from app.utils.xml_parser import parse_xml_to_dict, extract_segments, get_field_value
from app.utils.mapping_parser import convert_mapping_to_json

logger = logging.getLogger("app")

class TransformService:
    """Service for transforming XML to JSON according to mapping rules."""
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize with a storage service.
        
        Args:
            storage_service: Service for MinIO interactions
        """
        self.storage_service = storage_service
    
    async def process_file(self, source_file_path: str, config_path: str, template_path: str) -> Tuple[str, str]:
        """
        Process a single XML file to BYDM JSON format.
        
        Args:
            source_file_path: Path to source XML file
            config_path: Path to mapping configuration
            template_path: Path to BYDM template
            
        Returns:
            Tuple of (output_path, log_path)
        """
        try:
            logger.info(f"Processing file: {source_file_path}")
            
            # Load the source XML, mapping config, and template
            xml_data = self.storage_service.load_file(source_file_path)
            config = self.storage_service.load_json(config_path)
            template = self.storage_service.load_json(template_path)
            
            # Parse XML to dictionary
            xml_dict = parse_xml_to_dict(xml_data)
            
            # Create output using template
            bydm_data = [template.copy()]
            
            # Transform data using mapping config
            await self._apply_mapping(xml_dict, config, bydm_data[0])
            
            # Generate output file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = source_file_path.split('/')[-1].replace('.xml', '')
            output_path = f"{settings.TARGET_FOLDER}/{file_name}_{timestamp}.json"
            
            # Save transformed data
            self.storage_service.save_json(bydm_data, output_path)
            
            # Save processing log
            log_content = f"Successfully processed {source_file_path} to {output_path}"
            log_path = self.storage_service.save_log(log_content)
            
            logger.info(f"Transformation completed: {source_file_path} -> {output_path}")
            return output_path, log_path
            
        except Exception as e:
            logger.error(f"Error processing file {source_file_path}: {str(e)}")
            # Save error log
            log_content = f"Error processing {source_file_path}: {str(e)}"
            log_path = self.storage_service.save_log(log_content)
            raise
    
    async def _apply_mapping(self, xml_dict: Dict[str, Any], config: Dict[str, Any], 
                          output_json: Dict[str, Any]) -> None:
        """
        Apply mapping configuration to transform XML to BYDM format.
        
        Args:
            xml_dict: Dictionary representation of XML
            config: Mapping configuration
            output_json: Output JSON being constructed
        """
        mappings = config.get("mappings", {})
        
        # Process each segment in the mapping
        for segment_name, segment_mapping in mappings.items():
            # Extract segment data from XML
            segments = extract_segments(xml_dict, segment_name)
            
            if not segments:
                logger.warning(f"Segment {segment_name} not found in XML")
                continue
                
            # Process each segment instance
            for segment in segments:
                await self._process_segment(segment, segment_mapping, output_json)
    
    async def _process_segment(self, segment: Dict[str, Any], 
                            segment_mapping: Dict[str, Any], 
                            output_json: Dict[str, Any]) -> None:
        """
        Process a single segment according to mapping rules.
        
        Args:
            segment: Segment dictionary
            segment_mapping: Mapping rules for the segment
            output_json: Output JSON being constructed
        """
        for field_name, field_mapping in segment_mapping.items():
            if isinstance(field_mapping, dict) and "target" in field_mapping:
                # Get field value from segment
                field_value = segment.get(field_name, "")
                
                # Handle special case where value is in '#text' property (common in xmltodict output)
                if isinstance(field_value, dict) and '#text' in field_value:
                    field_value = field_value['#text']
                
                if not field_value and field_value != 0:
                    # Use default value if available
                    field_value = field_mapping.get("default_value", "")
                
                # Apply transformation if specified
                transformation = field_mapping.get("transformation")
                if transformation and field_value:
                    field_value = self._apply_transformation(field_value, transformation)
                
                # Validate field value
                validation_rule = field_mapping.get("validation")
                if validation_rule:
                    field_value = self._validate_field(field_value, validation_rule, field_name)
                
                # Set value in output JSON
                if field_value is not None:
                    self._set_nested_value(output_json, field_mapping["target"], field_value)
            elif isinstance(field_mapping, dict):
                # Handle nested mapping (recursive call)
                nested_segment = segment.get(field_name, {})
                if nested_segment:
                    await self._process_segment(nested_segment, field_mapping, output_json)
    
    def _apply_transformation(self, value: str, transformation: Dict[str, Any]) -> str:
        """
        Apply transformation rule to a field value.
        
        Args:
            value: Field value to transform
            transformation: Transformation rule
            
        Returns:
            Transformed value
        """
        if not transformation:
            return value
            
        if transformation.get("type") == "MAP":
            mapping_values = transformation.get("values", {})
            return mapping_values.get(str(value), value)
            
        return value
    
    def _validate_field(self, value: Any, validation_rule: str, field_name: str) -> Optional[str]:
        """
        Validate a field value against rules.
        
        Args:
            value: Field value to validate
            validation_rule: Type of validation to apply
            field_name: Name of the field (for logging)
            
        Returns:
            Validated value or None if invalid
        """
        if value is None or value == "":
            return None
            
        # Convert to string for validation
        value = str(value).strip()
        
        if validation_rule.upper() == "NUMBER":
            # Allow decimal numbers
            if not value.replace('.', '', 1).isdigit():
                logger.warning(f"Validation failed for {field_name}: Expected NUMBER, got '{value}'")
                return None
        elif validation_rule.upper() == "TEXT":
            if not value:
                logger.warning(f"Validation failed for {field_name}: Expected TEXT, got empty string")
                return None
                
        return value
    
    def _set_nested_value(self, json_obj: Dict[str, Any], nested_key: str, value: Any) -> None:
        """
        Set a value in a nested JSON structure.
        
        Args:
            json_obj: JSON object to modify
            nested_key: Nested key path (e.g., "a.b.0.c")
            value: Value to set
        """
        keys = nested_key.split(".")
        temp = json_obj
        
        # Navigate to the correct position
        for i, key in enumerate(keys[:-1]):
            # Handle array indices
            if key.isdigit():
                key = int(key)
                # Ensure array has enough elements
                if isinstance(temp, list):
                    while len(temp) <= key:
                        temp.append({})
                    temp = temp[key]
                else:
                    # If not already a list, create a new list
                    new_temp = []
                    while len(new_temp) <= key:
                        new_temp.append({})
                    temp[keys[i-1]] = new_temp
                    temp = new_temp[key]
            else:
                # For dictionary keys
                if key not in temp or not isinstance(temp[key], (dict, list)):
                    # Create dict if key doesn't exist or isn't a container
                    if keys[i+1].isdigit():
                        # Next key is an array index, so create a list
                        temp[key] = []
                    else:
                        # Next key is a dict key, so create a dict
                        temp[key] = {}
                temp = temp[key]
        
        # Set the value at the final position
        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
            # Ensure array has enough elements
            if isinstance(temp, list):
                while len(temp) <= last_key:
                    temp.append(None)
                temp[last_key] = value
            else:
                # Convert to list if not already
                temp = []
                while len(temp) <= last_key:
                    temp.append(None)
                temp[last_key] = value
        else:
            temp[last_key] = value
    
    async def batch_process(self, source_folder: str, config_path: str, 
                         template_path: str) -> List[Dict[str, Any]]:
        """
        Process multiple XML files in batch mode.
        
        Args:
            source_folder: Folder containing XML files
            config_path: Path to mapping configuration
            template_path: Path to BYDM template
            
        Returns:
            List of processing results
        """
        results = []
        files = self.storage_service.list_files(source_folder)
        xml_files = [f for f in files if f.endswith('.xml')]
        
        logger.info(f"Starting batch processing of {len(xml_files)} XML files")
        
        # Process files in chunks to limit concurrency
        for i in range(0, len(xml_files), settings.BATCH_SIZE):
            batch = xml_files[i:i+settings.BATCH_SIZE]
            tasks = []
            
            for file_path in batch:
                task = asyncio.create_task(
                    self.process_file(file_path, config_path, template_path)
                )
                tasks.append((file_path, task))
            
            # Wait for all tasks in this batch to complete
            for file_path, task in tasks:
                try:
                    output_path, log_path = await task
                    results.append({
                        "source_file": file_path,
                        "status": "success",
                        "output_file": output_path,
                        "log_file": log_path
                    })
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results.append({
                        "source_file": file_path,
                        "status": "failed",
                        "error": str(e)
                    })
        
        logger.info(f"Batch processing completed: {len(results)} files processed")
        return results