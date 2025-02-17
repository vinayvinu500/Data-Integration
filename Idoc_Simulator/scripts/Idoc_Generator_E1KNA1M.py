import random
import pandas as pd
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
# Function to generate a random date within a range
def random_date(start, end):
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds())),
    )
# Define the range for random dates
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31)
# Generate 1,000 sample records
records = [] 
for i in range(1, 3): 
    docnum = f"{i:015d}"  # Format document number with leading zeros 
    createdt = random_date(start_date, end_date).strftime('%Y%m%d') 
    createtime = f"{random.randint(0,23):02d}{random.randint(0,59):02d}{random.randint(0,59):02d}" 
    sender = f"{random.randint(1000000000, 9999999999):010d}" 
    receiver = f"{random.randint(1000000000, 9999999999):010d}" 
    doctype = random.choice(["ORDERS", "INVOIC", "DESADV"]) 
    status = random.choice(["60", "70"," ","80"]) 
    kunnr = f"{random.randint(1000000000, 9999999999):010d}" 
    land1 = random.choice(["US", "CAN", "PH"])
    name1 = random.choice(["ABC Logistics Inc.","Sample Corporation"])
    pstlz = f"{random.randint(10001, 99999):010d}" 
    telf1 = f"{random.randint(1000000000, 9999999999):010d}" 
    record = { 
        "SegmentName": "E1KNA1M",
        "KUNNR": kunnr, 
        "LAND1": land1, 
        "NAME1": name1, 
        "ORT01": "New York", 
        "PSTLZ": pstlz, 
        "REGIO": "NY", 
        "STRAS": "123 Main Street", 
        "TELF1": telf1, 
        "LIFNR": "Vendor", 
        "SPRAS": "EN" 
    } 
    records.append(record) 
# Convert the records to a DataFrame
df = pd.DataFrame(records)
# Define the target folder path
target_folder = 'C:/Users/FQ427DY/Downloads/Idoc_Simulator/source'
# Check if the target folder exists, and create it if it doesn't
if not os.path.exists(target_folder):
    os.makedirs(target_folder)
# Create root element
idoc = ET.Element("IDOC", {"BEGIN": "1"})				 
# Control Record (EDI_DC40)
control_record = ET.SubElement(idoc, "E1KNA1M")
ET.SubElement(control_record, "TABNAM").text = "E1KNA1M"
ET.SubElement(control_record, "DOCNUM").text = "0000000009876543"
ET.SubElement(control_record, "DIRECT").text = "1"
ET.SubElement(control_record, "IDOCTYP").text = "LOCMAS"
ET.SubElement(control_record, "MESTYP").text = "LOCMAS"
ET.SubElement(control_record, "SNDPRT").text = "LS"
ET.SubElement(control_record, "SNDPRN").text = "SAP_SYSTEM"
ET.SubElement(control_record, "RCVPRT").text = "LS"
ET.SubElement(control_record, "RCVPRN").text = "EXTERNAL_SYSTEM"
ET.SubElement(control_record, "CREDAT").text = datetime.now().strftime('%Y%m%d')
ET.SubElement(control_record, "CRETIM").text = datetime.now().strftime('%H%M%S')
 
# Loop through Excel and create location segments
for _, row in df.iterrows():
    segment = ET.SubElement(idoc, row["SegmentName"], {"SEGMENT": "1"})
    for col in df.columns:
        if col != "SegmentName" and pd.notna(row[col]):
            ET.SubElement(segment, col).text = str(row[col])

# Convert to XML string and save file
xml_str = ET.tostring(idoc, encoding="utf-8").decode()
filename = f"location_idoc_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
file_path = os.path.join(target_folder, filename)  # Use the target folder path

with open(file_path, "w", encoding="utf-8") as xml_file:
    xml_file.write(xml_str)

print(f"IDoc XML saved to {file_path}")
