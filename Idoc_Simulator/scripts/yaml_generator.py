import pandas as pd
import yaml
import os
import shutil
from datetime import datetime
# Define the folder path
output_folder = "C:/Users/FQ427DY/Downloads/Idoc_Simulator/config_file"
os.makedirs(output_folder, exist_ok=True)  # Create folder if it doesn't exist
# Define file paths
yaml_file_path = os.path.join(output_folder, "config.yaml")
# Backup existing YAML file if it exists
if os.path.exists(yaml_file_path):
   timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
   backup_file_path = os.path.join(output_folder, f"config_backup_{timestamp}.yaml")
   shutil.copy(yaml_file_path, backup_file_path)
   print(f"Backup created: {backup_file_path}")
# Load Excel file
df = pd.read_excel("C:/Users/FQ427DY/Downloads/Idoc_Simulator/source/Yaml_Creation_Mapping.xlsx")
# Filter rows where 'Mapping Needed' is 'Y'
df = df[df["Mapping Needed"] == "Y"]
# Initialize YAML structure
yaml_data = {"mappings": {}}
# Define transformations
for _, row in df.iterrows():
    # Initialize the mapping dictionary with target column
    mapping = {
        "target": row["target_column"]
    }
    # Handle transformation values if provided
    if pd.notna(row["transformation_values"]):
        value_mappings = {}
        for pair in row["transformation_values"].split(","):
            key, value = pair.split(":")
            value_mappings[key.strip()] = value.strip()
        # Check if the mapping type is 'conditional_map'
        if row["mapping_type"] == "conditional_map":
            # Assign the conditions dictionary directly to the transformation key
            mapping["transformation"] = "conditional_map"
            mapping["conditions"] = value_mappings
        else:
            # If the mapping type is not 'conditional_map', assign the mapping type as is
            mapping["transformation"] = row["mapping_type"]
    else:
        # If no transformation values are provided, use the mapping type as is
        mapping["transformation"] = row["mapping_type"]
    
    # Use src_column as the key instead of including it inside mappings
    yaml_data["mappings"][row["src_column"]] = mapping
# Save to YAML file
with open(yaml_file_path, "w") as yaml_file:
   yaml.dump(yaml_data, yaml_file, default_flow_style=False, sort_keys=False, indent=2)
print(f"YAML file generated: {yaml_file_path}")