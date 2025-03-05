import xml.etree.ElementTree as ET
import json
import logging
import glob
import importlib.util
from datetime import datetime
from pathlib import Path
from jsonschema import validate, ValidationError  # Ensure you have installed jsonschema
import sys
from pathlib import Path

# ---------------------------
# Global Variables & Configuration
# ---------------------------
# Initialize global validation flag
validation_success = True

# Add the 'extensions' folder to the sys.path
extensions_path = Path(__file__).resolve().parent.parent / "extensions"
sys.path.insert(0, str(extensions_path))

# Compute the project root directory (assuming this script is in the "scripts" folder)
base_path = Path(__file__).resolve().parent.parent

# Create logs directory and configure logging with UTF-8 encoding to support Unicode characters
logs_dir = base_path / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f"idoc_to_bydm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# General file handler with UTF-8 encoding
file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Error file handler
error_handler = logging.FileHandler(str(logs_dir / "errors.log"), encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

# ---------------------------
# Utility Functions
# ---------------------------
def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        raise

def xml_to_dict(elem):
    """Recursively converts an XML element and its children into a dictionary."""
    d = {elem.tag: {} if elem.attrib else None}
    children = list(elem)
    if children:
        dd = {}
        for child in map(xml_to_dict, children):
            for k, v in child.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {elem.tag: dd}
    if elem.attrib:
        d[elem.tag].update({('@' + k): v for k, v in elem.attrib.items()})
    text = elem.text.strip() if elem.text else ""
    if text:
        if children or elem.attrib:
            d[elem.tag]['#text'] = text
        else:
            d[elem.tag] = text
    return d

def get_nested_value(json_obj, nested_key):
    keys = nested_key.split(".")
    temp = json_obj
    for key in keys:
        if key.isdigit():
            key = int(key)
            if isinstance(temp, list) and len(temp) > key:
                temp = temp[key]
            else:
                return None
        else:
            if isinstance(temp, dict) and key in temp:
                temp = temp[key]
            else:
                return None
    return temp

def set_nested_value(json_obj, nested_key, value):
    keys = nested_key.split(".")
    temp = json_obj
    for i, key in enumerate(keys[:-1]):
        if key.isdigit():
            idx = int(key)
            if not isinstance(temp, list):
                logger.error(f"Expected a list at {'.'.join(keys[:i])} but found {type(temp).__name__}.")
                return
            while len(temp) <= idx:
                temp.append({})
            temp = temp[idx]
        else:
            if not isinstance(temp, dict):
                logger.error(f"Expected a dict at {'.'.join(keys[:i])} but found {type(temp).__name__}.")
                return
            next_key = keys[i+1] if i+1 < len(keys) else None
            if key not in temp:
                temp[key] = [] if (next_key and next_key.isdigit()) else {}
            temp = temp[key]
    last_key = keys[-1]
    if last_key.isdigit():
        idx = int(last_key)
        if not isinstance(temp, list):
            logger.error(f"Expected a list at the end of {nested_key} but found {type(temp).__name__}.")
            return
        while len(temp) <= idx:
            temp.append(None)
        temp[idx] = value
    else:
        if not isinstance(temp, dict):
            logger.error(f"Expected a dict to set key '{last_key}' but found {type(temp).__name__}.")
            return
        temp[last_key] = value

def apply_transformation(value, transformation):
    if not transformation:
        return value
    if transformation.get("type") == "MAP":
        return transformation["values"].get(value, value)
    return value

# ---------------------------
# Validation and Usage Tracking
# ---------------------------
mapping_usage = {}

def track_mapping(key):
    mapping_usage[key] = mapping_usage.get(key, 0) + 1

def validate_data(value, validation_rule, field_name):
    global validation_success
    if validation_rule == "NUMBER":
        if not value.isdigit():
            logger.warning(f"Validation failed for {field_name}: Expected NUMBER, got '{value}'")
            validation_success = False
            return None
    elif validation_rule == "TEXT":
        if not isinstance(value, str):
            logger.warning(f"Validation failed for {field_name}: Expected TEXT, got '{value}'")
            validation_success = False
            return None
    return value

# ---------------------------
# Parsing Functions
# ---------------------------
def parse_segment(segment, mapping_info, parent_json):
    for field in segment:
        src_field = field.tag
        if src_field not in mapping_info:
            logger.warning(f"Unmapped field '{src_field}' in segment '{segment.tag}'")
            continue

        field_mapping = mapping_info[src_field]

        # Array mapping (e.g., partner functions)
        if isinstance(field_mapping, dict) and "target" in field_mapping and field_mapping.get("isArray"):
            new_obj = {}
            nested_map = field_mapping.get("mapping")
            for sub_field in field:
                sub_src_field = sub_field.tag
                if sub_src_field not in nested_map:
                    logger.warning(f"Unmapped field '{sub_src_field}' in segment '{field.tag}' for array mapping")
                    continue
                sub_mapping = nested_map[sub_src_field]
                sub_value = sub_field.text.strip() if sub_field.text else ""
                transformation = sub_mapping.get("transformation")
                validation_rule = sub_mapping.get("validation")
                transformed_value = apply_transformation(sub_value, transformation)
                valid_value = validate_data(transformed_value, validation_rule, sub_src_field)
                if valid_value is not None:
                    new_obj[sub_mapping["target"]] = valid_value
                    logger.info(f"Mapped '{sub_src_field}' -> '{field_mapping['target']}.{sub_mapping['target']}', Value: '{valid_value}'")
                    track_mapping(f"{field_mapping['target']}.{sub_mapping['target']}")
            target_path = field_mapping["target"]
            target_array = get_nested_value(parent_json, target_path)
            if target_array is None:
                set_nested_value(parent_json, target_path, [])
                target_array = get_nested_value(parent_json, target_path)
            if isinstance(target_array, list):
                target_array.append(new_obj)
            else:
                logger.error(f"Expected target {target_path} to be a list, but found {type(target_array).__name__}")
        # Normal leaf mapping
        elif isinstance(field_mapping, dict) and "target" in field_mapping:
            src_value = field.text.strip() if field.text else ""
            transformation = field_mapping.get("transformation")
            validation_rule = field_mapping.get("validation")
            transformed_value = apply_transformation(src_value, transformation)
            valid_value = validate_data(transformed_value, validation_rule, src_field)
            if valid_value is not None:
                set_nested_value(parent_json, field_mapping["target"], valid_value)
                logger.info(f"Mapped '{src_field}' -> '{field_mapping['target']}', Value: '{valid_value}'")
                track_mapping(field_mapping["target"])
        elif isinstance(field_mapping, dict):
            parse_segment(field, field_mapping, parent_json)
        else:
            logger.warning(f"Invalid mapping for field '{src_field}' in segment '{segment.tag}'")

def parse_idoc(xml_path, config, template):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        output_json = template.copy()
        output_json["unmappedSegments"] = []
        unmapped_summary = {}
        for segment in root.findall("./*"):
            seg_name = segment.tag
            if seg_name in config['mappings']:
                parse_segment(segment, config['mappings'][seg_name], output_json)
            else:
                logger.warning(f"No mapping found for segment '{seg_name}'")
                unmapped_summary[seg_name] = unmapped_summary.get(seg_name, 0) + 1
                output_json["unmappedSegments"].append({seg_name: xml_to_dict(segment)})
        output_json["unmappedSummary"] = unmapped_summary
        output_json["mappingUsage"] = mapping_usage
        logger.info(f"IDoc successfully parsed from {xml_path}")
        return output_json
    except Exception as e:
        logger.error(f"Error parsing IDoc: {e}")
        raise

# ---------------------------
# Schema Validation
# ---------------------------
def validate_schema(output_json, schema_path):
    schema = load_json(schema_path)
    try:
        validate(instance=output_json, schema=schema)
        logger.info("Output JSON is valid against the schema.")
    except ValidationError as ve:
        logger.error(f"Schema validation error: {ve}")
        output_json["schemaErrors"] = str(ve)

# ---------------------------
# Main Execution
# ---------------------------
if __name__ == "__main__":
    idoc_xml_path = base_path / "source" / "Cust Locations IDOC.xml"
    config_json_path = base_path / "config_file" / "Location_mapping.json"
    template_json_path = base_path / "config_file" / "Location_Template.json"
    bydm_json_path = base_path / "output" / "BYDM_Format.json"
    schema_json_path = base_path / "config_file" / "locationMessage.json"  # Extended schema

    logger.info("Starting IDoc to BYDM JSON conversion")

    config = load_json(config_json_path)
    template = load_json(template_json_path)
    if "location" not in template or not template["location"]:
        template["location"] = [{}]

    bydm_json = parse_idoc(idoc_xml_path, config, template)
    run_plugins(bydm_json, config['mappings'])

    validate_schema(bydm_json, schema_json_path)

    if validation_success:
        with open(bydm_json_path, "w", encoding="utf-8") as json_file:
            json.dump(bydm_json, json_file, indent=4)
        logger.info(f"BYDM JSON successfully generated at {bydm_json_path}")
        print(f"BYDM JSON generated at: {bydm_json_path}")
    else:
        logger.error("BYDM JSON generation failed due to validation errors.")
        print("BYDM JSON generation failed due to validation errors.")
