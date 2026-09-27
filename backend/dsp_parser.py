import json
import re
from typing import Tuple, Optional

def extract_dsp_actions(response_text: str) -> Tuple[str, Optional[dict]]:
    """
    Extract DSP actions from LLM response.
    Returns (clean_text_without_tags, dsp_actions_dict_or_None)
    """
    pattern = r"<DSP_ACTIONS>(.*?)</DSP_ACTIONS>"
    match = re.search(pattern, response_text, re.DOTALL)
    
    if not match:
        return response_text, None
        
    json_str = match.group(1).strip()
    
    try:
        dsp_actions = json.loads(json_str)
        
        summary_parts = []
        if "eq" in dsp_actions and isinstance(dsp_actions["eq"], list):
            summary_parts.append(f"{len(dsp_actions['eq'])} EQ bands")
        if "de_esser" in dsp_actions:
            summary_parts.append("De-esser")
        if "compressor" in dsp_actions:
            summary_parts.append("Compressor")
        if "reverb" in dsp_actions:
            summary_parts.append("Reverb")
        if "saturation" in dsp_actions:
            summary_parts.append("Saturation")
        if "stereo" in dsp_actions:
            summary_parts.append("Stereo Width")
            
        summary_text = "\n\n🎛️ **[DSP Actions Generated]**"
        if summary_parts:
            summary_text += " — " + ", ".join(summary_parts)
            
        clean_text = re.sub(pattern, summary_text, response_text, flags=re.DOTALL)
        return clean_text, dsp_actions
    except json.JSONDecodeError:
        return response_text, None
