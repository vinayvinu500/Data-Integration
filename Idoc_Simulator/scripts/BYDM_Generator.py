import os
import xml.etree.ElementTree as ET
import yaml
import json
import logging
# Setup logging
LOG_FILE = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/logs/idoc_processing.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# File paths
SOURCE_DIR = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/source"
TARGET_DIR = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/output"
CONFIG_FILE = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/config_file/config.yaml"# Load transformation config
# Load transformation config
try:
   with open(CONFIG_FILE, "r") as config_file:
       config = yaml.safe_load(config_file)
       mappings = config.get("mappings", {})
       logging.debug(f"✅ Loaded mappings: {mappings}")
except Exception as e:
   logging.error(f"❌ Failed to load config file: {e}")
   raise SystemExit("Error: Unable to load config file.")
# Function to apply transformations
def apply_transformations(field, value, mapping_config):
    # Check if the mapping_config is a string, indicating a direct field renaming
    if isinstance(mapping_config, str):
        transformed_field = mapping_config
    else:
        # Otherwise, it's a dictionary with transformation details
        transformed_field = mapping_config.get("target", field)
        transformation_type = mapping_config.get("transformation", None)
        conditions = mapping_config.get("conditions", {})
        
        if transformation_type == "uppercase":
            value = value.upper()
        elif transformation_type == "conditional_map":
            value = conditions.get(value, conditions.get("", value))  # Use the default value if provided

    logging.debug(f"🔄 Transforming {field}: '{value}' -> '{transformed_field}'")
    # Perform validation if specified
    validation_config = mapping_config.get("validation", {})
    validation_type = validation_config.get("type", None)
    if validation_type == "number" and not value.isdigit():
        raise ValueError(f"Validation error: Field '{field}' expects a number but got '{value}'")
    elif validation_type == "text" and not isinstance(value, str):
        raise ValueError(f"Validation error: Field '{field}' expects text but got '{value}'")
    return transformed_field, value
# Process each XML file in the source folder
for filename in os.listdir(SOURCE_DIR):
    if filename.endswith(".xml"):
        xml_path = os.path.join(SOURCE_DIR, filename)
        json_path = os.path.join(TARGET_DIR, filename.replace(".xml", ".json"))
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            # Extract all <E1KNA1M> data segments, skipping the control record
            segments = root.findall(".//E1KNA1M[@SEGMENT='1']")
            if not segments:
                logging.warning(f"⚠️ No valid data segments found in {filename}")
                continue
            result_data = []
            for segment in segments:
                segment_data = {}
                for field, mapping_config in mappings.items():
                    xml_element = segment.find(field)
                    value = xml_element.text.strip() if xml_element is not None and xml_element.text else ""
                    # Apply transformations and get the transformed field name
                    transformed_field, transformed_value = apply_transformations(field, value, mapping_config)
                    segment_data[transformed_field] = transformed_value
                logging.debug(f"📄 Processed segment: {segment_data}")
                result_data.append(segment_data)
            # Save transformed data as JSON
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(result_data, json_file, indent=4)
            logging.info(f"✅ Successfully processed {filename} -> {json_path}")
        except ET.ParseError as e:
            logging.error(f"❌ XML parsing error in {filename}: {e}")
        except Exception as e:
            logging.error(f"❌ Unexpected error in {filename}: {e}")
