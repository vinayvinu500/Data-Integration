import pandas as pd
import io
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("app")

# Column names in the Excel mapping sheet
COL_BYDM_TARGET_PATH = "BYDM Target Path"
COL_SAP_XPATH = "SAP Source Path (XPath)"
COL_TRANSFORMATION_RULE = "Transformation Rule"
COL_DEFAULT_VALUE = "Default Value"
COL_TARGET_DATA_TYPE = "Target Data Type"
COL_IS_MANDATORY = "Is Mandatory (Target)"

def load_mapping_from_excel(excel_data: bytes, sheet_name: str = "Data Mapping") -> List[Dict[str, Any]]:
    """
    Parse Excel mapping sheet to mapping rules.
    
    Args:
        excel_data: Excel file content as bytes
        sheet_name: Name of the sheet containing mapping rules
        
    Returns:
        List of dictionaries, each representing a mapping rule
    """
    try:
        # Load Excel into pandas DataFrame
        excel_file = io.BytesIO(excel_data)
        df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=object)
        
        # Check if required columns exist
        required_columns = [COL_BYDM_TARGET_PATH, COL_SAP_XPATH]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f"Missing required columns in mapping sheet: {', '.join(missing_columns)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Process DataFrame to extract mapping rules
        mapping_rules = []
        for _, row in df.iterrows():
            target_path = row.get(COL_BYDM_TARGET_PATH)
            source_path = row.get(COL_SAP_XPATH)
            
            # Skip rows without target or source path
            if pd.isna(target_path) or pd.isna(source_path):
                continue
            
            # Create mapping rule
            rule = {
                'target': target_path.strip(),
                'source': source_path.strip(),
                'transformation': row.get(COL_TRANSFORMATION_RULE, ''),
                'default_value': row.get(COL_DEFAULT_VALUE, ''),
                'validation': row.get(COL_TARGET_DATA_TYPE, 'TEXT'),
                'is_mandatory': str(row.get(COL_IS_MANDATORY, 'N')).upper() in ('Y', 'YES', 'TRUE', '1')
            }
            
            # Handle NaN values
            for key in rule:
                if pd.isna(rule[key]):
                    if key in ['transformation', 'default_value']:
                        rule[key] = ''
                    elif key == 'validation':
                        rule[key] = 'TEXT'
                    elif key == 'is_mandatory':
                        rule[key] = False
            
            mapping_rules.append(rule)
        
        logger.info(f"Loaded {len(mapping_rules)} mapping rules from Excel")
        return mapping_rules
    
    except Exception as e:
        logger.error(f"Failed to load mapping from Excel: {e}")
        raise
    
def parse_transformation_rule(rule_text: str) -> Dict[str, str]:
    """
    Parse transformation rule text into a mapping dictionary.
    
    Args:
        rule_text: String representation of transformation rule
        
    Returns:
        Dictionary mapping source values to target values
    """
    if not rule_text or pd.isna(rule_text):
        return {}
    
    # Simple parsing for key-value mapping rules
    result = {}
    try:
        for line in rule_text.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
    except Exception as e:
        logger.error(f"Error parsing transformation rule: {e}")
    
    return result

def convert_mapping_to_json(mapping_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert mapping rules to structured JSON for processing.
    
    Args:
        mapping_rules: List of mapping rule dictionaries
        
    Returns:
        Structured JSON mapping configuration
    """
    mapping_json = {"mappings": {}}
    
    for rule in mapping_rules:
        # Extract segment name from source path
        source_parts = rule['source'].split('.')
        segment_name = source_parts[0] if source_parts else None
        
        if not segment_name:
            logger.warning(f"Skipping rule with invalid source path: {rule['source']}")
            continue
        
        # Initialize segment if not exists
        if segment_name not in mapping_json["mappings"]:
            mapping_json["mappings"][segment_name] = {}
        
        # Extract field name
        field_name = source_parts[-1] if len(source_parts) > 1 else None
        if not field_name:
            logger.warning(f"Skipping rule with no field name: {rule['source']}")
            continue
        
        # Add mapping rule to the appropriate segment
        mapping_rule = {
            "target": rule['target'],
            "validation": rule['validation'],
        }
        
        # Add conditional properties
        if rule['default_value']:
            mapping_rule["default_value"] = rule['default_value']
        
        if rule['transformation']:
            transformation_values = parse_transformation_rule(rule['transformation'])
            if transformation_values:
                mapping_rule["transformation"] = {
                    "type": "MAP",
                    "values": transformation_values
                }
        
        # Handle nested segments
        if len(source_parts) > 2:
            # This is a nested field, need to create nested structure
            current = mapping_json["mappings"][segment_name]
            for part in source_parts[1:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[field_name] = mapping_rule
        else:
            # Direct field in segment
            mapping_json["mappings"][segment_name][field_name] = mapping_rule
    
    return mapping_json