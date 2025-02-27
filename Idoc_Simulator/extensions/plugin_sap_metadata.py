def post_process(output_json, mapping_config):
    """
    This plugin simulates integration with SAP ECC/S4HANA metadata.
    For each unmapped segment, it "retrieves" metadata (here we simulate it)
    and adds a new field "sapMetadata" to the output JSON.
    
    Args:
        output_json (dict): The final output JSON.
        mapping_config (dict): The overall mapping configuration (not used here).
    """
    unmapped = output_json.get("unmappedSegments", [])
    metadata_info = {}
    
    for segment in unmapped:
        for seg_name, seg_data in segment.items():
            # In a real scenario, call a SAP metadata API here.
            dummy_metadata = {
                "expectedFields": [],
                "description": f"Metadata for {seg_name} from SAP system."
            }
            metadata_info[seg_name] = dummy_metadata

    output_json["sapMetadata"] = metadata_info
    print("Simulated SAP metadata added to output JSON.")
