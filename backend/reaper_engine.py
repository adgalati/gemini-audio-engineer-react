import os
from typing import List, Dict

def generate_reaper_project(job_id: str, stems: List[str], midi_files: List[str], output_path: str):
    """
    Generate a basic .RPP file for Reaper that imports stems and MIDI.
    """
    
    rpp_content = []
    rpp_content.append("<REAPER_PROJECT 0.1 \"6.75/win64\" 1680192000")
    rpp_content.append("  RIPPLE 0")
    rpp_content.append("  GROUPOVERRIDE 0 0 0")
    rpp_content.append("  AUTO_CROSSFADE 1 0.010000 0.010000")
    
    # 1. Add Stems as Tracks
    for stem in stems:
        track_name = os.path.splitext(stem)[0].upper()
        # Relative path from the project file location to the stem
        stem_rel_path = f"stems/{stem}"
        
        rpp_content.append("  <TRACK")
        rpp_content.append(f"    NAME {track_name}")
        rpp_content.append("    <ITEM")
        rpp_content.append("      POSITION 0")
        rpp_content.append("      SNAPOFFS 0")
        rpp_content.append(f"      FILE \"{stem_rel_path}\"")
        rpp_content.append("    >")
        rpp_content.append("  >")

    # 2. Add MIDI files as Tracks
    for midi in midi_files:
        track_name = os.path.splitext(midi)[0].upper()
        midi_rel_path = f"midi/{midi}"
        
        rpp_content.append("  <TRACK")
        rpp_content.append(f"    NAME {track_name}")
        rpp_content.append("    <ITEM")
        rpp_content.append("      POSITION 0")
        rpp_content.append("      SNAPOFFS 0")
        rpp_content.append(f"      FILE \"{midi_rel_path}\"")
        rpp_content.append("    >")
        rpp_content.append("  >")

    rpp_content.append(">")
    
    with open(output_path, "w") as f:
        f.write("\n".join(rpp_content))
    
    return output_path
