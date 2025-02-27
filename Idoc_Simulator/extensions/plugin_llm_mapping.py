import json
import logging
from ollama import chat

logger = logging.getLogger(__name__)

def get_mapping_context(mapping_config: dict) -> str:
    """
    Generate a brief context summary of the current mapping configuration.
    This could include the top-level keys (e.g., EDI_DC40, E1KNA1M, etc.) 
    and a summary of their target paths.
    """
    context = "Current Mapping Overview:\n"
    for segment, config in mapping_config.items():
        context += f"- {segment}: "
        # If the mapping is a dictionary with a 'target', list it; if nested, note it.
        if isinstance(config, dict) and "target" in config:
            context += f"target -> {config['target']}"
            if config.get("isArray"):
                context += " [Array]"
        elif isinstance(config, dict):
            # For nested mappings, list the keys
            nested_keys = ", ".join(config.keys())
            context += f"nested keys: {nested_keys}"
        context += "\n"
    return context

def get_local_llm_suggestions(prompt: str, model: str = "deepseek-r1:8b") -> str:
    """
    Calls the local Ollama service using the synchronous 'chat' function.
    """
    try:
        response = chat(model=model, messages=[{"role": "user", "content": prompt}])
        suggestion = response['message']['content'].strip()
        logger.info("Ollama output: %s", suggestion)
        return suggestion
    except Exception as e:
        logger.error("Error calling Ollama: %s", e)
        return "Error: Unable to generate mapping suggestion."

def generate_mapping_suggestion(unmapped_segment: dict, mapping_config: dict) -> str:
    """
    Prepares a prompt including both the unmapped segment and a summary of the current mapping configuration.
    
    Args:
        unmapped_segment (dict): The unmapped segment data.
        mapping_config (dict): The overall mapping configuration.
    
    Returns:
        str: The LLM's suggestion.
    """
    context_summary = get_mapping_context(mapping_config)
    prompt = (
        "You are an expert in SAP IDoc mapping and BYDM JSON formats.\n\n"
        f"{context_summary}\n"
        "Given the following unmapped XML segment converted to JSON:\n\n"
        f"{json.dumps(unmapped_segment, indent=2)}\n\n"
        "Please suggest a JSON mapping configuration snippet to map these fields appropriately into the BYDM format."
    )
    return get_local_llm_suggestions(prompt, "smallthinker")

def post_process(output_json: dict, mapping_config: dict):
    """
    Post-processes the output JSON by generating mapping suggestions for each unmapped segment.
    The suggestions incorporate context from the current mapping configuration.
    """
    unmapped = output_json.get("unmappedSegments", [])
    suggestions = {}

    if not unmapped:
        print("No unmapped segments found; no suggestions generated.")
        return

    for segment in unmapped:
        for seg_name, seg_data in segment.items():
            logger.info("Generating suggestion for unmapped segment '%s'", seg_name)
            suggestion = generate_mapping_suggestion(seg_data, mapping_config)
            suggestions[seg_name] = suggestion
            print(f"Suggestion for segment {seg_name}:\n{suggestion}\n")

    output_json["llmMappingSuggestions"] = suggestions
    logger.info("LLM mapping suggestions added to output JSON.")
