import xml.etree.ElementTree as ET
import yaml
import json
import os
import shutil
import logging
from datetime import datetime

# Configure logging
log_file = f"logs/idoc_to_bydm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load YAML configuration
def load_config(config_path):
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logging.error(f"Error loading YAML config: {e}")
        raise

# Apply transformations
def apply_transformation(value, transformation_info):
    if not transformation_info or value is None:
        return value
    # Check if transformation_info is a string (indicating a direct transformation type)
    if isinstance(transformation_info, str):
        if transformation_info == "UPPERCASE":
            return value.upper()
    # Check if transformation_info is a dictionary (indicating a transformation with additional details)
    elif isinstance(transformation_info, dict):
        transformation_type = transformation_info.get("transformation")
        conditions = transformation_info.get("conditions", {})
        
        if transformation_type == "CONDITIONAL":
            return conditions.get(value, conditions.get("default", value))
        elif transformation_type == "MAP":
            return conditions.get(value, value)
    else:
        logging.warning(f"Unknown transformation type for value '{value}': {transformation_info}")
    return value


# Perform data validation
def validate_data(value, validation_rule, field_name):
    if validation_rule == "NUMBER" and not value.isdigit():
        raise ValueError(f"Validation failed for {field_name}: Expected NUMBER, got '{value}'")
    elif validation_rule == "TEXT" and not isinstance(value, str):
        raise ValueError(f"Validation failed for {field_name}: Expected TEXT, got '{value}'")
    # If no validation rule is provided or if the value passes validation, return the value
    return value


# Recursive function to parse segments
def parse_segment(segment, segment_name, config):
    segment_data = {}
    segment_mapping = config["mappings"].get(segment_name, {})
    for field in segment:
        if list(field):  # If field has children, it's a nested segment
            nested_segment_name = field.tag
            if nested_segment_name not in segment_data:
                segment_data[nested_segment_name] = []
            segment_data[nested_segment_name].append(parse_segment(field, nested_segment_name, config))
        else:
            src_field = field.tag
            src_value = field.text.strip() if field.text else ""
            if src_field in segment_mapping:
                mapping_info = segment_mapping[src_field]
                target_field = mapping_info["target"]
                transformed_value = apply_transformation(src_value, mapping_info)  # Pass the entire mapping_info
                validation_rule = mapping_info.get("validation_rule", None)
                valid_value = validate_data(transformed_value, validation_rule, src_field)
                if valid_value is not None:
                    segment_data[target_field] = valid_value
                    logging.info(f"Mapped '{src_field}' in '{segment_name}' → '{target_field}', Value: '{valid_value}'")
            else:
                logging.warning(f"Unmapped field '{src_field}' in segment '{segment_name}'")
    return segment_data

# Parse IDoc XML and transform into JSON
def parse_idoc(xml_path, config):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        bydm_data = {}
        for segment in root.findall("./*"):  # Iterate over all segments
            segment_name = segment.tag
            parsed_segment = parse_segment(segment, segment_name, config)
            if parsed_segment:
                if segment_name not in bydm_data:
                    bydm_data[segment_name] = []
                bydm_data[segment_name].append(parsed_segment)
        logging.info(f"IDoc successfully parsed from {xml_path}")
        return bydm_data
    except Exception as e:
        logging.error(f"Error parsing IDoc: {e}")
        raise

# Main execution
if __name__ == "__main__":
    idoc_xml_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/source/Cust Locations IDOC.xml"
    config_yaml_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/config_file/Samplelocation_14th_Feb.yaml"
    bydm_json_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/output/bydm_output_location_14th_Feb.json"
    os.makedirs("source", exist_ok=True)
    os.makedirs("config_file", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    logging.info("Starting IDoc to BYDM JSON conversion")
    # Load configuration
    config = load_config(config_yaml_path)
    # Parse IDoc and generate JSON
    try:
        bydm_json = parse_idoc(idoc_xml_path, config)
        # Save JSON output only if no validation errors occurred
        with open(bydm_json_path, "w", encoding="utf-8") as json_file:
            json.dump(bydm_json, json_file, indent=4)
        logging.info(f"BYDM JSON successfully generated at {bydm_json_path}")
        print(f"BYDM JSON generated at: {bydm_json_path}")
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        print(f"Validation error: {e}")
        # Optionally, handle the failed validation case, e.g., by not writing the JSON file

