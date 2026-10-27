"""
ToolID: identify which editing application produced a C2PA manifest. Looking claim_generator_info.name

    "claim_generator": "lightroom/9.2",
    "claim_generator_info": [
        {"name": "Lightroom", "version": "9.2", "org.cai.c2pa_rs": "0.46.0"}
    ]

"""
from __future__ import annotations
from typing import Optional

MARKERS = {"lightroom", "adobe photoshop"}

def identify_tool(tool_name: Optional[str]) -> Optional[str]:
    """Normalize and validate a claim-generator name against known tools."""
    if not tool_name:
        return None
    tool = tool_name.lower()
    return tool if tool in MARKERS else None