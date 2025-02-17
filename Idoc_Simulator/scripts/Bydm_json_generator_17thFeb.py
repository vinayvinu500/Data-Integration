import xml.etree.ElementTree as ET
import json
import os
import logging
from datetime import datetime
from pathlib import Path

os.chdir('../')
base_path = os.getcwd()
# Configure logging
log_file = f"logs/idoc_to_bydm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Load JSON configuration
def load_json(file_path):
   try:
       with open(file_path, "r") as file:
           return json.load(file)
   except Exception as e:
       logging.error(f"Error loading JSON file {file_path}: {e}")
       raise
# Function to set values in nested JSON
def set_nested_value(json_obj, nested_key, value):
    keys = nested_key.split(".")
    temp = json_obj
    for key in keys[:-1]:  # Traverse till the second last key
        if key.isdigit():  # If the key is a digit, it's an index for a list
            key = int(key)  # Convert the key to an integer
            while len(temp) <= key:  # Ensure the list is long enough
                temp.append({})
            temp = temp[key]
        else:
            if isinstance(temp, list):
                # If temp is a list, then the next key should be an index
                logging.error(f"Expected a dictionary but found a list at {key}. Cannot set value for {nested_key}.")
                return
            if key not in temp:
                temp[key] = {}  # Create missing nested keys
            temp = temp[key]
    if isinstance(temp, list):
        logging.error(f"Expected a dictionary but found a list at {keys[-2]}. Cannot set value for {nested_key}.")
    else:
        temp[keys[-1]] = value  # Set the final value

    # Handle the last key
    if keys[-1].isdigit():
        index = int(keys[-1])
        while index >= len(temp):  # Ensure the array is large enough
            temp.append(None)
        temp[index] = value
    else:
        if isinstance(temp, list):
            logging.error(f"Expected a dictionary to set the key '{keys[-1]}', but found a list in the path '{nested_key}'.")
        else:
            temp[keys[-1]] = value  # Set the final value
# Apply transformations (mapping values)
def apply_transformation(value, transformation):
   if not transformation:
       return value
   if transformation.get("type") == "MAP":
       return transformation["values"].get(value, value)
   return value
# Global flag to track validation status
validation_success = True

# Perform data validation
def validate_data(value, validation_rule, field_name):
    global validation_success
    if validation_rule == "NUMBER":
        if not value.isdigit():
            logging.warning(f"Validation failed for {field_name}: Expected NUMBER, got '{value}'")
            validation_success = False
            return None  # Invalid data will be skipped
    elif validation_rule == "TEXT":
        if not isinstance(value, str):
            logging.warning(f"Validation failed for {field_name}: Expected TEXT, got '{value}'")
            validation_success = False
            return None
    return value
# Recursive function to parse IDoc segments
def parse_segment(segment, segment_name, config, parent_json):
    segment_mapping = config["mappings"].get(segment_name, {})
    for field in segment:
        src_field = field.tag
        src_value = field.text.strip() if field.text else ""
        if src_field in segment_mapping:
            mapping_info = segment_mapping[src_field]
            if 'target' in mapping_info:
                target_field = mapping_info["target"] #need to run a loop if mapping_info ['target'] is mssing,need to check more mappings        
                transformation = mapping_info.get("transformation")
                validation_rule = mapping_info.get("validation")
                transformed_value = apply_transformation(src_value, transformation)
                valid_value = validate_data(transformed_value, validation_rule, src_field)
                if valid_value is not None:
                    set_nested_value(parent_json, target_field, valid_value)
                    logging.info(f"Mapped '{src_field}' → '{target_field}', Value: '{valid_value}'")
            else:
                print(mapping_info.items())
                #need to run a loop if mapping_info ['target'] is mssing,need to check more mappings        
                
        else:
            logging.warning(f"Unmapped field '{src_field}' in segment '{segment_name}'")
# Parse IDoc XML and transform into JSON
def parse_idoc(xml_path, config, template):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        bydm_data = [template.copy()]  # Start with a list containing the expected template
        for segment in root.findall("./*"):  # Iterate over all segments
            segment_name = segment.tag
            if segment_name in config['mappings']:  # Check if the segment is mapped
                parse_segment(segment, segment_name, config, bydm_data[0])  # Pass the first object in the list
        logging.info(f"IDoc successfully parsed from {xml_path}")
        return bydm_data
    except Exception as e:
        logging.error(f"Error parsing IDoc: {e}")
        raise
# Main execution
if __name__ == "__main__":
    # idoc_xml_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/source/Cust Locations IDOC.xml"
    # config_json_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/config_file/Location_mapping.json"
    # template_json_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/config_file/Location_Template.json"
    # bydm_json_path = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/output/bydm_17th_Feb.json"

    idoc_xml_path = Path(base_path + "/source/Cust Locations IDOC.xml")
    config_json_path = Path(base_path + "/config_file/Location_mapping.json")
    template_json_path = Path(base_path + "/config_file/Location_Template.json")
    bydm_json_path = Path(base_path + "/output/bydm_17th_Feb.json")
    
    logging.info("Starting IDoc to BYDM JSON conversion")
    
    # Load configuration & template
    config = load_json(config_json_path)
    template = load_json(template_json_path)
    
    # Parse IDoc and generate JSON
    bydm_json = parse_idoc(idoc_xml_path, config, template)
    
    # Check if all validations passed before saving the JSON output
    if validation_success:
        # Save JSON output
        with open(bydm_json_path, "w", encoding="utf-8") as json_file:
            json.dump(bydm_json, json_file, indent=4)
        logging.info(f"BYDM JSON successfully generated at {bydm_json_path}")
        print(f"BYDM JSON generated at: {bydm_json_path}")
    else:
        logging.error("BYDM JSON generation failed due to validation errors.")
        print("BYDM JSON generation failed due to validation errors.")