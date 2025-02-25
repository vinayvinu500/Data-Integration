import xml.etree.ElementTree as ET
import json
import logging
from datetime import datetime
from pathlib import Path

# Compute the project root directory
base_path = Path(__file__).resolve().parent.parent

# Configure logging
logs_dir = base_path / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f"idoc_to_bydm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=str(log_file), level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def load_json(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading JSON file {file_path}: {e}")
        raise

def xml_to_dict(elem):
    """Recursively converts an XML element and its children into a dict."""
    d = {elem.tag: {} if elem.attrib else None}
    children = list(elem)
    if children:
        dd = {}
        for dc in map(xml_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {elem.tag: dd}
    if elem.attrib:
        d[elem.tag].update(('@' + k, v) for k, v in elem.attrib.items())
    if elem.text:
        text = elem.text.strip()
        if children or elem.attrib:
            if text:
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
                logging.error(f"Expected a list at {'.'.join(keys[:i])} but found {type(temp).__name__}.")
                return
            while len(temp) <= idx:
                temp.append({})
            temp = temp[idx]
        else:
            if not isinstance(temp, dict):
                logging.error(f"Expected a dict at {'.'.join(keys[:i])} but found {type(temp).__name__}.")
                return
            next_key = keys[i+1] if i+1 < len(keys) else None
            if key not in temp:
                if next_key and next_key.isdigit():
                    temp[key] = []
                else:
                    temp[key] = {}
            temp = temp[key]
    last_key = keys[-1]
    if last_key.isdigit():
        idx = int(last_key)
        if not isinstance(temp, list):
            logging.error(f"Expected a list at the end of {nested_key} but found {type(temp).__name__}.")
            return
        while len(temp) <= idx:
            temp.append(None)
        temp[idx] = value
    else:
        if not isinstance(temp, dict):
            logging.error(f"Expected a dict to set key '{last_key}' but found {type(temp).__name__}.")
            return
        temp[last_key] = value

def apply_transformation(value, transformation):
    if not transformation:
        return value
    if transformation.get("type") == "MAP":
        return transformation["values"].get(value, value)
    return value

# Global flag for validation
validation_success = True

def validate_data(value, validation_rule, field_name):
    global validation_success
    if validation_rule == "NUMBER":
        if not value.isdigit():
            logging.warning(f"Validation failed for {field_name}: Expected NUMBER, got '{value}'")
            validation_success = False
            return None
    elif validation_rule == "TEXT":
        if not isinstance(value, str):
            logging.warning(f"Validation failed for {field_name}: Expected TEXT, got '{value}'")
            validation_success = False
            return None
    return value

def parse_segment(segment, mapping_info, parent_json):
    for field in segment:
        src_field = field.tag
        if src_field not in mapping_info:
            logging.warning(f"Unmapped field '{src_field}' in segment '{segment.tag}'")
            continue

        field_mapping = mapping_info[src_field]
        if isinstance(field_mapping, dict) and "target" in field_mapping and field_mapping.get("isArray"):
            new_obj = {}
            nested_map = field_mapping.get("mapping")
            for sub_field in field:
                sub_src_field = sub_field.tag
                if sub_src_field not in nested_map:
                    logging.warning(f"Unmapped field '{sub_src_field}' in segment '{field.tag}' for array mapping")
                    continue
                sub_mapping = nested_map[sub_src_field]
                sub_value = sub_field.text.strip() if sub_field.text else ""
                transformation = sub_mapping.get("transformation")
                validation_rule = sub_mapping.get("validation")
                transformed_value = apply_transformation(sub_value, transformation)
                valid_value = validate_data(transformed_value, validation_rule, sub_src_field)
                if valid_value is not None:
                    new_obj[sub_mapping["target"]] = valid_value
                    logging.info(f"Mapped '{sub_src_field}' → '{field_mapping['target']}.{sub_mapping['target']}', Value: '{valid_value}'")
            target_path = field_mapping["target"]
            target_array = get_nested_value(parent_json, target_path)
            if target_array is None:
                set_nested_value(parent_json, target_path, [])
                target_array = get_nested_value(parent_json, target_path)
            if isinstance(target_array, list):
                target_array.append(new_obj)
            else:
                logging.error(f"Expected target {target_path} to be a list, but found {type(target_array).__name__}")
        elif isinstance(field_mapping, dict) and "target" in field_mapping:
            src_value = field.text.strip() if field.text else ""
            transformation = field_mapping.get("transformation")
            validation_rule = field_mapping.get("validation")
            transformed_value = apply_transformation(src_value, transformation)
            valid_value = validate_data(transformed_value, validation_rule, src_field)
            if valid_value is not None:
                set_nested_value(parent_json, field_mapping["target"], valid_value)
                logging.info(f"Mapped '{src_field}' → '{field_mapping['target']}', Value: '{valid_value}'")
        elif isinstance(field_mapping, dict):
            parse_segment(field, field_mapping, parent_json)
        else:
            logging.warning(f"Invalid mapping for field '{src_field}' in segment '{segment.tag}'")

def parse_idoc(xml_path, config, template):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        output_json = template.copy()
        # Prepare a fallback section for unmapped segments
        output_json["unmappedSegments"] = []
        for segment in root.findall("./*"):
            seg_name = segment.tag
            if seg_name in config['mappings']:
                parse_segment(segment, config['mappings'][seg_name], output_json)
            else:
                logging.warning(f"No mapping found for segment '{seg_name}'")
                # Convert the segment to dict and add to fallback
                seg_dict = xml_to_dict(segment)
                output_json["unmappedSegments"].append({ seg_name: seg_dict })
        logging.info(f"IDoc successfully parsed from {xml_path}")
        return output_json
    except Exception as e:
        logging.error(f"Error parsing IDoc: {e}")
        raise

if __name__ == "__main__":
    idoc_xml_path = base_path / "source" / "Cust Locations IDOC.xml"
    config_json_path = base_path / "config_file" / "Location_mapping.json"
    template_json_path = base_path / "config_file" / "Location_Template.json"
    bydm_json_path = base_path / "output" / "BYDM_Format.json"
    
    logging.info("Starting IDoc to BYDM JSON conversion")
    
    config = load_json(config_json_path)
    template = load_json(template_json_path)
    if "location" not in template or not template["location"]:
        template["location"] = [{}]
    
    bydm_json = parse_idoc(idoc_xml_path, config, template)
    
    if validation_success:
        with open(bydm_json_path, "w", encoding="utf-8") as json_file:
            json.dump(bydm_json, json_file, indent=4)
        logging.info(f"BYDM JSON successfully generated at {bydm_json_path}")
        print(f"BYDM JSON generated at: {bydm_json_path}")
    else:
        logging.error("BYDM JSON generation failed due to validation errors.")
        print("BYDM JSON generation failed due to validation errors.")
