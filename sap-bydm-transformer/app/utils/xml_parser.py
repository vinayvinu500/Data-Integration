import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import xmltodict
import logging

logger = logging.getLogger("app")

def parse_xml_to_dict(xml_data: bytes) -> Dict[str, Any]:
    """
    Parse XML data to a dictionary.
    
    Args:
        xml_data: XML content as bytes
        
    Returns:
        Dictionary representation of the XML
    """
    try:
        return xmltodict.parse(xml_data)
    except Exception as e:
        logger.error(f"Failed to parse XML: {e}")
        raise ValueError(f"Invalid XML data: {e}")

def extract_segments(xml_dict: Dict[str, Any], segment_path: str) -> List[Dict[str, Any]]:
    """
    Extract specific segments from XML dictionary.
    
    Args:
        xml_dict: Dictionary representation of XML
        segment_path: Path to the segment in the XML structure (e.g., "IDOC.E1LOC")
        
    Returns:
        List of segment dictionaries
    """
    try:
        # Split the path and navigate the dictionary
        path_parts = segment_path.split('.')
        current = xml_dict
        
        for part in path_parts:
            if part not in current:
                logger.warning(f"Segment path '{part}' not found in XML")
                return []
            current = current[part]
        
        # Handle both single item and list of items
        if isinstance(current, list):
            return current
        elif isinstance(current, dict):
            return [current]
        else:
            logger.warning(f"Segment path '{segment_path}' does not contain a dictionary or list")
            return []
    except Exception as e:
        logger.error(f"Error extracting segments from path '{segment_path}': {e}")
        return []

def get_field_value(segment: Dict[str, Any], field_path: str) -> Optional[str]:
    """
    Get a field value from a segment using a path.
    
    Args:
        segment: Segment dictionary
        field_path: Path to the field (e.g., "BASIC.NAME")
        
    Returns:
        Field value as string or None if not found
    """
    try:
        # Split the path and navigate the dictionary
        path_parts = field_path.split('.')
        current = segment
        
        for part in path_parts:
            if part not in current:
                return None
            current = current[part]
        
        # Handle special case where value is in '#text' property
        if isinstance(current, dict) and '#text' in current:
            return current['#text']
        
        return str(current) if current is not None else None
    except Exception as e:
        logger.error(f"Error getting field value for path '{field_path}': {e}")
        return None